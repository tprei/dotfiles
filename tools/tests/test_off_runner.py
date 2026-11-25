import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local" / "share" / "off"))

from offload import runner
from offload.cli import main
from offload.config import load_config

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

    def remap(text, name):
        base = ROOT / name
        return text.replace("/home/sprite", str(base / "home" / "sprite")).replace("/tmp/off.env", str(base / "off.env"))

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
        upload = option(args, "--file")
        if upload:
            source, dest = upload.split(":", 1)
            shutil.copy(source, remap(dest, name))
        cwd = remap(option(args, "--dir") or "/home/sprite", name)
        argv = [remap(part, name) for part in args[args.index("--") + 1:]]
        state["calls"].append(["exec", name, *argv])
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
    import os, shutil, sys
    from pathlib import Path

    ROOT = Path(os.environ["FAKE_SPRITE_ROOT"])
    args = sys.argv[1:]
    shell = args[args.index("-e") + 1].split()
    name = shell[shell.index("-s") + 1]
    source, dest = args[-2], args[-1]

    def remote(path):
        return Path(path.removeprefix("env:").replace("/home/sprite", str(ROOT / name / "home" / "sprite")))

    if dest.startswith("env:"):
        shutil.copytree(source, remote(dest), dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    else:
        found = remote(source)
        if not found.exists():
            sys.exit(23)
        target = Path(dest) / found.name
        if found.is_dir():
            shutil.copytree(found, target, dirs_exist_ok=True)
        else:
            shutil.copy(found, target)
    '''
).lstrip()

OFFLOAD_TOML = textwrap.dedent(
    """
    version = 1

    [worker]
    max = 2

    [setup]
    inputs = ["package.json"]
    run = ["echo setup-ran"]

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
    """
).lstrip()


class RunnerEndToEndTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="off-runner-test-"))
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
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
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
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        previous = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, previous)

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
        comments = json.loads(self.state_file.read_text())["sprites"]["off-testhost-repo-1"]["checkpoints"]
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
        self.assertEqual(created, ["off-testhost-repo-1", "off-testhost-repo-2"])

    def test_timeout_returns_124(self) -> None:
        code, output = self.off("run", "slow")
        self.assertEqual(code, runner.EXIT_TIMEOUT, output)


if __name__ == "__main__":
    unittest.main()
