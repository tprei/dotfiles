from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from offload.config import ConfigError, OffloadConfig, TaskSpec, load_config
from offload.identity import base_key, host_slug, repo_slug, worker_prefix
from offload.policy import (
    LOCKED_PRIVILEGES,
    memory_policy,
    policy_hash,
    run_network_rules,
    setup_network_rules,
)
from offload.runner import (
    EXIT_OFF_ERROR,
    OffError,
    destroy_workers,
    host_workers,
    repo_workers,
    run_task,
)
from offload.sprites import SpriteError, Sprites
from offload.state import read_cache, read_records
from offload.tern import watch

CPU_HOUR_USD = 0.0385
GB_HOUR_USD = 0.021875


def main(argv: Sequence[str]) -> int:
    head, extra = _split_extra(list(argv))
    parser = _parser()
    args = parser.parse_args(head)
    if extra is not None and args.command != "run":
        parser.error("'--' is only accepted by run")
    try:
        return _dispatch(args, extra or [])
    except (ConfigError, OffError, SpriteError, OSError) as error:
        print(f"off: error: {error}", file=sys.stderr)
        return EXIT_OFF_ERROR


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="off", description="Run a repo's declared tasks on Sprite workers.")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="show the resolved plan (local only)")
    plan.add_argument("task", nargs="?")
    run = commands.add_parser("run", help="run a task; arguments after -- go to the task")
    run.add_argument("task")
    commands.add_parser("status", help="list this host's workers")
    down = commands.add_parser("down", help="destroy this repo's workers")
    down.add_argument("--all", action="store_true", help="destroy every worker on this host")
    viewer = commands.add_parser("watch", help="follow a run's log until the shard finishes")
    viewer.add_argument("run_id")
    viewer.add_argument("--shard", type=int, default=1)
    usage = commands.add_parser("usage", help="Sprite usage and estimated cost of off workers")
    usage.add_argument("--days", type=int, default=7)
    return parser


def _split_extra(argv: list[str]) -> tuple[list[str], list[str] | None]:
    if "--" not in argv:
        return argv, None
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def _dispatch(args: argparse.Namespace, extra: list[str]) -> int:
    command: str = args.command
    if command == "plan":
        return _plan(args.task)
    if command == "run":
        return _run(args.task, extra)
    if command == "status":
        return _status()
    if command == "watch":
        return watch(args.run_id, args.shard)
    if command == "usage":
        return _usage(args.days)
    return _down(args.all)


def _run(name: str, extra: list[str]) -> int:
    config = load_config(_repo_root())
    return run_task(config, _task(config, name), extra, viewer=Path(sys.argv[0]).resolve())


def _usage(days: int) -> int:
    if days < 1:
        raise OffError("--days must be at least 1")
    start = datetime.now(UTC) - timedelta(days=days)
    query = f"/v1/usage?start={start.strftime('%Y-%m-%dT%H:%M:%SZ')}&group_by=sprite"
    payload = json.loads(Sprites().org_api(query))
    prefix = f"/{worker_prefix(host_slug(), None)}"
    totals: dict[str, tuple[float, float]] = {}
    for bucket in payload["usage"]:
        ref = str(bucket.get("sprite_ref", ""))
        if prefix not in f"/{ref}":
            continue
        name = ref.rsplit("/", 1)[-1]
        cpu, mem = totals.get(name, (0.0, 0.0))
        totals[name] = (cpu + float(bucket["cpu_time_sec"]), mem + float(bucket["reserved_memory_byte_sec"]))
    rows: list[Sequence[str]] = []
    total_cost = 0.0
    for name, (cpu_s, mem_bs) in sorted(totals.items()):
        cost = cpu_s / 3600 * CPU_HOUR_USD + mem_bs / 1024**3 / 3600 * GB_HOUR_USD
        total_cost += cost
        rows.append((name, f"{cpu_s / 3600:.3f}", f"{mem_bs / 1024**3 / 3600:.3f}", f"${cost:.4f}"))
    since = start.timestamp()
    runs = [r for r in read_records() if datetime.fromisoformat(str(r["ts"])).timestamp() >= since]
    busy_s = sum(float(str(r.get("duration_s", 0))) for r in runs)
    print(f"last {days} day(s){' (partial data)' if payload.get('partial') else ''}")
    if rows:
        _print_table(("worker", "cpu-h", "gb-h", "cost"), rows)
        print(f"total ${total_cost:.4f} compute (storage not included)")
    else:
        print("no per-worker usage recorded by Fly in this window yet (its usage data lags)")
    print(f"{len(runs)} run(s) from this machine, {busy_s / 60:.1f} min of wall time")
    return 0


def _plan(name: str | None) -> int:
    config = load_config(_repo_root())
    tasks = [_task(config, name)] if name is not None else list(config.tasks.values())
    host = host_slug()
    repo = repo_slug(config.root)
    files = _sync_files(config.root, config.sync_exclude)
    policies = {
        "setup_network": setup_network_rules(config.worker),
        "run_network": run_network_rules(config.worker),
        "privileges": LOCKED_PRIVILEGES,
        "memory": memory_policy(config.worker.memory_mb),
    }
    env = ", ".join(f"{key} {'set' if key in os.environ else 'MISSING'}" for key in config.env_pass) or "none"
    print(f"config   {config.root / 'offload.toml'}")
    print(f"base     {base_key(config)}:{policy_hash(config.worker)}")
    print(f"workers  {worker_prefix(host, repo)}[1-{config.worker.max}]  {config.worker.memory_mb} MiB each")
    print(f"sync     {len(files)} files (tracked and untracked, sync excludes applied)")
    print(f"env      {env}")
    print("policy")
    print(json.dumps(policies, indent=2))
    print()
    _print_table(
        ("task", "where", "shards", "timeout", "run"),
        [(task.name, task.where, str(task.shards), f"{task.timeout_s}s", task.run) for task in tasks],
    )
    return 0


def _status() -> int:
    sprites = Sprites()
    host = host_slug()
    config = _optional_config()
    prefix = None if config is None else worker_prefix(host, repo_slug(config.root))
    wanted = None if config is None else (base_key(config), policy_hash(config.worker))
    rows: list[Sequence[str]] = []
    for info in sorted(host_workers(sprites, host), key=lambda item: item.name):
        cache = read_cache(info.name)
        in_repo = prefix is not None and info.name.startswith(prefix) and info.name.removeprefix(prefix).isdigit()
        current = None if cache is None else (cache.base_key, cache.policy_hash)
        matched = "-" if not in_repo else ("yes" if current == wanted else "no")
        last_used = (
            "-" if cache is None else datetime.fromtimestamp(cache.last_used, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        rows.append((info.name, info.status, "-" if current is None else ":".join(current), matched, last_used))
    if not rows:
        print(f"no workers on host {host}")
        return 0
    _print_table(("name", "status", "base", "match", "last used"), rows)
    return 0


def _down(everything: bool) -> int:
    sprites = Sprites()
    host = host_slug()
    workers = host_workers(sprites, host) if everything else repo_workers(sprites, host, repo_slug(_repo_root()))
    if not workers:
        print("no workers to destroy")
        return 0
    for name in destroy_workers(sprites, [info.name for info in workers]):
        print(f"destroyed {name}")
    return 0


def _task(config: OffloadConfig, name: str) -> TaskSpec:
    task = config.tasks.get(name)
    if task is None:
        known = ", ".join(sorted(config.tasks)) or "none"
        raise OffError(f"unknown task '{name}'; tasks: {known}")
    return task


def _git_root() -> Path | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    if completed.returncode == 0:
        return Path(completed.stdout.strip())
    if "not a git repository" in completed.stderr:
        return None
    raise OffError(f"git rev-parse failed: {completed.stderr.strip()}")


def _repo_root() -> Path:
    root = _git_root()
    if root is None:
        raise OffError("not inside a git repository")
    return root


def _optional_config() -> OffloadConfig | None:
    root = _git_root()
    if root is None or not (root / "offload.toml").is_file():
        return None
    return load_config(root)


def _sync_files(root: Path, exclude: tuple[str, ...]) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "-co", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise OffError(f"git ls-files failed: {completed.stderr.strip()}")
    return [path for path in completed.stdout.split("\0") if path and not _excluded(path, exclude)]


def _excluded(path: str, patterns: tuple[str, ...]) -> bool:
    names = [*path.split("/"), path]
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns for name in names)


def _print_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    table = [header, *rows]
    widths = [max(len(row[column]) for row in table) for column in range(len(header))]
    for row in table:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip())
