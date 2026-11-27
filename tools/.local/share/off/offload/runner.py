from __future__ import annotations

import contextlib
import fnmatch
import os
import re
import secrets
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Final, TextIO

from .config import OffloadConfig, TaskSpec
from .identity import base_key, host_slug, repo_slug, worker_name, worker_prefix
from .policy import LOCKED_PRIVILEGES, memory_policy, policy_hash, run_network_rules, setup_network_rules
from .sprites import SpriteError, Sprites, SpriteInfo, summarize_output
from .state import (
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
    run_log,
    state_root,
    write_cache,
)
from .tern import open_viewers

WORKDIR: Final = "/home/sprite/work"
ENV_FILE: Final = "/tmp/off.env"
OFF_DIR: Final = "/home/sprite/.off"
BASE_LIST: Final = f"{OFF_DIR}/base-files"
RUN_LIST: Final = "/tmp/off.files"
EXIT_TIMEOUT: Final = 124
EXIT_OFF_ERROR: Final = 125
EXIT_INTERRUPTED: Final = 130
KILL_GRACE_S: Final = 120
SETUP_TIMEOUT_S: Final = 3600
RSYNC_TIMEOUT_S: Final = 1800
SYNC_ATTEMPTS: Final = 3
SYNC_RETRY_DELAY_S: Final = 2
RSYNC_TRANSPORT_CODES: Final = frozenset({10, 12, 30, 35, 255})
TASK_ATTEMPTS: Final = 2
# Worker .bashrc runs readline setup that warns without a tty; the exported stub silences it for login shells.
NO_BIND: Final = "bind() { :; }; export -f bind; "
IDLE_RETENTION_S: Final = 7 * 24 * 3600
EXIT_SENTINEL: Final = "__off_exit__"
_SENTINEL_LINE: Final = re.compile(rf"{EXIT_SENTINEL} ([0-9a-f]+) (\d+)\n?")
_OUTPUT_LOCK: Final = threading.Lock()


class OffError(Exception):
    pass


class _Live:
    def __init__(self) -> None:
        self.interrupted = threading.Event()
        self._procs: set[subprocess.Popen[str]] = set()
        self._lock = threading.Lock()

    @contextlib.contextmanager
    def track(self, proc: subprocess.Popen[str]) -> Iterator[None]:
        with self._lock:
            self._procs.add(proc)
            if self.interrupted.is_set():
                proc.kill()
        try:
            yield
        finally:
            with self._lock:
                self._procs.discard(proc)

    def stop(self) -> None:
        with self._lock:
            self.interrupted.set()
            for proc in self._procs:
                proc.kill()


@dataclass(frozen=True)
class _Run:
    sprites: Sprites
    config: OffloadConfig
    task: TaskSpec
    run_id: str
    repo: str
    command: str
    env: Mapping[str, str]
    live: _Live


@dataclass(frozen=True)
class _Exec:
    client_code: int
    task_code: int | None
    expired: bool


def sync_files(config: OffloadConfig) -> list[str]:
    tracked = _git_paths(config.root, ["ls-files", "-z", "--recurse-submodules"])
    untracked = _git_paths(config.root, ["ls-files", "-z", "-o", "--exclude-standard"])
    return [
        path
        for path in dict.fromkeys([*tracked, *untracked])
        if _is_file_entry(config.root / path) and not _excluded(path, config.sync_exclude)
    ]


def sync_argv(config: OffloadConfig, shell: str) -> list[str]:
    return [
        "rsync",
        "-a",
        "--from0",
        "--files-from=-",
        "--ignore-missing-args",
        "-e",
        shell,
        f"{config.root}/",
        f"env:{WORKDIR}/",
    ]


def _git_paths(root: Path, args: list[str]) -> list[str]:
    listed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if listed.returncode != 0:
        raise OffError(f"git {' '.join(args)} failed: {listed.stderr.decode(errors='replace').strip()}")
    return [path for path in os.fsdecode(listed.stdout).split("\0") if path]


def _is_file_entry(path: Path) -> bool:
    """Untracked nested repos and uninitialized submodules show up as directories; their contents aren't ours to sync."""
    try:
        return not stat.S_ISDIR(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def base_marker(config: OffloadConfig) -> str:
    return f"off:base:{base_key(config)}:{policy_hash(config.worker)}"


def run_task(config: OffloadConfig, task: TaskSpec, extra_args: list[str], *, launcher: Path | None = None) -> int:
    previous = signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        if task.where == "local":
            return _run_local(config, task, extra_args)
        return _run_sprite(config, task, extra_args, launcher)
    except (OffError, SpriteError, OSError) as error:
        _say(sys.stderr, f"off: error: {error}\n")
        return EXIT_OFF_ERROR
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    finally:
        signal.signal(signal.SIGTERM, previous)


def _raise_interrupt(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def repo_workers(sprites: Sprites, host: str, repo: str) -> list[SpriteInfo]:
    prefix = worker_prefix(host, repo)
    return [info for info in sprites.list_sprites(prefix) if info.name.removeprefix(prefix).isdigit()]


def host_workers(sprites: Sprites, host: str) -> list[SpriteInfo]:
    prefix = worker_prefix(host, None)
    return [info for info in sprites.list_sprites(prefix) if _is_worker_suffix(info.name.removeprefix(prefix))]


def destroy_workers(sprites: Sprites, names: list[str]) -> list[str]:
    held: list[tuple[str, Lease]] = []
    busy: list[str] = []
    for name in names:
        lease = Lease(lock_path(name))
        if lease.try_acquire():
            held.append((name, lease))
        else:
            busy.append(name)
    try:
        if busy:
            raise OffError(f"workers busy with a run: {', '.join(busy)}")
        for name, _ in held:
            sprites.destroy(name)
            delete_cache(name)
        return [name for name, _ in held]
    finally:
        for _, lease in held:
            lease.release()


def ensure_ready(
    sprites: Sprites, config: OffloadConfig, name: str, live: _Live, setup_emit: Callable[[str], None]
) -> str:
    marker = base_marker(config)
    info = _find(sprites, name)
    if info is not None:
        checkpoint = next((cp for cp in sprites.checkpoints(name) if cp.comment == marker), None)
        if checkpoint is not None:
            return _ready(sprites, config, name, info, checkpoint.id, clean=_clean_at(name, checkpoint.id))
        sprites.destroy(name)
        delete_cache(name)
    try:
        checkpoint_id = _bootstrap(sprites, config, name, marker, live, setup_emit)
    except (OffError, SpriteError, OSError):
        _discard_worker(sprites, name)
        raise
    info = _find(sprites, name)
    if info is None:
        raise OffError(f"worker {name} is missing after setup")
    return _ready(sprites, config, name, info, checkpoint_id, clean=True)


def _ready(
    sprites: Sprites,
    config: OffloadConfig,
    name: str,
    info: SpriteInfo,
    checkpoint_id: str,
    *,
    clean: bool,
) -> str:
    sprites.ensure_private_url(name, info)
    _touch(config, name, checkpoint_id, clean=clean)
    return checkpoint_id


def _bootstrap(
    sprites: Sprites, config: OffloadConfig, name: str, marker: str, live: _Live, setup_emit: Callable[[str], None]
) -> str:
    sprites.create(name)
    sprites.set_network(name, setup_network_rules(config.worker))
    sprites.set_memory(name, memory_policy(config.worker.memory_mb))
    _exec_checked(
        sprites, name, ["mkdir", "-p", WORKDIR], live, cwd="/home/sprite", failure="could not create work dir"
    )
    # Only the setup inputs go in before setup: setup has open egress and its tree is checkpointed for good.
    _sync_up(sprites, config, name, list(config.setup.inputs), setup_emit)
    for line in config.setup.run:
        bounded = f"timeout --kill-after=15s {SETUP_TIMEOUT_S}s bash -lc {shlex.quote(line)}"
        _exec_checked(
            sprites,
            name,
            ["bash", "-c", NO_BIND + bounded],
            live,
            cwd=WORKDIR,
            failure=f"setup failed: {line}",
            emit=setup_emit,
        )
    # Checkpoints capture policies, and restoring one taken before set_privileges hangs, so lock first.
    sprites.set_privileges(name, LOCKED_PRIVILEGES)
    sprites.set_network(name, run_network_rules(config.worker))
    sprites.set_memory(name, memory_policy(config.worker.memory_mb))
    _exec_checked(sprites, name, ["true"], live, cwd=WORKDIR, failure="worker did not come back after lockdown")
    files = sync_files(config)
    _sync_up(sprites, config, name, files, setup_emit)
    listing = _write_file_list(files)
    try:
        _exec_checked(
            sprites,
            name,
            ["bash", "-c", f"mkdir -p {OFF_DIR} && mv {RUN_LIST} {BASE_LIST}"],
            live,
            cwd=WORKDIR,
            failure="could not record the base file list",
            uploads=[(listing, RUN_LIST)],
        )
    finally:
        listing.unlink(missing_ok=True)
    return sprites.checkpoint(name, marker).id


def _discard_worker(sprites: Sprites, name: str) -> None:
    try:
        sprites.destroy(name)
    except (SpriteError, OSError) as error:
        _warn(f"could not destroy half-built worker {name}: {error}")
    delete_cache(name)


def _find(sprites: Sprites, name: str) -> SpriteInfo | None:
    return next((info for info in sprites.list_sprites(name) if info.name == name), None)


def _touch(config: OffloadConfig, name: str, checkpoint_id: str, *, clean: bool) -> None:
    write_cache(
        name,
        WorkerCache(
            base_key=base_key(config),
            base_checkpoint=checkpoint_id,
            policy_hash=policy_hash(config.worker),
            last_used=time.time(),
            clean=clean,
        ),
    )


def _cache_if_readable(name: str) -> WorkerCache | None:
    try:
        return read_cache(name)
    except (ValueError, TypeError) as error:
        _warn(f"unreadable cache for {name}: {error}")
        return None


def _clean_at(name: str, checkpoint_id: str) -> bool:
    cache = _cache_if_readable(name)
    return cache is not None and cache.clean and cache.base_checkpoint == checkpoint_id


def _is_ready(config: OffloadConfig, name: str) -> bool:
    cache = _cache_if_readable(name)
    return (
        cache is not None
        and cache.base_key == base_key(config)
        and cache.policy_hash == policy_hash(config.worker)
    )


def reset_worker(sprites: Sprites, name: str, checkpoint_id: str) -> None:
    with Lease(lock_path(name)):
        cache = _cache_if_readable(name)
        if cache is None or cache.clean or cache.base_checkpoint != checkpoint_id:
            return
        sprites.restore(name, checkpoint_id)
        write_cache(name, replace(cache, clean=True))


def _spawn_reset(launcher: Path, name: str, checkpoint_id: str) -> None:
    with (state_root() / "reset.log").open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(launcher), "_reset", name, checkpoint_id],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def _reset_workers(sprites: Sprites, workers: list[str], launcher: Path | None) -> None:
    for name in workers:
        cache = _cache_if_readable(name)
        if cache is None or cache.clean or not cache.base_checkpoint:
            continue
        try:
            if launcher is None:
                reset_worker(sprites, name, cache.base_checkpoint)
            else:
                _spawn_reset(launcher, name, cache.base_checkpoint)
        except (SpriteError, OSError) as error:
            _warn(f"could not reset worker {name}: {error}")


def _run_local(config: OffloadConfig, task: TaskSpec, extra_args: list[str]) -> int:
    env = {**os.environ, **task.env, "OFF": "1"}
    proc = subprocess.Popen(
        ["bash", "-lc", _command(task, extra_args)],
        cwd=config.root,
        env=env,
        start_new_session=True,
    )
    try:
        return proc.wait(timeout=task.timeout_s)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        _say(sys.stderr, f"off: task {task.name} timed out after {task.timeout_s}s\n")
        return EXIT_TIMEOUT
    except KeyboardInterrupt:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        return EXIT_INTERRUPTED


def _run_sprite(config: OffloadConfig, task: TaskSpec, extra_args: list[str], launcher: Path | None) -> int:
    env = _base_env(config, task)
    sprites = Sprites()
    host = host_slug()
    repo = repo_slug(config.root)
    names = [worker_name(host, repo, index) for index in range(1, config.worker.max + 1)]
    run_id = new_run_id(task.name)
    started_at = datetime.now(UTC)
    started = time.monotonic()
    _say(sys.stderr, f"off: run {run_id} ({task.name}, {task.shards} shard(s)) log: {run_log(run_id, 1)}\n")
    ready = [name for name in names[task.shards :] if _is_ready(config, name)]
    leases = lease_workers([*names[: task.shards], *ready], task.shards)
    workers = [name for name, _ in leases]
    if launcher is not None:
        open_viewers(run_id, task.shards, config.root, launcher)
    ctx = _Run(sprites, config, task, run_id, repo, _command(task, extra_args), env, _Live())
    try:
        exit_code = _combine(_run_shards(ctx, workers))
    except KeyboardInterrupt:
        exit_code = EXIT_INTERRUPTED
    finally:
        for _, lease in leases:
            lease.release()
        _reset_workers(sprites, workers, launcher)
    if task.artifacts:
        _say(sys.stderr, f"off: artifacts: {artifact_root(repo, run_id)}/\n")
    try:
        append_record(
            {
                "run_id": run_id,
                "ts": started_at.isoformat(timespec="seconds"),
                "host": host,
                "repo": repo,
                "task": task.name,
                "shards": task.shards,
                "workers": workers,
                "exit": exit_code,
                "duration_s": round(time.monotonic() - started, 1),
                "where": "sprite",
            }
        )
    except OSError as error:
        _warn(f"run record not saved: {error}")
    _collect_idle(sprites, host, repo)
    return exit_code


def _command(task: TaskSpec, extra_args: list[str]) -> str:
    return task.run if not extra_args else f"{task.run} {shlex.join(extra_args)}"


def _base_env(config: OffloadConfig, task: TaskSpec) -> dict[str, str]:
    missing = [name for name in config.env_pass if name not in os.environ]
    if missing:
        raise OffError(f"missing env: {', '.join(missing)}")
    return {**{name: os.environ[name] for name in config.env_pass}, **task.env}


def _run_shards(ctx: _Run, workers: list[str]) -> list[int]:
    pool = ThreadPoolExecutor(max_workers=len(workers))
    try:
        futures = [pool.submit(_run_shard, ctx, index, name) for index, name in enumerate(workers, start=1)]
        return [future.result() for future in futures]
    except KeyboardInterrupt:
        ctx.live.stop()
        raise
    finally:
        while True:
            try:
                pool.shutdown(wait=True)
                break
            except KeyboardInterrupt:
                ctx.live.stop()


def _run_shard(ctx: _Run, index: int, name: str) -> int:
    count = ctx.task.shards
    prefix = "" if count == 1 else f"[{index}/{count}] "
    code = EXIT_OFF_ERROR
    with run_log(ctx.run_id, index).open("w", encoding="utf-8") as log:

        def emit(line: str) -> None:
            log.write(line)
            log.flush()
            _say(sys.stdout, f"{prefix}{line}")

        try:
            code = _execute(ctx, index, name, emit)
        except (OffError, SpriteError, OSError) as error:
            where = "" if count == 1 else f"shard {index}/{count}: "
            message = f"off: error: {where}{error}\n"
            log.write(message)
            _say(sys.stderr, message)
        finally:
            done_marker(ctx.run_id, index).write_text(f"{code}\n", encoding="utf-8")
    return code


def _execute(ctx: _Run, index: int, name: str, emit: Callable[[str], None]) -> int:
    base_id = ensure_ready(ctx.sprites, ctx.config, name, ctx.live, lambda line: emit(f"[setup] {line}"))
    limit = ctx.task.timeout_s
    attempt = 1
    while True:
        result = _attempt(ctx, index, name, base_id, emit)
        if result.task_code is not None:
            _pull_artifacts(ctx, name, index)
            _touch(ctx.config, name, base_id, clean=False)
            return result.task_code
        _stop_remote(ctx.sprites, ctx.config, name, base_id)
        if ctx.live.interrupted.is_set():
            emit("off: interrupted; the remote task was stopped\n")
            return EXIT_INTERRUPTED
        if result.expired:
            emit(f"off: local watchdog stopped the task after {limit + KILL_GRACE_S}s\n")
            return EXIT_TIMEOUT
        if attempt == TASK_ATTEMPTS:
            raise OffError(f"lost the task on {name}: sprite exec exited {result.client_code} without a result")
        attempt += 1
        emit(f"off: lost the connection to {name}; retrying once\n")


def _attempt(ctx: _Run, index: int, name: str, base_id: str, emit: Callable[[str], None]) -> _Exec:
    if not _clean_at(name, base_id):
        ctx.sprites.restore(name, base_id)
    _touch(ctx.config, name, base_id, clean=False)
    files = sync_files(ctx.config)
    _sync_up(ctx.sprites, ctx.config, name, files, emit)
    envfile = _write_env_file(
        {**ctx.env, "CI": "1", "OFF": "1", "OFF_SHARD": str(index), "OFF_SHARDS": str(ctx.task.shards)}
    )
    listing = _write_file_list(files)
    limit = ctx.task.timeout_s
    nonce = secrets.token_hex(8)
    sentinel = f"{EXIT_SENTINEL} {nonce}"
    script = (
        f"if ! . {ENV_FILE}; then printf '\\n{sentinel} {EXIT_OFF_ERROR}\\n'; exit {EXIT_OFF_ERROR}; fi; "
        f"rm -f {ENV_FILE}; "
        f"if [ -f {BASE_LIST} ]; then "
        f"LC_ALL=C comm -z -23 <(LC_ALL=C sort -zu {BASE_LIST}) <(LC_ALL=C sort -zu {RUN_LIST}) "
        f"| xargs -0 -r rm -f --; fi; "
        f"rm -f {RUN_LIST}; "
        f"start=$SECONDS; "
        f"timeout --kill-after=15s {limit}s bash -lc {shlex.quote(ctx.command)}; code=$?; "
        f'if [ "$code" -eq 137 ] && [ $((SECONDS - start)) -ge {limit} ]; then code={EXIT_TIMEOUT}; fi; '
        f"printf '\\n{sentinel} %d\\n' \"$code\"; exit \"$code\""
    )
    try:
        proc = ctx.sprites.start_exec(
            name,
            ["bash", "-c", NO_BIND + script],
            cwd=WORKDIR,
            uploads=[(envfile, ENV_FILE), (listing, RUN_LIST)],
        )
        with ctx.live.track(proc):
            result = _pump(proc, emit, limit + KILL_GRACE_S, nonce)
    finally:
        envfile.unlink(missing_ok=True)
        listing.unlink(missing_ok=True)
    return result


def _stop_remote(sprites: Sprites, config: OffloadConfig, name: str, base_id: str) -> None:
    try:
        sprites.restore(name, base_id)
    except (SpriteError, OSError) as error:
        _warn(f"could not stop the remote task on {name}: {error}")
    else:
        _touch(config, name, base_id, clean=True)


def _pump(proc: subprocess.Popen[str], emit: Callable[[str], None], limit_s: float, nonce: str) -> _Exec:
    """Stream output until EOF; the exit code comes from the wrapper's nonce-tagged sentinel line.

    Output after the sentinel (background processes, logout scripts) is still shown.
    """
    if proc.stdout is None:
        raise OffError("sprite exec has no output stream")
    expired = threading.Event()

    def expire() -> None:
        expired.set()
        proc.kill()

    timer = threading.Timer(limit_s, expire)
    timer.start()
    task_code: int | None = None
    held: list[str] = []
    try:
        with proc.stdout:
            for line in proc.stdout:
                code = _sentinel_code(line, nonce) if task_code is None else None
                if code is not None:
                    held.clear()
                    task_code = code
                    continue
                _flush(held, emit)
                if line == "\n" and task_code is None:
                    held.append(line)
                else:
                    emit(line)
    finally:
        timer.cancel()
        _flush(held, emit)
    client_code = proc.wait()
    accepted = task_code if task_code == client_code and not expired.is_set() else None
    return _Exec(client_code=client_code, task_code=accepted, expired=expired.is_set())


def _sentinel_code(line: str, nonce: str) -> int | None:
    match = _SENTINEL_LINE.fullmatch(line)
    if match is None or match.group(1) != nonce:
        return None
    return int(match.group(2))


def _flush(held: list[str], emit: Callable[[str], None]) -> None:
    for line in held:
        emit(line)
    held.clear()


def _write_env_file(env: Mapping[str, str]) -> Path:
    descriptor, name = tempfile.mkstemp(prefix="off-env-", suffix=".env")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for key, value in env.items():
            handle.write(f"export {key}={shlex.quote(value)}\n")
    return Path(name)


def _write_file_list(files: list[str]) -> Path:
    descriptor, name = tempfile.mkstemp(prefix="off-files-", suffix=".list")
    with os.fdopen(descriptor, "w", encoding="utf-8", errors="surrogateescape") as handle:
        handle.write("\0".join(files))
    return Path(name)


def _pull_artifacts(ctx: _Run, name: str, index: int) -> None:
    if not ctx.task.artifacts:
        return
    destination = artifacts_dir(ctx.repo, ctx.run_id, index)
    shell = ctx.sprites.rsync_shell(name)
    for path in ctx.task.artifacts:
        try:
            completed = _rsync(["rsync", "-a", "-e", shell, f"env:{WORKDIR}/{path}", f"{destination}/"])
        except OffError as error:
            _warn(f"artifact {path} not pulled: {error}")
            continue
        if completed.returncode != 0:
            _warn(f"artifact {path} not pulled: {summarize_output(completed.stderr)}")


def _sync_up(
    sprites: Sprites, config: OffloadConfig, name: str, files: list[str], emit: Callable[[str], None]
) -> None:
    for attempt in range(1, SYNC_ATTEMPTS + 1):
        completed = _rsync(sync_argv(config, sprites.rsync_shell(name)), stdin="\0".join(files))
        if completed.returncode == 0:
            return
        if completed.returncode not in RSYNC_TRANSPORT_CODES or attempt == SYNC_ATTEMPTS:
            raise OffError(f"sync to {name} failed: {summarize_output(completed.stderr)}")
        emit(f"off: sync to {name} interrupted (rsync exit {completed.returncode}); retrying\n")
        time.sleep(SYNC_RETRY_DELAY_S)


def _rsync(argv: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            errors="surrogateescape",
            timeout=RSYNC_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError as error:
        raise OffError("rsync not found; install rsync") from error
    except subprocess.TimeoutExpired as error:
        raise OffError(f"rsync timed out after {RSYNC_TIMEOUT_S}s") from error


def _exec_checked(
    sprites: Sprites,
    name: str,
    argv: list[str],
    live: _Live,
    *,
    cwd: str,
    failure: str,
    emit: Callable[[str], None] | None = None,
    uploads: Sequence[tuple[Path, str]] = (),
) -> None:
    proc = sprites.start_exec(name, argv, cwd=cwd, uploads=uploads)
    output = emit or _discard
    if proc.stdout is None:
        raise OffError("sprite exec has no output stream")
    timer = threading.Timer(SETUP_TIMEOUT_S + KILL_GRACE_S, proc.kill)
    timer.start()
    try:
        with proc.stdout, live.track(proc):
            for line in proc.stdout:
                output(line)
    finally:
        timer.cancel()
    code = proc.wait()
    if code != 0:
        raise OffError(f"{failure} (exit {code})")


def _discard(_line: str) -> None:
    return None


def _combine(codes: list[int]) -> int:
    return next((code for code in codes if code != 0), 0)


def _collect_idle(sprites: Sprites, host: str, repo: str) -> None:
    prefix = worker_prefix(host, repo)
    try:
        infos = repo_workers(sprites, host, repo)
    except SpriteError as error:
        _warn(f"cleanup skipped: {error}")
        return
    now = time.time()
    for info in infos:
        if int(info.name.removeprefix(prefix)) <= 1:
            continue
        lease = Lease(lock_path(info.name))
        if not lease.try_acquire():
            continue
        try:
            if _idle(info.name, now):
                sprites.destroy(info.name)
                delete_cache(info.name)
        except (SpriteError, OSError) as error:
            _warn(f"could not collect {info.name}: {error}")
        finally:
            lease.release()


def _idle(name: str, now: float) -> bool:
    """Only workers this machine has a record of: another machine with the same hostname may be using the rest."""
    try:
        cache = read_cache(name)
    except (ValueError, TypeError) as error:
        _warn(f"unreadable cache for {name}; leaving the worker alone: {error}")
        return False
    return cache is not None and now - cache.last_used >= IDLE_RETENTION_S


def _excluded(path: str, patterns: tuple[str, ...]) -> bool:
    names = [*path.split("/"), path]
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns for name in names)


def _is_worker_suffix(rest: str) -> bool:
    repo, separator, index = rest.rpartition("-")
    return bool(separator and repo and "-" not in repo and index.isdigit())


def _say(stream: TextIO, text: str) -> None:
    with _OUTPUT_LOCK:
        stream.write(text)
        stream.flush()


def _warn(message: str) -> None:
    _say(sys.stderr, f"off: warning: {message}\n")
