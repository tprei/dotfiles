import codecs
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from .state import done_marker, pid_alive, run_log, run_pid

_PROBE_TIMEOUT_S: Final = 3.0
_CALL_TIMEOUT_S: Final = 5.0
_CHUNK_BYTES: Final = 64 * 1024


class _TernError(Exception):
    pass


@dataclass(frozen=True)
class TernTarget:
    binary: str
    wsl_distro: str | None


def detect_tern() -> TernTarget | None:
    mode = os.environ.get("OFF_TERN") or "auto"
    if mode == "off":
        return None
    if mode != "auto":
        _warn(f"OFF_TERN must be auto or off, not {mode!r}; using auto")
    if not sys.stderr.isatty() or "OMP_BASH_SESSION" in os.environ:
        return None
    distro = os.environ.get("WSL_DISTRO_NAME") or None
    binary = "tern.exe" if distro else "tern"
    if shutil.which(binary) is None:
        return None
    target = TernTarget(binary=binary, wsl_distro=distro)
    try:
        _tern(target, ["ls", "--json"], _PROBE_TIMEOUT_S)
    except _TernError as error:
        _warn(f"tern probe failed, no viewers: {error}")
        return None
    return target


def viewer_argv(
    target: TernTarget, off_path: Path, cwd: Path, run_id: str, shard: int
) -> list[str]:
    # --viewer makes watch exit 0 on any shard result, so --end-on-success closes the session.
    watch_args = ["watch", run_id, "--shard", str(shard), "--viewer"]
    if target.wsl_distro is None:
        return [str(off_path), *watch_args]
    wsl = ["wsl.exe", "-d", target.wsl_distro, "--cd", str(cwd), "--"]
    return [*wsl, str(off_path), *watch_args]


def open_viewers(run_id: str, task: str, shards: int, cwd: Path, off_path: Path) -> None:
    target = detect_tern()
    if target is None:
        return
    try:
        for shard in range(1, shards + 1):
            argv = viewer_argv(target, off_path, cwd, run_id, shard)
            name = _session_name(task, run_id, shard, shards)
            _tern(target, ["new", "session", name, "--end-on-success", "--", *argv], _CALL_TIMEOUT_S)
    except _TernError as error:
        _warn(f"tern viewer failed: {error}")


def _session_name(task: str, run_id: str, shard: int, shards: int) -> str:
    name = f"off {task} {run_id[-4:]}"
    return f"{name} {shard}/{shards}" if shards > 1 else name


def watch(run_id: str, shard: int, *, poll_s: float = 0.25, out: TextIO = sys.stdout) -> int:
    log = run_log(run_id, shard)
    marker = done_marker(run_id, shard)
    pid_file = run_pid(run_id)
    # A shard that fails before opening its log still gets a marker.
    while not log.exists() and not marker.exists():
        if _run_gone(pid_file):
            return _lost(run_id, out)
        time.sleep(poll_s)
    if log.exists() and not _follow_log(log, marker, pid_file, poll_s, out):
        return _lost(run_id, out)
    try:
        code = _read_exit_code(marker, poll_s)
    except ValueError as error:
        out.write(f"off: error: {error}\n")
        out.flush()
        return 125
    out.write(f"off: shard {shard} exited {code}\n")
    out.flush()
    return code


def _follow_log(log: Path, marker: Path, pid_file: Path, poll_s: float, out: TextIO) -> bool:
    """Stream the log until the shard's done marker appears; False if the run's process died without one."""
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    finished_normally = True
    with log.open("rb") as handle:
        while True:
            # Sample the marker first: if it exists and a read then hits EOF, the log is drained.
            finished = marker.exists()
            chunk = handle.read(_CHUNK_BYTES)
            if chunk:
                out.write(decoder.decode(chunk))
                out.flush()
            elif finished:
                break
            elif _run_gone(pid_file) and not marker.exists():
                finished_normally = False
                break
            else:
                time.sleep(poll_s)
    out.write(decoder.decode(b"", final=True))
    out.flush()
    return finished_normally


def _run_gone(pid_file: Path) -> bool:
    try:
        pid = int(pid_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return False
    return not pid_alive(pid)


def _lost(run_id: str, out: TextIO) -> int:
    out.write(f"off: run {run_id} ended without a result (its off process is gone)\n")
    out.flush()
    return 125


def _read_exit_code(marker: Path, poll_s: float) -> int:
    # The writer may create the marker before it writes the code.
    while True:
        text = marker.read_text(encoding="utf-8").strip()
        if text:
            break
        time.sleep(poll_s)
    try:
        return int(text)
    except ValueError as error:
        raise ValueError(f"done marker {marker} does not hold an exit code: {text!r}") from error


def _tern(target: TernTarget, args: list[str], timeout_s: float) -> str:
    command = [target.binary, *args]
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _TernError(f"{' '.join(command)}: {error}") from error
    if result.returncode != 0:
        detail = " ".join(result.stderr.split()) or f"exit {result.returncode}"
        raise _TernError(f"{' '.join(command)}: {detail}")
    return result.stdout


def _warn(message: str) -> None:
    print(f"off: warning: {message}", file=sys.stderr)
