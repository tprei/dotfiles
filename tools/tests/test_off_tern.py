import io
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local" / "share" / "off"))

from offload.cli import main
from offload.state import done_marker, run_log, run_pid
from offload.tern import TernTarget, detect_tern, open_viewers, viewer_argv, watch


class ViewerArgvTest(unittest.TestCase):
    def test_wsl_runs_watch_through_wsl_exe(self) -> None:
        argv = viewer_argv(
            TernTarget(binary="tern.exe", wsl_distro="Ubuntu"),
            Path("/home/prei/.local/bin/off"),
            Path("/home/prei/repo"),
            "run-1",
            2,
        )
        self.assertEqual(
            argv,
            [
                "wsl.exe",
                "-d",
                "Ubuntu",
                "--cd",
                "/home/prei/repo",
                "--",
                "/home/prei/.local/bin/off",
                "watch",
                "run-1",
                "--shard",
                "2",
                "--viewer",
            ],
        )

    def test_native_runs_watch_directly(self) -> None:
        argv = viewer_argv(
            TernTarget(binary="tern", wsl_distro=None),
            Path("/usr/local/bin/off"),
            Path("/home/prei/repo"),
            "run-1",
            2,
        )
        self.assertEqual(argv, ["/usr/local/bin/off", "watch", "run-1", "--shard", "2", "--viewer"])


class DetectTernTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stderr = self.enterContext(mock.patch("offload.tern.sys.stderr"))
        self.stderr.isatty.return_value = True
        self.enterContext(
            mock.patch.dict(os.environ, {"OFF_TERN": "auto", "WSL_DISTRO_NAME": "Ubuntu"}, clear=True)
        )

    def test_off_disables_viewers_without_probing(self) -> None:
        with (
            mock.patch.dict(os.environ, {"OFF_TERN": "off"}),
            mock.patch("offload.tern.subprocess.run") as run,
        ):
            self.assertIsNone(detect_tern())
        run.assert_not_called()

    def test_wsl_looks_for_windows_binary(self) -> None:
        with mock.patch("offload.tern.shutil.which", return_value=None) as which:
            self.assertIsNone(detect_tern())
        which.assert_called_once_with("tern.exe")

    def test_terminal_probes_tern_and_returns_target(self) -> None:
        with (
            mock.patch("offload.tern.shutil.which", return_value="tern.exe"),
            mock.patch(
                "offload.tern.subprocess.run",
                return_value=subprocess.CompletedProcess(["tern.exe"], 0, "{}", ""),
            ) as run,
        ):
            self.assertEqual(detect_tern(), TernTarget(binary="tern.exe", wsl_distro="Ubuntu"))
        self.assertEqual(run.call_args.args[0], ["tern.exe", "ls", "--json"])

    def test_non_terminal_stderr_gets_no_viewers(self) -> None:
        self.stderr.isatty.return_value = False
        with (
            mock.patch("offload.tern.shutil.which", return_value="tern.exe") as which,
            mock.patch("offload.tern.subprocess.run") as run,
        ):
            self.assertIsNone(detect_tern())
        which.assert_not_called()
        run.assert_not_called()

    def test_agent_shell_gets_no_viewers(self) -> None:
        with (
            mock.patch.dict(os.environ, {"OMP_BASH_SESSION": "session-1"}),
            mock.patch("offload.tern.shutil.which", return_value="tern.exe") as which,
            mock.patch("offload.tern.subprocess.run") as run,
        ):
            self.assertIsNone(detect_tern())
        which.assert_not_called()
        run.assert_not_called()


class OpenViewersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.target = TernTarget(binary="tern.exe", wsl_distro="Ubuntu")
        self.enterContext(mock.patch("offload.tern.detect_tern", return_value=self.target))
        self.tern = self.enterContext(mock.patch("offload.tern._tern", return_value=""))
        self.cwd = Path("/home/prei/repo")
        self.off = Path("/home/prei/.local/bin/off")

    def test_each_shard_gets_its_own_session_that_ends_on_success(self) -> None:
        run_id = "20261127-101010-build-ab12"
        open_viewers(run_id, "build", 2, self.cwd, self.off)
        self.assertEqual(
            [call.args[1] for call in self.tern.call_args_list],
            [
                [
                    "new",
                    "session",
                    f"off build ab12 {shard}/2",
                    "--end-on-success",
                    "--",
                    *viewer_argv(self.target, self.off, self.cwd, run_id, shard),
                ]
                for shard in (1, 2)
            ],
        )

    def test_single_shard_session_has_no_shard_suffix(self) -> None:
        run_id = "20261127-101010-build-ab12"
        open_viewers(run_id, "build", 1, self.cwd, self.off)
        self.assertEqual(
            [call.args[1] for call in self.tern.call_args_list],
            [
                [
                    "new",
                    "session",
                    "off build ab12",
                    "--end-on-success",
                    "--",
                    *viewer_argv(self.target, self.off, self.cwd, run_id, 1),
                ]
            ],
        )


class WatchTest(unittest.TestCase):
    def setUp(self) -> None:
        state = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(mock.patch.dict(os.environ, {"XDG_STATE_HOME": state}))
        self.log = run_log("run-x", 1)
        self.marker = done_marker("run-x", 1)

    def test_follows_log_until_marker_and_returns_exit_code(self) -> None:
        lines = [f"line {number}\n" for number in range(200)]

        def write_shard() -> None:
            time.sleep(0.1)
            with self.log.open("w") as handle:
                for line in lines:
                    handle.write(line)
                    handle.flush()
                    time.sleep(0.001)
            self.marker.write_text("3\n")

        writer = threading.Thread(target=write_shard)
        writer.start()
        out = io.StringIO()
        try:
            code = watch("run-x", 1, poll_s=0.01, out=out)
        finally:
            writer.join()
        self.assertEqual(code, 3)
        self.assertEqual(out.getvalue(), "".join(lines) + "off: shard 1 exited 3\n")

    def test_marker_without_log_reports_status_only(self) -> None:
        self.marker.write_text("125\n")
        out = io.StringIO()
        code = watch("run-x", 1, poll_s=0.01, out=out)
        self.assertEqual(code, 125)
        self.assertEqual(out.getvalue(), "off: shard 1 exited 125\n")

    def test_waits_for_exit_code_written_after_marker(self) -> None:
        self.log.write_text("done\n")
        self.marker.touch()

        def write_code() -> None:
            time.sleep(0.05)
            self.marker.write_text("4\n")

        writer = threading.Thread(target=write_code)
        writer.start()
        out = io.StringIO()
        try:
            code = watch("run-x", 1, poll_s=0.01, out=out)
        finally:
            writer.join()
        self.assertEqual(code, 4)
        self.assertEqual(out.getvalue(), "done\noff: shard 1 exited 4\n")

    def test_malformed_marker_exits_125(self) -> None:
        self.marker.write_text("oops\n")
        out = io.StringIO()
        code = watch("run-x", 1, poll_s=0.01, out=out)
        self.assertEqual(code, 125)
        self.assertIn("off: error: done marker", out.getvalue())

    def test_gives_up_when_the_run_process_died_without_a_marker(self) -> None:
        dead = subprocess.Popen(["true"])
        dead.wait()
        run_pid("run-x").write_text(str(dead.pid))
        self.log.write_text("partial\n")
        out = io.StringIO()
        code = watch("run-x", 1, poll_s=0.01, out=out)
        self.assertEqual(code, 125)
        self.assertIn("partial\n", out.getvalue())
        self.assertIn("ended without a result", out.getvalue())


class ViewerExitTest(unittest.TestCase):
    def test_viewer_exits_zero_whatever_the_shard_result(self) -> None:
        for code in (0, 3, 125):
            with self.subTest(code=code), mock.patch("offload.cli.watch", return_value=code):
                self.assertEqual(main(["watch", "run-x", "--viewer"]), 0)

    def test_watch_without_viewer_exits_with_the_shard_result(self) -> None:
        with mock.patch("offload.cli.watch", return_value=3):
            self.assertEqual(main(["watch", "run-x"]), 3)


if __name__ == "__main__":
    unittest.main()
