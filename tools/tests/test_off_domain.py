import json
import os
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local" / "share" / "off"))

from offload.config import (
    ConfigError,
    OffloadConfig,
    SetupSpec,
    WorkerSpec,
    load_config,
    parse_config,
    parse_duration,
)
from offload.identity import base_key, host_slug, repo_slug, token, worker_name, worker_prefix
from offload.policy import policy_hash, run_network_rules, setup_network_rules
from offload.state import (
    Lease,
    WorkerCache,
    append_record,
    artifact_root,
    artifacts_dir,
    delete_cache,
    done_marker,
    lease_workers,
    lock_path,
    new_run_id,
    read_cache,
    read_records,
    run_log,
    state_root,
    write_cache,
)

MINIMAL = """
version = 1

[setup]
inputs = ["yarn.lock"]
run = ["yarn install --frozen-lockfile"]

[tasks.check]
run = "yarn test"
timeout = "20m"
"""

WORKER = WorkerSpec(
    memory_mb=4096,
    max=2,
    egress=("registry.npmjs.org",),
    setup_egress=("pypi.org",),
)


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "yarn.lock").write_bytes(b"lock v1\n")

    def _load(self, text: str) -> OffloadConfig:
        return parse_config(self.root, tomllib.loads(text))

    def test_defaults(self) -> None:
        config = self._load(MINIMAL)
        self.assertEqual(
            config.worker, WorkerSpec(memory_mb=4096, max=2, egress=(), setup_egress=())
        )
        self.assertEqual(
            config.setup,
            SetupSpec(inputs=("yarn.lock",), run=("yarn install --frozen-lockfile",)),
        )
        self.assertEqual(config.sync_exclude, ())
        self.assertEqual(config.env_pass, ())
        task = config.tasks["check"]
        self.assertEqual(task.name, "check")
        self.assertEqual(task.run, "yarn test")
        self.assertEqual(task.timeout_s, 1200)
        self.assertEqual(task.where, "sprite")
        self.assertEqual(task.shards, 1)
        self.assertEqual(task.artifacts, ())
        self.assertEqual(dict(task.env), {})

    def test_task_env_and_env_pass(self) -> None:
        text = MINIMAL.replace('timeout = "20m"', 'timeout = "20m"\n[tasks.check.env]\nCI = "1"')
        config = self._load(text + '\n[env]\npass = ["GITHUB_TOKEN"]\n')
        self.assertEqual(dict(config.tasks["check"].env), {"CI": "1"})
        self.assertEqual(config.env_pass, ("GITHUB_TOKEN",))

    def test_required_keys(self) -> None:
        with self.assertRaisesRegex(ConfigError, "version: required, must be 1"):
            self._load(MINIMAL.replace("version = 1", "version = 2"))
        with self.assertRaisesRegex(ConfigError, "missing tasks"):
            self._load(MINIMAL.split("[tasks.check]")[0])
        with self.assertRaisesRegex(ConfigError, "missing tasks.check.timeout"):
            self._load(MINIMAL.replace('timeout = "20m"\n', ""))

    def test_unknown_task_key_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "unknown key tasks.check.timout"):
            self._load(MINIMAL.replace('timeout = "20m"', 'timout = "20m"'))

    def test_timeout_must_be_a_duration(self) -> None:
        with self.assertRaisesRegex(ConfigError, "tasks.check.timeout: bad duration"):
            self._load(MINIMAL.replace('"20m"', '"20"'))

    def test_timeout_capped_at_six_hours(self) -> None:
        config = self._load(MINIMAL.replace('"20m"', '"6h"'))
        self.assertEqual(config.tasks["check"].timeout_s, 21600)
        with self.assertRaisesRegex(ConfigError, "exceeds the 6h maximum"):
            self._load(MINIMAL.replace('"20m"', '"7h"'))

    def test_shards_bounded_by_worker_max(self) -> None:
        sharded = MINIMAL.replace("[tasks.check]", "[tasks.check]\nshards = 3")
        with self.assertRaisesRegex(ConfigError, "tasks.check.shards: must be between 1 and 2"):
            self._load(sharded)
        widened = sharded + "\n[worker]\nmax = 4\n"
        self.assertEqual(self._load(widened).tasks["check"].shards, 3)

    def test_missing_setup_input_rejected(self) -> None:
        (self.root / "yarn.lock").unlink()
        with self.assertRaisesRegex(ConfigError, "yarn.lock is not a file"):
            self._load(MINIMAL)

    def test_paths_must_stay_in_repo(self) -> None:
        with self.assertRaisesRegex(ConfigError, "setup.inputs: '../yarn.lock' must be relative"):
            self._load(MINIMAL.replace('"yarn.lock"', '"../yarn.lock"'))
        with self.assertRaisesRegex(
            ConfigError, "tasks.check.artifacts: '/tmp/out' must be relative"
        ):
            self._load(
                MINIMAL.replace('timeout = "20m"', 'timeout = "20m"\nartifacts = ["/tmp/out"]')
            )

    def test_task_names_follow_rules(self) -> None:
        for name in ["Check", "1check", "check_all", "a" * 33]:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ConfigError, "invalid task name"):
                    self._load(MINIMAL.replace("[tasks.check]", f"[tasks.{name}]"))
        longest = "a" * 32
        config = self._load(MINIMAL.replace("[tasks.check]", f"[tasks.{longest}]"))
        self.assertEqual(set(config.tasks), {longest})

    def test_env_names_validated(self) -> None:
        with self.assertRaisesRegex(ConfigError, "'1BAD' is not an environment variable name"):
            self._load(
                MINIMAL.replace('timeout = "20m"', 'timeout = "20m"\n[tasks.check.env]\n"1BAD" = "x"')
            )
        with self.assertRaisesRegex(ConfigError, "'bad-name' is not an environment variable name"):
            self._load(MINIMAL + '\n[env]\npass = ["bad-name"]\n')

    def test_blank_commands_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "tasks.check.run: command is empty"):
            self._load(MINIMAL.replace('run = "yarn test"', 'run = "  "'))
        with self.assertRaisesRegex(ConfigError, "setup.run: command is empty"):
            self._load(MINIMAL.replace('run = ["yarn install --frozen-lockfile"]', 'run = [" "]'))

    def test_base_key_tracks_setup_and_inputs_only(self) -> None:
        config = self._load(MINIMAL)
        key = base_key(config)
        self.assertEqual(len(key), 12)
        task_edit = self._load(MINIMAL.replace('"yarn test"', '"yarn test --ci"'))
        self.assertEqual(base_key(task_edit), key)
        setup_edit = self._load(MINIMAL.replace("--frozen-lockfile", "--ignore-scripts"))
        self.assertNotEqual(base_key(setup_edit), key)
        (self.root / "yarn.lock").write_bytes(b"lock v2\n")
        self.assertNotEqual(base_key(config), key)

    def test_warm_commands_parse_and_change_the_base_only_when_present(self) -> None:
        plain = self._load(MINIMAL)
        self.assertEqual(plain.warm, ())
        warm_text = MINIMAL.replace("[tasks.check]", '[warm]\nrun = ["yarn tsc --noEmit"]\n\n[tasks.check]')
        warmed = self._load(warm_text)
        self.assertEqual(warmed.warm, ("yarn tsc --noEmit",))
        self.assertNotEqual(base_key(warmed), base_key(plain))
        self.assertNotEqual(base_key(warmed), base_key(self._load(warm_text.replace("--noEmit", "-b"))))
        with self.assertRaisesRegex(ConfigError, "warm.run: needs at least 1 entry"):
            self._load(MINIMAL.replace("[tasks.check]", "[warm]\nrun = []\n\n[tasks.check]"))
        with self.assertRaisesRegex(ConfigError, "warm"):
            self._load(MINIMAL.replace("[tasks.check]", '[warm]\nrun = ["x"]\nwhen = "always"\n\n[tasks.check]'))

    def test_load_config_reads_offload_toml(self) -> None:
        (self.root / "offload.toml").write_text(MINIMAL)
        config = load_config(self.root)
        self.assertEqual(config.root, self.root)
        self.assertEqual(set(config.tasks), {"check"})

    def test_load_config_requires_offload_toml(self) -> None:
        with self.assertRaisesRegex(ConfigError, "no offload.toml at"):
            load_config(self.root)

    def test_parse_duration(self) -> None:
        self.assertEqual(parse_duration("90s"), 90)
        self.assertEqual(parse_duration("20m"), 1200)
        self.assertEqual(parse_duration("2h"), 7200)
        for text in ["20", "1.5m", "20d", "20M", "", "0s", "soon"]:
            with self.subTest(text=text):
                with self.assertRaises(ConfigError):
                    parse_duration(text)


class PolicyTest(unittest.TestCase):
    def test_run_rules_deny_all_then_allow_egress(self) -> None:
        self.assertEqual(
            run_network_rules(WORKER),
            [
                {"domain": "*", "action": "deny"},
                {"domain": "registry.npmjs.org", "action": "allow"},
            ],
        )

    def test_setup_rules_add_setup_egress(self) -> None:
        self.assertEqual(
            setup_network_rules(WORKER),
            [
                {"include": "defaults"},
                {"domain": "pypi.org", "action": "allow"},
                {"domain": "registry.npmjs.org", "action": "allow"},
            ],
        )

    def test_policy_hash_tracks_memory_and_egress(self) -> None:
        base = policy_hash(WORKER)
        self.assertNotEqual(base, policy_hash(replace(WORKER, memory_mb=8192)))
        self.assertNotEqual(base, policy_hash(replace(WORKER, egress=())))


class IdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_token_is_dashless_and_keeps_truncated_names_apart(self) -> None:
        first = token("workstation-a", "workstation-a", 10)
        second = token("workstation-b", "workstation-b", 10)
        self.assertTrue(first.startswith("workstatio"))
        self.assertNotIn("-", first)
        self.assertNotEqual(first, second)
        self.assertRegex(token("!!!", "!!!", 5), r"^[0-9a-f]{4}$")

    def test_host_prefixes_do_not_overlap(self) -> None:
        dev = worker_prefix(token("dev", "dev", 10), None)
        laptop = worker_name(token("dev-laptop", "dev-laptop", 10), "repo1234", 1)
        self.assertFalse(laptop.startswith(dev))

    def test_host_slug_prefers_off_host(self) -> None:
        with mock.patch.dict(os.environ, {"OFF_HOST": "Ubuntu Box"}):
            self.assertRegex(host_slug(), r"^ubuntubox[0-9a-f]{4}$")

    def test_repo_slug_falls_back_to_directory_name(self) -> None:
        repo = self.root / "My Repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        self.assertRegex(repo_slug(repo), r"^myrepo[0-9a-f]{4}$")

    def test_repo_slug_reads_origin(self) -> None:
        repo = self.root / "checkout"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "remote",
                "add",
                "origin",
                "git@github.com:thiago-preischadt/claudio-estudos.git",
            ],
            check=True,
        )
        self.assertRegex(repo_slug(repo), r"^claudioestudos[0-9a-f]{4}$")
        other = self.root / "fork"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        subprocess.run(
            ["git", "-C", str(other), "remote", "add", "origin", "git@github.com:someone/claudio-estudos.git"],
            check=True,
        )
        self.assertNotEqual(repo_slug(repo), repo_slug(other))

    def test_worker_names(self) -> None:
        self.assertEqual(worker_name("box", "repo", 1), "off-box-repo-1")
        self.assertEqual(worker_prefix("box", "repo"), "off-box-repo-")
        self.assertEqual(worker_prefix("box", None), "off-box-")


class StateTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name)
        patcher = mock.patch.dict(os.environ, {"XDG_STATE_HOME": temporary.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_state_root_follows_xdg_state_home(self) -> None:
        self.assertEqual(state_root(), self.state / "off")

    def test_state_root_defaults_under_home(self) -> None:
        with mock.patch.dict(os.environ):
            os.environ.pop("XDG_STATE_HOME")
            self.assertEqual(state_root(), Path.home() / ".local" / "state" / "off")

    def test_paths_live_under_state_root(self) -> None:
        off = self.state / "off"
        self.assertEqual(lock_path("off-a"), off / "locks" / "off-a.lock")
        self.assertEqual(artifact_root("repo", "run1"), off / "artifacts" / "repo" / "run1")
        self.assertEqual(
            artifacts_dir("repo", "run1", 2), off / "artifacts" / "repo" / "run1" / "2"
        )
        self.assertTrue((off / "artifacts" / "repo" / "run1" / "2").is_dir())
        self.assertEqual(run_log("run1", 2), off / "runs" / "run1.2.log")
        self.assertEqual(done_marker("run1", 2), off / "runs" / "run1.2.done")

    def test_new_run_id_shape(self) -> None:
        self.assertRegex(new_run_id("check"), r"^\d{8}-\d{6}-check-[0-9a-f]{4}$")

    def test_cache_round_trip(self) -> None:
        self.assertIsNone(read_cache("off-a"))
        cache = WorkerCache(
            base_key="base-a",
            base_checkpoint="cp-1",
            policy_hash="policy-a",
            last_used=1.5,
        )
        write_cache("off-a", cache)
        self.assertEqual(read_cache("off-a"), cache)
        delete_cache("off-a")
        self.assertIsNone(read_cache("off-a"))
        delete_cache("off-a")

    def test_cache_without_clean_key_loads_as_not_clean(self) -> None:
        cache = WorkerCache(
            base_key="base-a",
            base_checkpoint="cp-1",
            policy_hash="policy-a",
            last_used=1.5,
            clean=True,
        )
        write_cache("off-a", cache)
        path = self.state / "off" / "workers" / "off-a.json"
        record = json.loads(path.read_text())
        del record["clean"]
        path.write_text(json.dumps(record))
        self.assertEqual(read_cache("off-a"), replace(cache, clean=False))
        delete_cache("off-a")

    def test_records_append_and_read(self) -> None:
        self.assertEqual(read_records(), [])
        append_record({"run": "r1", "exit": 0})
        append_record({"run": "r2", "exit": 124})
        self.assertEqual(read_records(), [{"run": "r1", "exit": 0}, {"run": "r2", "exit": 124}])

    def test_lease_is_exclusive_and_reacquirable(self) -> None:
        lease = Lease(lock_path("off-a"))
        self.assertTrue(lease.try_acquire())
        self.assertFalse(Lease(lock_path("off-a")).try_acquire())
        with self.assertRaisesRegex(RuntimeError, "already held"):
            lease.acquire()
        lease.release()
        again = Lease(lock_path("off-a"))
        self.assertTrue(again.try_acquire())
        again.release()

    def test_lease_context_manager_holds_lock(self) -> None:
        with Lease(lock_path("off-b")):
            self.assertFalse(Lease(lock_path("off-b")).try_acquire())
        probe = Lease(lock_path("off-b"))
        self.assertTrue(probe.try_acquire())
        probe.release()

    def test_lease_workers_prefers_free_workers_in_order(self) -> None:
        leases = lease_workers(["off-a", "off-b", "off-c"], 2)
        self.assertEqual([name for name, _ in leases], ["off-a", "off-b"])
        for _, lease in leases:
            lease.release()

    def test_lease_workers_skips_held_worker(self) -> None:
        holder = Lease(lock_path("off-a"))
        self.assertTrue(holder.try_acquire())
        self.addCleanup(holder.release)
        leases = lease_workers(["off-a", "off-b"], 1)
        self.assertEqual([name for name, _ in leases], ["off-b"])
        for _, lease in leases:
            lease.release()

    def test_lease_workers_waits_when_all_busy(self) -> None:
        holder = Lease(lock_path("off-a"))
        self.assertTrue(holder.try_acquire())
        self.addCleanup(holder.release)
        result: list[list[tuple[str, Lease]]] = []
        waiter = threading.Thread(
            target=lambda: result.append(lease_workers(["off-a"], 1)), daemon=True
        )
        waiter.start()
        waiter.join(0.2)
        self.assertTrue(waiter.is_alive())
        holder.release()
        waiter.join(5)
        self.assertFalse(waiter.is_alive())
        self.assertEqual([name for name, _ in result[0]], ["off-a"])
        for _, lease in result[0]:
            lease.release()

    def test_lease_workers_rejects_bad_requests(self) -> None:
        with self.assertRaises(ValueError):
            lease_workers(["off-a", "off-a"], 1)
        with self.assertRaises(ValueError):
            lease_workers(["off-a"], 2)


if __name__ == "__main__":
    unittest.main()
