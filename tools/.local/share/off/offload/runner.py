from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TextIO

from .config import OffloadConfig, TaskSpec
from .identity import base_key, host_slug, repo_slug, worker_name, worker_prefix
from .policy import LOCKED_PRIVILEGES, memory_policy, policy_hash, run_network_rules, setup_network_rules
from .sprites import SpriteError, Sprites, SpriteInfo, summarize_output
from .tern import open_viewers
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
    write_cache,
)

WORKDIR: Final = "/home/sprite/work"
ENV_FILE: Final = "/tmp/off.env"
EXIT_TIMEOUT: Final = 124
EXIT_OFF_ERROR: Final = 125
KILL_GRACE_S: Final = 120
SETUP_TIMEOUT_S: Final = 3600
RSYNC_TIMEOUT_S: Final = 1800
IDLE_RETENTION_S: Final = 7 * 24 * 3600
_OUTPUT_LOCK: Final = threading.Lock()


class OffError(Exception):
    pass


@dataclass(frozen=True)
class _Run:
    sprites: Sprites
    config: OffloadConfig
    task: TaskSpec
    run_id: str
    repo: str
    command: str
    env: Mapping[str, str]


def sync_argv(config: OffloadConfig, shell: str) -> list[str]:
    return [
        "rsync",
        "-a",
        "--delete",
        "--filter=:- .gitignore",
        "--exclude=/.git",
        *(f"--exclude={pattern}" for pattern in config.sync_exclude),
        "-e",
        shell,
        f"{config.root}/",
        f"env:{WORKDIR}/",
    ]


def run_task(config: OffloadConfig, task: TaskSpec, extra_args: list[str], *, viewer: Path | None = None) -> int:
    try:
        if task.where == "local":
            return _run_local(config, task, extra_args)
        return _run_sprite(config, task, extra_args, viewer)
    except (OffError, SpriteError, OSError) as error:
        _say(sys.stderr, f"off: error: {error}\n")
        return EXIT_OFF_ERROR


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


def base_marker(config: OffloadConfig) -> str:
    return f"off:base:{base_key(config)}:{policy_hash(config.worker)}"


def ensure_ready(
    sprites: Sprites, config: OffloadConfig, name: str, setup_emit: Callable[[str], None] | None = None
) -> str:
    marker = base_marker(config)
    info = _find(sprites, name)
    if info is not None:
        checkpoint = next((cp for cp in sprites.checkpoints(name) if cp.comment == marker), None)
        if checkpoint is not None:
            sprites.ensure_private_url(name, info)
            _touch(config, name, checkpoint.id)
            return checkpoint.id
        sprites.destroy(name)
    return _bootstrap(sprites, config, name, marker, setup_emit or _setup_output)


def _bootstrap(
    sprites: Sprites, config: OffloadConfig, name: str, marker: str, setup_emit: Callable[[str], None]
) -> str:
    sprites.create(name)
    sprites.set_network(name, setup_network_rules(config.worker))
    sprites.set_memory(name, memory_policy(config.worker.memory_mb))
    _exec_checked(
        sprites,
        name,
        ["mkdir", "-p", WORKDIR],
        cwd="/home/sprite",
        failure="could not create work dir",
        emit=_discard,
    )
    _sync_up(sprites, config, name)
    for line in config.setup.run:
        _exec_checked(
            sprites,
            name,
            ["bash", "-lc", line],
            cwd=WORKDIR,
            failure=f"setup failed: {line}",
            emit=setup_emit,
        )
    # Checkpoints capture policies, and restoring one taken before set_privileges hangs, so lock first.
    sprites.set_privileges(name, LOCKED_PRIVILEGES)
    sprites.set_network(name, run_network_rules(config.worker))
    sprites.set_memory(name, memory_policy(config.worker.memory_mb))
    _exec_checked(
        sprites,
        name,
        ["true"],
        cwd=WORKDIR,
        failure="worker did not come back after lockdown",
        emit=_discard,
    )
    checkpoint = sprites.checkpoint(name, marker)
    info = _find(sprites, name)
    if info is None:
        raise OffError(f"worker {name} is missing after setup")
    sprites.ensure_private_url(name, info)
    _touch(config, name, checkpoint.id)
    return checkpoint.id


def _find(sprites: Sprites, name: str) -> SpriteInfo | None:
    return next((info for info in sprites.list_sprites(name) if info.name == name), None)


def _touch(config: OffloadConfig, name: str, checkpoint_id: str) -> None:
    write_cache(
        name,
        WorkerCache(
            base_key=base_key(config),
            base_checkpoint=checkpoint_id,
            policy_hash=policy_hash(config.worker),
            last_used=time.time(),
        ),
    )


def _run_local(config: OffloadConfig, task: TaskSpec, extra_args: list[str]) -> int:
    env = {**os.environ, **task.env, "OFF": "1"}
    try:
        completed = subprocess.run(
            ["bash", "-lc", _command(task, extra_args)],
            cwd=config.root,
            env=env,
            timeout=task.timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _say(sys.stderr, f"off: task {task.name} timed out after {task.timeout_s}s\n")
        return EXIT_TIMEOUT
    return completed.returncode


def _run_sprite(config: OffloadConfig, task: TaskSpec, extra_args: list[str], viewer: Path | None) -> int:
    env = _base_env(config, task)
    sprites = Sprites()
    host = host_slug()
    repo = repo_slug(config.root)
    names = [worker_name(host, repo, index) for index in range(1, config.worker.max + 1)]
    run_id = new_run_id(task.name)
    started_at = datetime.now(UTC)
    started = time.monotonic()
    _say(sys.stderr, f"off: run {run_id} ({task.name}, {task.shards} shard(s)) log: {run_log(run_id, 1)}\n")
    if viewer is not None:
        open_viewers(run_id, task.shards, config.root, viewer)
    leases = lease_workers(names, task.shards)
    workers = [name for name, _ in leases]
    try:
        ctx = _Run(sprites, config, task, run_id, repo, _command(task, extra_args), env)
        codes = _run_shards(ctx, workers)
    finally:
        for _, lease in leases:
            lease.release()
    if task.artifacts:
        _say(sys.stderr, f"off: artifacts: {artifact_root(repo, run_id)}/\n")
    exit_code = _combine(codes)
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
    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        futures = [pool.submit(_run_shard, ctx, index, name) for index, name in enumerate(workers, start=1)]
        return [future.result() for future in futures]


def _run_shard(ctx: _Run, index: int, name: str) -> int:
    count = ctx.task.shards
    prefix = "" if count == 1 else f"[{index}/{count}] "
    with run_log(ctx.run_id, index).open("w", encoding="utf-8") as log:

        def emit(line: str) -> None:
            log.write(line)
            _say(sys.stdout, f"{prefix}{line}")

        try:
            code = _execute(ctx, index, name, emit)
        except (OffError, SpriteError, OSError) as error:
            where = "" if count == 1 else f"shard {index}/{count}: "
            message = f"off: error: {where}{error}\n"
            log.write(message)
            _say(sys.stderr, message)
            code = EXIT_OFF_ERROR
        done_marker(ctx.run_id, index).write_text(f"{code}\n", encoding="utf-8")
    return code


def _execute(ctx: _Run, index: int, name: str, emit: Callable[[str], None]) -> int:
    base_id = ensure_ready(ctx.sprites, ctx.config, name, lambda line: emit(f"[setup] {line}"))
    ctx.sprites.restore(name, base_id)
    _sync_up(ctx.sprites, ctx.config, name)
    envfile = _write_env_file(
        {**ctx.env, "CI": "1", "OFF": "1", "OFF_SHARD": str(index), "OFF_SHARDS": str(ctx.task.shards)}
    )
    try:
        script = (
            f". {ENV_FILE} && rm -f {ENV_FILE} && "
            f"exec timeout --kill-after=15s {ctx.task.timeout_s}s bash -lc {shlex.quote(ctx.command)}"
        )
        proc = ctx.sprites.start_exec(name, ["bash", "-lc", script], cwd=WORKDIR, upload=(envfile, ENV_FILE))
        code = _pump(proc, emit, ctx.task.timeout_s + KILL_GRACE_S)
    finally:
        envfile.unlink(missing_ok=True)
    _pull_artifacts(ctx, name, index)
    _touch(ctx.config, name, base_id)
    return code


def _pump(proc: subprocess.Popen[str], emit: Callable[[str], None], limit_s: float) -> int:
    if proc.stdout is None:
        raise OffError("sprite exec has no output stream")
    expired = threading.Event()

    def expire() -> None:
        expired.set()
        proc.kill()

    timer = threading.Timer(limit_s, expire)
    timer.start()
    try:
        with proc.stdout:
            for line in proc.stdout:
                emit(line)
    finally:
        timer.cancel()
    code = proc.wait()
    return EXIT_TIMEOUT if expired.is_set() else code


def _write_env_file(env: Mapping[str, str]) -> Path:
    descriptor, name = tempfile.mkstemp(prefix="off-env-", suffix=".env")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for key, value in env.items():
            handle.write(f"export {key}={shlex.quote(value)}\n")
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


def _sync_up(sprites: Sprites, config: OffloadConfig, name: str) -> None:
    completed = _rsync(sync_argv(config, sprites.rsync_shell(name)))
    if completed.returncode != 0:
        raise OffError(f"sync to {name} failed: {summarize_output(completed.stderr)}")


def _rsync(argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=RSYNC_TIMEOUT_S, check=False)
    except FileNotFoundError as error:
        raise OffError("rsync not found; install rsync") from error
    except subprocess.TimeoutExpired as error:
        raise OffError(f"rsync timed out after {RSYNC_TIMEOUT_S}s") from error


def _exec_checked(
    sprites: Sprites,
    name: str,
    argv: list[str],
    *,
    cwd: str,
    failure: str,
    emit: Callable[[str], None],
) -> None:
    proc = sprites.start_exec(name, argv, cwd=cwd, upload=None)
    code = _pump(proc, emit, SETUP_TIMEOUT_S)
    if code != 0:
        raise OffError(f"{failure} (exit {code})")


def _discard(_line: str) -> None:
    return None


def _setup_output(line: str) -> None:
    _say(sys.stderr, f"[setup] {line}")


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
        cache = read_cache(info.name)
        if cache is None or now - cache.last_used < IDLE_RETENTION_S:
            continue
        lease = Lease(lock_path(info.name))
        if not lease.try_acquire():
            continue
        try:
            sprites.destroy(info.name)
            delete_cache(info.name)
        except (SpriteError, OSError) as error:
            _warn(f"could not collect {info.name}: {error}")
        finally:
            lease.release()


def _is_worker_suffix(rest: str) -> bool:
    repo, separator, index = rest.rpartition("-")
    return bool(separator and repo and index.isdigit())


def _say(stream: TextIO, text: str) -> None:
    with _OUTPUT_LOCK:
        stream.write(text)
        stream.flush()


def _warn(message: str) -> None:
    _say(sys.stderr, f"off: warning: {message}\n")
