import fcntl
import json
import os
import secrets
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Self, TextIO


def state_root() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "off"


class Lease:
    """Exclusive flock on a lock file, held from acquire until release or with-block exit."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: TextIO | None = None

    def try_acquire(self) -> bool:
        try:
            self._take(fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    def acquire(self) -> None:
        self._take(fcntl.LOCK_EX)

    def release(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()

    def _take(self, flags: int) -> None:
        if self._handle is not None:
            raise RuntimeError(f"lease {self._path.name} is already held by this object")
        handle = self._path.open("a")
        try:
            fcntl.flock(handle, flags)
        except BaseException:
            handle.close()
            raise
        self._handle = handle


def lease_workers(names: list[str], count: int) -> list[tuple[str, Lease]]:
    """Lease `count` distinct workers, taking any free ones without waiting.

    When not enough are free, release them and block on the first `count` names in order:
    every run waits in the same order, so two runs can't each hold what the other needs.
    """
    if len(set(names)) != len(names) or count > len(names):
        raise ValueError(f"cannot lease {count} of {len(names)} distinct workers")
    leases: list[tuple[str, Lease]] = []
    for name in names:
        if len(leases) == count:
            return leases
        lease = Lease(lock_path(name))
        if lease.try_acquire():
            leases.append((name, lease))
    if len(leases) == count:
        return leases
    for _, lease in leases:
        lease.release()
    ordered: list[tuple[str, Lease]] = []
    try:
        for name in names[:count]:
            lease = Lease(lock_path(name))
            lease.acquire()
            ordered.append((name, lease))
    except BaseException:
        for _, lease in ordered:
            lease.release()
        raise
    return ordered


@dataclass
class WorkerCache:
    base_key: str
    base_checkpoint: str
    policy_hash: str
    last_used: float
    clean: bool = False


def read_cache(name: str) -> WorkerCache | None:
    try:
        text = _cache_path(name).read_text()
    except FileNotFoundError:
        return None
    return WorkerCache(**json.loads(text))


def write_cache(name: str, cache: WorkerCache) -> None:
    path = _cache_path(name)
    temp = path.with_name(f"{path.name}.tmp")
    temp.write_text(json.dumps(asdict(cache), sort_keys=True))
    os.replace(temp, path)


def delete_cache(name: str) -> None:
    _cache_path(name).unlink(missing_ok=True)


def new_run_id(task: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{task}-{secrets.token_hex(2)}"


def run_log(run_id: str, shard: int) -> Path:
    return _private_dir("runs") / f"{run_id}.{shard}.log"


def done_marker(run_id: str, shard: int) -> Path:
    return _private_dir("runs") / f"{run_id}.{shard}.done"


def run_pid(run_id: str) -> Path:
    return _private_dir("runs") / f"{run_id}.pid"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def reset_log() -> Path:
    return _private_dir() / "reset.log"


def artifact_root(repo: str, run_id: str) -> Path:
    return _private_dir("artifacts", repo, run_id)


def artifacts_dir(repo: str, run_id: str, shard: int) -> Path:
    path = artifact_root(repo, run_id) / str(shard)
    path.mkdir(mode=0o700, exist_ok=True)
    return path


def append_record(record: Mapping[str, object]) -> None:
    with _records_path().open("a") as handle:
        handle.write(json.dumps(record) + "\n")


def read_records() -> list[dict[str, object]]:
    try:
        text = _records_path().read_text()
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in text.splitlines()]


def lock_path(name: str) -> Path:
    return _private_dir("locks") / f"{name}.lock"


def _cache_path(name: str) -> Path:
    return _private_dir("workers") / f"{name}.json"


def _records_path() -> Path:
    return _private_dir() / "runs.jsonl"


def _private_dir(*parts: str) -> Path:
    root = state_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path
