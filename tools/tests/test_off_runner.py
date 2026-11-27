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
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local" / "share" / "off"))

from offload import runner
from offload.cli import main
from offload.config import load_config
from offload.identity import host_slug, repo_slug, worker_name
from offload.sprites import Sprites
from offload.state import Lease, lease_workers, lock_path

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
        state["sprites"][name] = {"checkpoints": []}
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
            cp_id = f"v{len(sprite['checkpoints']) + 2}"
            shutil.copytree(home, ROOT / f"{name}.cp" / cp_id)
            sprite["checkpoints"].append({"id": cp_id, "comment": json.loads(option(curl, "-d"))["comment"]})
            complete(f"Checkpoint {cp_id} created")
        elif path.endswith("/restore"):
            cp_id = path.split("/")[2]
            shutil.rmtree(home)
            shutil.copytree(ROOT / f"{name}.cp" / cp_id, home)
            complete(f"Restored {cp_id}")
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
        sys.exit(subprocess.run(argv, cwd=cwd, env=env).returncode)
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
    """
).lstrip()


def _reset_inline(_launcher: Path, name: str, checkpoint_id: str) -> None:
    runner.reset_worker(Sprites(), name, checkpoint_id)


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

    def test_run_waits_for_a_busy_built_worker_instead_of_building_another(self) -> None:
        self.assertEqual(self.off("run", "ok")[0], 0)
        holder = Lease(lock_path(self.workers[0]))
        self.assertTrue(holder.try_acquire())
        threading.Timer(0.5, holder.release).start()
        code, output = self.off("run", "ok")
        self.assertEqual(code, 0, output)
        creates = [call[1] for call in self.calls() if call[0] == "create"]
        self.assertEqual(creates, [self.workers[0]])

    def test_exec_runs_an_ad_hoc_command_and_keeps_its_exit_code(self) -> None:
        code, output = self.off("exec", "--", "echo hi && exit 4")
        self.assertEqual(code, 4, output)
        self.assertIn("hi", output)

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


if __name__ == "__main__":
    unittest.main()
