import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local" / "share" / "off"))

from offload import runner
from offload.cli import main
from offload.config import OffloadConfig, load_config
from offload.identity import host_slug, repo_slug, worker_name
from offload.sprites import Sprites
from offload.state import Lease, lease_workers, lock_path, read_cache, write_cache

FAKE_SPRITE = textwrap.dedent(
    r'''
    #!/usr/bin/env python3
    import fcntl, json, os, shutil, subprocess, sys
    from pathlib import Path

    STATE = Path(os.environ["FAKE_SPRITE_STATE"])
    ROOT = Path(os.environ["FAKE_SPRITE_ROOT"])

    def load():
        return json.loads(STATE.read_text()) if STATE.exists() else {"sprites": {}, "calls": []}

    def save(state):
        STATE.write_text(json.dumps(state))

    def option(args, flag):
        return args[args.index(flag) + 1] if flag in args else None

    def options(args, flag):
        return [args[index + 1] for index, arg in enumerate(args) if arg == flag]

    def remap(text, name):
        base = ROOT / name
        return (
            text.replace("/home/sprite", str(base / "home" / "sprite"))
            .replace("/tmp/off.env", str(base / "off.env"))
            .replace("/tmp/off.files", str(base / "off.files"))
        )

    def complete(message):
        print(json.dumps({"type": "info", "data": message, "time": "t"}))
        print(json.dumps({"type": "complete", "data": message, "time": "t"}))

    def take_checkpoint(sprite, name, home, comment):
        cp_id = f"v{sprite['next_id']}"
        sprite["next_id"] += 1
        shutil.copytree(home, ROOT / f"{name}.cp" / cp_id)
        sprite["checkpoints"].append({"id": cp_id, "comment": comment})
        return cp_id

    lock = open(str(STATE) + ".lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    args = sys.argv[1:]
    state = load()
    command = args[0]
    name = option(args, "-s")
    if command == "list":
        prefix = option(args, "--prefix") or ""
        sprites = [
            {"name": n, "status": "cold", "url_settings": {"auth": "sprite"}}
            for n in sorted(state["sprites"]) if n.startswith(prefix)
        ]
        print(json.dumps({"sprites": sprites, "org": {}}))
    elif command == "create":
        name = args[-1]
        state["sprites"][name] = {"checkpoints": [], "next_id": 2}
        (ROOT / name / "home" / "sprite").mkdir(parents=True, exist_ok=True)
        state["calls"].append(["create", name])
    elif command == "destroy":
        name = args[-1]
        state["sprites"].pop(name, None)
        shutil.rmtree(ROOT / name, ignore_errors=True)
        shutil.rmtree(ROOT / f"{name}.cp", ignore_errors=True)
        state["calls"].append(["destroy", name])
    elif command == "config":
        pass
    elif command == "api":
        path = args[args.index("--") - 1]
        curl = args[args.index("--") + 1:]
        method = option(curl, "-X") or "GET"
        sprite = state["sprites"][name]
        home = ROOT / name / "home" / "sprite"
        state["calls"].append([method, path, name])
        marker = os.environ.get("FAKE_SPRITE_FAIL_CHECKPOINTS_ONCE", "")
        if path == "/checkpoints" and marker and not Path(marker).exists():
            Path(marker).touch()
            print("checkpoints unavailable", file=sys.stderr)
            sys.exit(22)
        if path == "/checkpoints":
            print(json.dumps([{"id": "Current"}] + sprite["checkpoints"]))
        elif path == "/checkpoint":
            cp_id = take_checkpoint(sprite, name, home, json.loads(option(curl, "-d"))["comment"])
            complete(f"Checkpoint {cp_id} created")
        elif path.endswith("/restore"):
            cp_id = path.split("/")[2]
            if not (ROOT / f"{name}.cp" / cp_id).is_dir():
                print(f"checkpoint {cp_id} not found", file=sys.stderr)
                sys.exit(22)
            take_checkpoint(sprite, name, home, f"pre-restore {sprite['next_id']}")
            shutil.rmtree(home)
            shutil.copytree(ROOT / f"{name}.cp" / cp_id, home)
            complete(f"Restored {cp_id}")
        elif method == "DELETE":
            cp_id = path.split("/")[2]
            sprite["checkpoints"] = [cp for cp in sprite["checkpoints"] if cp["id"] != cp_id]
            shutil.rmtree(ROOT / f"{name}.cp" / cp_id)
        else:
            print("{}")
    elif command == "exec":
        for upload in options(args, "--file"):
            source, dest = upload.split(":", 1)
            shutil.copy(source, remap(dest, name))
        cwd = remap(option(args, "--dir") or "/home/sprite", name)
        argv = [remap(part, name) for part in args[args.index("--") + 1:]]
        state["calls"].append(["exec", name, *argv])
        drops = int(os.environ.get("FAKE_SPRITE_DROP", "0"))
        if any("__off_exit__" in part for part in argv) and state.get("dropped", 0) < drops:
            state["dropped"] = state.get("dropped", 0) + 1
            save(state)
            sys.exit(255)
        save(state)
        fcntl.flock(lock, fcntl.LOCK_UN)
        env = {**os.environ, "HOME": str(ROOT / name / "home" / "sprite")}
        code = subprocess.run(argv, cwd=cwd, env=env).returncode
        after = os.environ.get("FAKE_SPRITE_EXIT_AFTER")
        if after and any("__off_exit__" in part for part in argv):
            sys.exit(int(after))
        sys.exit(code)
    save(state)
    '''
).lstrip()

FAKE_RSYNC = textwrap.dedent(
    r'''
    #!/usr/bin/env python3
    import os, sys
    from pathlib import Path

    ROOT = Path(os.environ["FAKE_SPRITE_ROOT"])
    args = sys.argv[1:]
    at = args.index("-e")
    shell = args[at + 1].split()
    name = shell[shell.index("-s") + 1]
    del args[at:at + 2]
    home = str(ROOT / name / "home" / "sprite")
    local = [arg.removeprefix("env:").replace("/home/sprite", home) if arg.startswith("env:") else arg for arg in args]
    failures = ROOT / "rsync-failures"
    failed = int(failures.read_text()) if failures.exists() else 0
    if failed < int(os.environ.get("FAKE_RSYNC_FAILURES", "0")):
        failures.write_text(str(failed + 1))
        sys.exit(12)
    os.execv(os.environ["REAL_RSYNC"], [os.environ["REAL_RSYNC"], *local])
    '''
).lstrip()

OFFLOAD_TOML = textwrap.dedent(
    """
    version = 1

    [worker]
    max = 2

    [setup]
    inputs = ["package.json"]
    run = ["echo setup-ran && ls -A > ../setup-saw"]

    [env]
    pass = ["OFF_TEST_TOKEN"]

    [tasks.ok]
    run = "echo hello from $OFF_SHARD and $OFF_TEST_TOKEN"
    timeout = "5m"

    [tasks.brief]
    run = "echo brief"
    timeout = "1m"

    [tasks.tree]
    run = "find . -not -path './.git*' | sort; if [ -L lib ]; then echo lib-is-link; fi"
    timeout = "1m"

    [tasks.fail]
    run = "exit 3"
    timeout = "1m"

    [tasks.slow]
    run = "sleep 5"
    timeout = "1s"

    [tasks.two]
    run = "echo shard=$OFF_SHARD/$OFF_SHARDS"
    timeout = "1m"
    shards = 2

    [tasks.show]
    run = "find . -name '*.txt' -o -name '*.env' | sort"
    timeout = "1m"

    [tasks.spoof]
    run = "echo __off_exit__ 0; exit 3"
    timeout = "1m"

    [tasks.background]
    run = "(sleep 0.3; echo server stopped) & echo ok"
    timeout = "1m"

    [tasks.fan]
    timeout = "1m"

    [tasks.fan.parallel]
    quick = "echo quick-done"
    slow = "sleep 0.3; echo slow-done; exit 3"

    [tasks.stall]
    timeout = "2s"

    [tasks.stall.parallel]
    quick = "echo quick-done"
    hang = "sleep 97"

    [tasks.stall-local]
    where = "local"
    timeout = "1s"

    [tasks.stall-local.parallel]
    quick = "true"
    hang = "sleep 98"
    """
).lstrip()


def _reset_inline(_launcher: Path, name: str, checkpoint_id: str, root: Path) -> None:
    runner.reset_worker(Sprites(), name, checkpoint_id, root)


def stray_processes(pattern: str) -> list[str]:
    deadline = time.monotonic() + 5
    while True:
        found = subprocess.run(
            ["pgrep", "-fx", pattern], capture_output=True, text=True, check=False
        ).stdout.split()
        if not found or time.monotonic() > deadline:
            return found
        time.sleep(0.1)


class RunnerEndToEndTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="off-runner-test-"))
        real_rsync = shutil.which("rsync")
        if real_rsync is None:
            raise RuntimeError("the off runner tests need rsync on PATH")
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.tmp)], check=False)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for name, body in (("sprite", FAKE_SPRITE), ("rsync", FAKE_RSYNC)):
            script = bin_dir / name
            script.write_text(body)
            script.chmod(0o755)
        self.state_file = self.tmp / "fake-state.json"
        (self.tmp / "fake-root").mkdir()
        (self.tmp / "tmp").mkdir()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        (self.repo / "package.json").write_text('{"name": "t"}\n')
        (self.repo / "offload.toml").write_text(OFFLOAD_TOML)
        (self.repo / ".gitignore").write_text("secret.env\n*.log\n!keep.log\n")
        (self.repo / "untracked.txt").write_text("synced\n")
        (self.repo / "secret.env").write_text("TOKEN=x\n")
        (self.repo / "local-only.txt").write_text("excluded by info/exclude\n")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / ".git" / "info" / "exclude").write_text("local-only.txt\n")
        env = {
            "OFF_SPRITE_BIN": str(bin_dir / "sprite"),
            "OFF_ORG": "test",
            "OFF_HOST": "testhost",
            "OFF_TERN": "off",
            "OFF_TEST_TOKEN": "tok",
            "XDG_STATE_HOME": str(self.tmp / "state"),
            "FAKE_SPRITE_STATE": str(self.state_file),
            "FAKE_SPRITE_ROOT": str(self.tmp / "fake-root"),
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "REAL_RSYNC": real_rsync,
            "TMPDIR": str(self.tmp / "tmp"),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        previous = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)
        spawn = mock.patch.object(runner, "_spawn_reset", _reset_inline)
        spawn.start()
        self.addCleanup(spawn.stop)
        self.workers = [worker_name(host_slug(), repo_slug(self.repo), index) for index in (1, 2)]

    def off(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = main(list(argv))
        return code, out.getvalue()

    def calls(self) -> list[list[str]]:
        calls: list[list[str]] = json.loads(self.state_file.read_text())["calls"]
        return calls

    def test_task_exit_code_is_returned(self) -> None:
        code, output = self.off("run", "fail")
        self.assertEqual(code, 3, output)

    def test_env_is_delivered_and_shard_numbered(self) -> None:
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("hello from 1 and tok", output)

    def test_missing_pass_env_fails_before_creating_a_worker(self) -> None:
        with mock.patch.dict(os.environ):
            del os.environ["OFF_TEST_TOKEN"]
            code, output = self.off("run", "ok")
        self.assertEqual(code, runner.EXIT_OFF_ERROR, output)
        self.assertIn("OFF_TEST_TOKEN", output)
        self.assertFalse(self.state_file.exists())

    def test_setup_runs_once_and_later_runs_restore_the_base(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertEqual(self.off("run", "ok")[0], 0)
        calls = self.calls()
        setups = [call for call in calls if call[0] == "exec" and any("setup-ran" in part for part in call)]
        restores = [call for call in calls if call[0] == "POST" and call[1].endswith("/restore")]
        self.assertEqual(len(setups), 1)
        self.assertEqual(len(restores), 2)
        self.assertEqual([call[0] for call in calls].count("create"), 1)

    def test_bootstrap_locks_policies_before_the_base_checkpoint(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        posts = [call[1] for call in self.calls() if call[0] == "POST"]
        checkpoint = posts.index("/checkpoint")
        self.assertLess(posts.index("/policy/privileges"), checkpoint)
        self.assertLess(max(i for i, p in enumerate(posts[:checkpoint]) if p == "/policy/network"), checkpoint)
        self.assertNotIn("/policy/privileges", posts[checkpoint:])
        marker = runner.base_marker(load_config(self.repo))
        comments = json.loads(self.state_file.read_text())["sprites"][self.workers[0]]["checkpoints"]
        self.assertEqual([cp["comment"] for cp in comments], [marker])

    def test_restore_points_are_pruned_and_the_base_survives(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertEqual(self.off("run", "ok")[0], 0)
        cache = read_cache(self.workers[0])
        self.assertIsNotNone(cache)
        marker = runner.base_marker(load_config(self.repo))
        checkpoints = json.loads(self.state_file.read_text())["sprites"][self.workers[0]]["checkpoints"]
        self.assertEqual(checkpoints, [{"id": cache.base_checkpoint, "comment": marker}])

    def test_warm_run_makes_no_checkpoint_listing(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        before = len(self.calls())
        with mock.patch.object(runner, "_spawn_reset") as spawn:
            self.assertEqual(self.off("run", "ok")[0], 0)
        spawn.assert_called_once()
        self.assertNotIn(["GET", "/checkpoints", self.workers[0]], self.calls()[before:])

    def test_stale_cache_lists_checkpoints_again(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        cache = read_cache(self.workers[0])
        self.assertIsNotNone(cache)
        write_cache(self.workers[0], replace(cache, base_key="stale"))
        before = len(self.calls())
        with mock.patch.object(runner, "_spawn_reset"):
            self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertIn(["GET", "/checkpoints", self.workers[0]], self.calls()[before:])

    def test_sync_compresses_the_stream(self) -> None:
        argv = runner.sync_argv(load_config(self.repo), "sh", by_content=False)
        self.assertEqual(argv[:3], ["rsync", "-a", "-z"])

    def test_setup_change_rebuilds_the_worker(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        (self.repo / "package.json").write_text('{"name": "t", "version": "2"}\n')
        self.assertEqual(self.off("run", "ok")[0], 0)
        kinds = [call[0] for call in self.calls()]
        self.assertEqual(kinds.count("create"), 2)
        self.assertEqual(kinds.count("destroy"), 1)

    def test_shards_run_on_separate_workers(self) -> None:
        code, output = self.off("run", "two")
        self.assertEqual(code, 0, output)
        self.assertIn("shard=1/2", output)
        self.assertIn("shard=2/2", output)
        created = sorted(call[1] for call in self.calls() if call[0] == "create")
        self.assertEqual(created, self.workers)

    def test_timeout_returns_124(self) -> None:
        code, output = self.off("run", "slow")
        self.assertEqual(code, runner.EXIT_TIMEOUT, output)

    def test_parallel_task_runs_every_step(self) -> None:
        code, output = self.off("run", "fan")
        self.assertEqual(code, 3, output)
        self.assertIn("[quick] quick-done", output)
        self.assertIn("[slow] slow-done", output)
        self.assertIn("[quick] exited 0", output)
        self.assertIn("[slow] exited 3", output)

    def test_parallel_task_rejects_extra_args_before_leasing(self) -> None:
        code, output = self.off("run", "fan", "--", "extra")
        self.assertEqual(code, runner.EXIT_OFF_ERROR, output)
        self.assertIn("parallel tasks take no extra arguments", output)
        self.assertFalse(self.state_file.exists(), output)

    def test_parallel_timeout_stops_every_sprite_step(self) -> None:
        code, output = self.off("run", "stall")
        self.assertEqual(code, runner.EXIT_TIMEOUT, output)
        self.assertIn("[quick] quick-done", output)
        self.assertEqual(stray_processes("sleep 97"), [])

    def test_parallel_timeout_stops_every_local_step(self) -> None:
        code, output = self.off("run", "stall-local")
        self.assertEqual(code, runner.EXIT_TIMEOUT, output)
        self.assertEqual(stray_processes("sleep 98"), [])

    def test_plan_names_parallel_steps(self) -> None:
        code, output = self.off("plan", "fan")
        self.assertEqual(code, 0, output)
        self.assertIn("parallel: quick, slow", output)

    def test_sync_follows_git_rules(self) -> None:
        nested = self.repo / "nested"
        subprocess.run(["git", "init", "-q", str(nested)], check=True)
        (nested / ".gitignore").write_text("inner.env\n")
        (nested / "inner.env").write_text("TOKEN=y\n")
        (nested / "nested.txt").write_text("nested repo file\n")
        source = self.tmp / "sub-source"
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        (source / "sub.txt").write_text("submodule file\n")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "-C", str(source), "add", "."], check=True)
        subprocess.run([*git, "-C", str(source), "commit", "-qm", "init"], check=True)
        subprocess.run(
            [*git, "-c", "protocol.file.allow=always", "-C", str(self.repo), "submodule", "add", "-q", str(source), "sub"],
            check=True,
        )
        code, output = self.off("run", "show")
        self.assertEqual(code, 0, output)
        self.assertIn("./untracked.txt", output)
        self.assertIn("./sub/sub.txt", output)
        self.assertNotIn("nested", output)
        self.assertNotIn("secret.env", output)
        self.assertNotIn("local-only.txt", output)

    def test_task_output_cannot_fake_the_exit_code(self) -> None:
        code, output = self.off("run", "spoof")
        self.assertEqual(code, 3, output)
        self.assertIn("__off_exit__ 0", output)

    def test_output_after_the_task_exits_keeps_its_exit_code(self) -> None:
        code, output = self.off("run", "background")
        self.assertEqual(code, 0, output)
        self.assertIn("server stopped", output)

    def test_setup_sees_only_its_inputs(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        saw = self.tmp / "fake-root" / self.workers[0] / "home" / "sprite" / "setup-saw"
        self.assertEqual(saw.read_text(), "package.json\n")

    def test_base_holds_the_tree_but_no_ignored_files(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        snapshot = self.tmp / "fake-root" / f"{self.workers[0]}.cp" / "v2"
        self.assertTrue((snapshot / "work" / "untracked.txt").is_file())
        self.assertTrue((snapshot / "work" / "package.json").is_file())
        self.assertTrue((snapshot / ".off" / "base-files").is_file())
        leaked = [path for path in snapshot.rglob("*") if path.name in {"secret.env", "local-only.txt"}]
        self.assertEqual(leaked, [])

    def test_file_deleted_locally_disappears_on_the_worker(self) -> None:
        code, output = self.off("run", "show")
        self.assertEqual(code, 0, output)
        self.assertIn("./untracked.txt", output)
        (self.repo / "untracked.txt").unlink()
        code, output = self.off("run", "show")
        self.assertEqual(code, 0, output)
        self.assertNotIn("./untracked.txt", output)

    def use_warm(self, *lines: str, setup: str = "echo setup-ran && ls -A > ../setup-saw") -> None:
        warm = "[warm]\nrun = [" + ", ".join(json.dumps(line) for line in lines) + "]\n\n[env]"
        text = OFFLOAD_TOML.replace("[env]", warm).replace("echo setup-ran && ls -A > ../setup-saw", setup)
        (self.repo / "offload.toml").write_text(text)

    def base_snapshot(self) -> Path:
        cache = read_cache(self.workers[0])
        assert cache is not None
        return self.tmp / "fake-root" / f"{self.workers[0]}.cp" / cache.base_checkpoint / "work"

    def test_warm_caches_land_in_the_base(self) -> None:
        self.use_warm("echo primed > .tool-cache && echo warmed")
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("[warm] warmed", output)
        self.assertEqual((self.base_snapshot() / ".tool-cache").read_text(), "primed\n")

    def test_failing_warm_command_keeps_the_build(self) -> None:
        self.use_warm("echo partial > .tool-cache; exit 7")
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("exited 7; its cache is kept", output)
        self.assertTrue((self.base_snapshot() / ".tool-cache").exists())

    def test_drift_counts_files_that_differ_from_the_base(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        (self.repo / "untracked.txt").write_text("changed\n")
        (self.repo / "added.txt").write_text("new\n")
        self.assertEqual(self.off("run", "ok")[0], 0)
        cache = read_cache(self.workers[0])
        assert cache is not None
        self.assertEqual(cache.drift, 2)

    def test_only_another_checkout_compares_content(self) -> None:
        origin = ["git", "-C", str(self.repo), "remote", "add", "origin", "https://example.invalid/t.git"]
        subprocess.run(origin, check=True)
        self.workers = [worker_name(host_slug(), repo_slug(self.repo), index) for index in (1, 2)]
        syncs = self.record_syncs()
        for _ in range(2):
            self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertNotIn("--checksum", syncs[-1])
        other = self.tmp / "other"
        shutil.copytree(self.repo, other, symlinks=True)
        later = time.time() + 3600
        for path in other.rglob("*"):
            if ".git" not in path.relative_to(other).parts and path.is_file():
                os.utime(path, (later, later))
        os.chdir(other)
        self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertIn("--checksum", syncs[-1])
        self.assertEqual(self.drift(), 0)
        (other / "untracked.txt").write_text("changed in other\n")
        with mock.patch.object(runner, "REFRESH_AFTER_FILES", 1):
            self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertNotIn("--checksum", syncs[-1])
        self.assertEqual(self.drift(), 0)

    def test_a_base_from_an_unknown_checkout_is_retaken_once(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        cache = read_cache(self.workers[0])
        assert cache is not None
        write_cache(self.workers[0], replace(cache, base_root=""))
        syncs = self.record_syncs()
        self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertIn("--checksum", syncs[0])
        refreshed = read_cache(self.workers[0])
        assert refreshed is not None
        self.assertNotEqual(refreshed.base_checkpoint, cache.base_checkpoint)
        self.assertEqual(self.off("run", "ok")[0], 0)
        self.assertNotIn("--checksum", syncs[-1])

    def record_syncs(self) -> list[list[str]]:
        syncs: list[list[str]] = []
        real_rsync = runner._rsync

        def recording_rsync(argv: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
            if "--files-from=-" in argv:
                syncs.append(argv)
            return real_rsync(argv, stdin=stdin)

        patcher = mock.patch.object(runner, "_rsync", recording_rsync)
        patcher.start()
        self.addCleanup(patcher.stop)
        return syncs

    def drift(self) -> int:
        cache = read_cache(self.workers[0])
        assert cache is not None
        return cache.drift

    def test_drift_past_the_threshold_refreshes_the_base(self) -> None:
        self.use_warm("cat untracked.txt > .tool-cache", setup="mkdir -p gen && echo out > gen/setup.txt")
        self.assertEqual(self.off("run", "ok")[0], 0)
        old = read_cache(self.workers[0])
        assert old is not None
        (self.repo / "untracked.txt").write_text("changed\n")
        (self.repo / "added.txt").write_text("new\n")
        with mock.patch.object(runner, "REFRESH_AFTER_FILES", 1):
            code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        new = read_cache(self.workers[0])
        assert new is not None
        self.assertNotEqual(new.base_checkpoint, old.base_checkpoint)
        self.assertEqual((new.drift, new.clean), (0, True))
        checkpoints = json.loads(self.state_file.read_text())["sprites"][self.workers[0]]["checkpoints"]
        self.assertEqual([cp["id"] for cp in checkpoints], [new.base_checkpoint])
        snapshot = self.base_snapshot()
        self.assertEqual((snapshot / "untracked.txt").read_text(), "changed\n")
        self.assertEqual((snapshot / ".tool-cache").read_text(), "changed\n")
        self.assertTrue((snapshot / "added.txt").exists())
        self.assertTrue((snapshot / "gen" / "setup.txt").exists())
        (self.repo / "added.txt").unlink()
        code, output = self.off("run", "tree")
        self.assertEqual(code, 0, output)
        self.assertNotIn("./added.txt", output)
        self.assertIn("./gen/setup.txt", output)
        self.assertIn(["POST", f"/checkpoints/{new.base_checkpoint}/restore", self.workers[0]], self.calls())

    def test_failed_refresh_keeps_the_old_base(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        old = read_cache(self.workers[0])
        assert old is not None
        (self.repo / "untracked.txt").write_text("changed\n")
        real_sync = runner._sync_up
        calls: list[str] = []

        def failing_refresh_sync(
            sprites: Sprites,
            config: OffloadConfig,
            name: str,
            files: list[str],
            emit: Callable[[str], None],
            *,
            by_content: bool,
        ) -> int:
            calls.append(name)
            if len(calls) == 2:
                raise runner.OffError("sync dropped")
            return real_sync(sprites, config, name, files, emit, by_content=by_content)

        with mock.patch.object(runner, "REFRESH_AFTER_FILES", 1), mock.patch.object(runner, "_sync_up", failing_refresh_sync):
            code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("base refresh failed", output)
        cache = read_cache(self.workers[0])
        assert cache is not None
        self.assertEqual((cache.base_checkpoint, cache.clean), (old.base_checkpoint, True))
        code, output = self.off("run", "show")
        self.assertEqual(code, 0, output)
        self.assertIn("./untracked.txt", output)

    def test_missing_cached_base_fails_once_then_lists_checkpoints_again(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        cache = read_cache(self.workers[0])
        assert cache is not None
        write_cache(self.workers[0], replace(cache, base_checkpoint="v99", clean=False))
        with mock.patch.object(runner, "_spawn_reset"):
            code, output = self.off("run", "ok")
        self.assertEqual(code, runner.EXIT_OFF_ERROR, output)
        self.assertIsNone(read_cache(self.workers[0]))
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("hello from 1", output)

    def test_run_waits_for_a_resetting_worker_instead_of_building_another(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        holder = Lease(lock_path(self.workers[0]))
        self.assertTrue(holder.try_acquire())
        marker = lock_path(self.workers[0]).with_suffix(".resetting")
        marker.write_text(str(os.getpid()))

        def finish_reset() -> None:
            holder.release()
            marker.unlink()

        threading.Timer(0.5, finish_reset).start()
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        creates = [call[1] for call in self.calls() if call[0] == "create"]
        self.assertEqual(creates, [self.workers[0]])

    def test_run_builds_another_worker_when_the_built_one_is_busy_with_a_run(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        holder = Lease(lock_path(self.workers[0]))
        self.assertTrue(holder.try_acquire())
        self.addCleanup(holder.release)
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        creates = [call[1] for call in self.calls() if call[0] == "create"]
        self.assertEqual(creates, self.workers)

    def test_directory_replaced_by_a_symlink_keeps_syncing(self) -> None:
        (self.repo / "lib").mkdir()
        (self.repo / "lib" / "a.py").write_text("old\n")
        self.assertEqual(self.off("run", "tree")[0], 0)
        shutil.rmtree(self.repo / "lib")
        (self.repo / "vendor" / "lib").mkdir(parents=True)
        (self.repo / "vendor" / "lib" / "a.py").write_text("new\n")
        (self.repo / "lib").symlink_to("vendor/lib")
        for _ in range(2):
            code, output = self.off("run", "tree")
            self.assertEqual(code, 0, output)
            self.assertIn("./vendor/lib/a.py", output)
            self.assertIn("lib-is-link", output)

    def test_deleted_package_leaves_no_empty_directory(self) -> None:
        (self.repo / "old_pkg").mkdir()
        (self.repo / "old_pkg" / "__init__.py").write_text("")
        self.assertEqual(self.off("run", "tree")[0], 0)
        shutil.rmtree(self.repo / "old_pkg")
        code, output = self.off("run", "tree")
        self.assertEqual(code, 0, output)
        self.assertNotIn("old_pkg", output)

    def test_result_after_a_dropped_client_is_kept_without_a_rerun(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_SPRITE_EXIT_AFTER": "255"}):
            code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertEqual(output.count("hello from 1"), 1, output)
        self.assertNotIn("retrying", output)

    def test_lost_connection_is_not_retried_without_time_left(self) -> None:
        with mock.patch.dict(os.environ, {"FAKE_SPRITE_DROP": "1"}):
            code, output = self.off("run", "brief")
        self.assertEqual(code, runner.EXIT_OFF_ERROR, output)
        self.assertIn("not enough time left to retry", output)

    def test_exec_runs_an_ad_hoc_command_and_keeps_its_exit_code(self) -> None:
        code, output = self.off("exec", "--", "python3 -m unittest no_such_test_module")
        self.assertEqual(code, 1, output)

    def test_exec_refuses_a_light_command_before_touching_the_sprite(self) -> None:
        code, output = self.off("exec", "--", "uv --version")
        self.assertEqual(code, 64, output)
        self.assertIn("refusing to offload 'uv --version'", output)
        self.assertFalse(self.state_file.exists())

    def test_lost_connection_is_an_off_error_and_stops_the_task(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        with mock.patch.dict(os.environ, {"FAKE_SPRITE_DROP": "2"}):
            code, output = self.off("run", "ok")
        self.assertEqual(code, runner.EXIT_OFF_ERROR, output)
        self.assertIn("retrying once", output)
        self.assertIn("lost the task", output)
        restores = [call for call in self.calls() if call[0] == "POST" and call[1].endswith("/restore")]
        self.assertEqual(len(restores), 3)

    def test_lost_connection_is_retried_once(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        with mock.patch.dict(os.environ, {"FAKE_SPRITE_DROP": "1"}):
            code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("retrying once", output)
        self.assertIn("hello from 1", output)

    def test_sync_failure_is_retried(self) -> None:
        env = {"FAKE_RSYNC_FAILURES": "1"}
        with mock.patch.dict(os.environ, env), mock.patch.object(runner, "SYNC_RETRY_DELAY_S", 0):
            code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertIn("rsync exit 12); retrying", output)

    def test_sync_gives_up_after_three_attempts(self) -> None:
        env = {"FAKE_RSYNC_FAILURES": "3"}
        with mock.patch.dict(os.environ, env), mock.patch.object(runner, "SYNC_RETRY_DELAY_S", 0):
            code, output = self.off("run", "ok")
        self.assertEqual(code, runner.EXIT_OFF_ERROR, output)
        self.assertIn("sync to", output)

    def test_checkpoints_failure_is_retried(self) -> None:
        marker = self.tmp / "checkpoints-failed"
        with mock.patch.dict(os.environ, {"FAKE_SPRITE_FAIL_CHECKPOINTS_ONCE": str(marker)}):
            code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        self.assertTrue(marker.exists())

    def test_exec_timeout_above_the_cap_is_a_usage_error(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
            main(["exec", "--timeout", "7h", "--", "true"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("exceeds the 6h maximum", err.getvalue())


class LeaseOrderTest(unittest.TestCase):
    def test_two_runs_wanting_every_worker_do_not_deadlock(self) -> None:
        state = tempfile.TemporaryDirectory()
        self.addCleanup(state.cleanup)
        names = ["w1", "w2"]
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": state.name}):
            blocker = Lease(lock_path("w2"))
            self.assertTrue(blocker.try_acquire())
            finished: list[str] = []

            def run(label: str) -> None:
                for _, lease in lease_workers(names, 2):
                    lease.release()
                finished.append(label)

            threads = [threading.Thread(target=run, args=(label,)) for label in ("a", "b")]
            for thread in threads:
                thread.start()
            time.sleep(0.3)
            blocker.release()
            for thread in threads:
                thread.join(timeout=10)
        self.assertEqual(sorted(finished), ["a", "b"])


class SpawnResetTest(unittest.TestCase):
    def test_reset_child_is_not_tracked_as_agent_work(self) -> None:
        state = self.enterContext(tempfile.TemporaryDirectory())
        seen = Path(state) / "seen-env.json"
        launcher = Path(state) / "launcher.py"
        launcher.write_text(
            f"import json, os\nopen({str(seen)!r}, 'w').write(json.dumps(dict(os.environ)))\n"
        )
        env = {"XDG_STATE_HOME": state, "OMP_BASH_SESSION": "session-1", "OFF_ORG": "kept"}
        with mock.patch.dict(os.environ, env):
            child = runner._spawn_reset(launcher, "worker", "cp", Path(state))
        self.assertEqual(child.wait(timeout=10), 0)
        child_env = json.loads(seen.read_text())
        self.assertNotIn("OMP_BASH_SESSION", child_env)
        self.assertEqual(child_env["OFF_ORG"], "kept")


class PruneScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root / "work"
        self.work.mkdir()

    def prune(self, base: list[str], current: list[str] | None) -> subprocess.CompletedProcess[str]:
        (self.root / "base").write_bytes(b"\0".join(path.encode() for path in base))
        if current is not None:
            (self.root / "run").write_bytes(b"\0".join(path.encode() for path in current))
        argv = [sys.executable, "-c", runner.PRUNE_SCRIPT, str(self.root / "base"), str(self.root / "run")]
        return subprocess.run(argv, cwd=self.work, capture_output=True, text=True)

    def test_missing_run_list_deletes_nothing(self) -> None:
        (self.work / "keep.txt").write_text("x")
        completed = self.prune(["keep.txt"], None)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue((self.work / "keep.txt").exists())

    def test_removes_only_stale_paths_including_odd_names(self) -> None:
        odd = ["-rf", "new\nline.txt", "pkg/mod.py"]
        (self.work / "pkg").mkdir()
        for path in [*odd, "keep.txt"]:
            (self.work / path).write_text("x")
        completed = self.prune([*odd, "keep.txt"], ["keep.txt"])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(sorted(path.name for path in self.work.iterdir()), ["keep.txt"])

    def test_never_deletes_through_a_symlinked_parent(self) -> None:
        (self.work / "vendor" / "lib").mkdir(parents=True)
        (self.work / "vendor" / "lib" / "a.py").write_text("live")
        (self.work / "lib").symlink_to("vendor/lib")
        completed = self.prune(["lib/a.py"], ["lib", "vendor/lib/a.py"])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual((self.work / "vendor" / "lib" / "a.py").read_text(), "live")


if __name__ == "__main__":
    unittest.main()
