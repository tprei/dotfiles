import io
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".local" / "share" / "off"))

from offload.state import done_marker, run_log
from offload.tern import TernTarget, detect_tern, viewer_argv, watch


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
        self.assertEqual(argv, ["/usr/local/bin/off", "watch", "run-1", "--shard", "2"])


class DetectTernTest(unittest.TestCase):
    def test_off_disables_viewers_without_probing(self) -> None:
        with (
            mock.patch.dict(os.environ, {"OFF_TERN": "off"}),
            mock.patch("offload.tern.subprocess.run") as run,
        ):
            self.assertIsNone(detect_tern())
        run.assert_not_called()

    def test_wsl_looks_for_windows_binary(self) -> None:
        with (
            mock.patch.dict(os.environ, {"OFF_TERN": "auto", "WSL_DISTRO_NAME": "Ubuntu"}),
            mock.patch("offload.tern.shutil.which", return_value=None) as which,
        ):
            self.assertIsNone(detect_tern())
        which.assert_called_once_with("tern.exe")


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


if __name__ == "__main__":
    unittest.main()
