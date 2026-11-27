import codecs
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from .state import done_marker, run_log

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
    watch_args = ["watch", run_id, "--shard", str(shard)]
    if target.wsl_distro is None:
        return [str(off_path), *watch_args]
    wsl = ["wsl.exe", "-d", target.wsl_distro, "--cd", str(cwd), "--"]
    return [*wsl, str(off_path), *watch_args]


def open_viewers(run_id: str, shards: int, cwd: Path, off_path: Path) -> None:
    target = detect_tern()
    if target is None:
        return
    try:
        has_session = "off" in _session_names(_tern(target, ["ls", "--json"], _CALL_TIMEOUT_S))
        for shard in range(1, shards + 1):
            argv = viewer_argv(target, off_path, cwd, run_id, shard)
            if shard == 1 and not has_session:
                _tern(target, ["new", "session", "off", "--", *argv], _CALL_TIMEOUT_S)
            else:
                _tern(target, ["new", "tab", "off", "--", *argv], _CALL_TIMEOUT_S)
    except _TernError as error:
        _warn(f"tern viewer failed: {error}")


def watch(run_id: str, shard: int, *, poll_s: float = 0.25, out: TextIO = sys.stdout) -> int:
    log = run_log(run_id, shard)
    marker = done_marker(run_id, shard)
    # A shard that fails before opening its log still gets a marker.
    while not log.exists() and not marker.exists():
        time.sleep(poll_s)
    if log.exists():
        _follow_log(log, marker, poll_s, out)
    try:
        code = _read_exit_code(marker, poll_s)
    except ValueError as error:
        out.write(f"off: error: {error}\n")
        out.flush()
        return 125
    out.write(f"off: shard {shard} exited {code}\n")
    out.flush()
    return code


def _follow_log(log: Path, marker: Path, poll_s: float, out: TextIO) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
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
            else:
                time.sleep(poll_s)
    out.write(decoder.decode(b"", final=True))
    out.flush()


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


def _session_names(listing: str) -> set[str]:
    try:
        data: object = json.loads(listing)
    except json.JSONDecodeError as error:
        raise _TernError("ls --json printed invalid JSON") from error
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, list):
        raise _TernError("ls --json has no sessions list")
    names: set[str] = set()
    for session in sessions:
        name = session.get("name") if isinstance(session, dict) else None
        if not isinstance(name, str):
            raise _TernError("ls --json has a session without a name")
        names.add(name)
    return names


def _warn(message: str) -> None:
    print(f"off: warning: {message}", file=sys.stderr)
