import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal


class ConfigError(Exception):
    """Invalid offload.toml, duration, or task request."""


@dataclass(frozen=True)
class WorkerSpec:
    memory_mb: int
    max: int
    egress: tuple[str, ...]
    setup_egress: tuple[str, ...]


@dataclass(frozen=True)
class SetupSpec:
    inputs: tuple[str, ...]
    run: tuple[str, ...]


@dataclass(frozen=True)
class TaskSpec:
    name: str
    run: str
    timeout_s: int
    where: Literal["sprite", "local"]
    shards: int
    artifacts: tuple[str, ...]
    env: Mapping[str, str]


@dataclass(frozen=True)
class OffloadConfig:
    root: Path
    worker: WorkerSpec
    setup: SetupSpec
    sync_exclude: tuple[str, ...]
    env_pass: tuple[str, ...]
    tasks: Mapping[str, TaskSpec]
    warm: tuple[str, ...] = ()


MAX_TIMEOUT_S = 6 * 3600
_TOP_LEVEL_KEYS = frozenset({"version", "worker", "setup", "warm", "sync", "env", "tasks"})
_WORKER_KEYS = frozenset({"memory_mb", "max", "egress", "setup_egress"})
_TASK_KEYS = frozenset({"run", "timeout", "where", "shards", "artifacts", "env"})
_TASK_NAME = re.compile(r"[a-z][a-z0-9-]{0,31}")
_DURATION = re.compile(r"([0-9]+)([smh])")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def parse_duration(text: str) -> int:
    match = _DURATION.fullmatch(text)
    if match is None or int(match.group(1)) == 0:
        raise ConfigError(
            f"bad duration {text!r}: use a positive count of s, m or h, e.g. 90s, 20m, 2h"
        )
    return int(match.group(1)) * _UNIT_SECONDS[match.group(2)]


def parse_timeout(text: str) -> int:
    seconds = parse_duration(text)
    if seconds > MAX_TIMEOUT_S:
        raise ConfigError(f"{text} exceeds the 6h maximum")
    return seconds


def load_config(root: Path) -> OffloadConfig:
    path = root / "offload.toml"
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as error:
        raise ConfigError(f"no offload.toml at {root}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: {error}") from error
    return parse_config(root, data)


def parse_config(root: Path, data: Mapping[str, object]) -> OffloadConfig:
    _check_keys(data, "", _TOP_LEVEL_KEYS)
    version = data.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ConfigError("version: required, must be 1")

    worker_table = _table(data, "", "worker")
    _check_keys(worker_table, "worker", _WORKER_KEYS)
    worker = WorkerSpec(
        memory_mb=_int(worker_table, "worker", "memory_mb", low=512, high=16384, default=4096),
        max=_int(worker_table, "worker", "max", low=1, high=8, default=2),
        egress=_str_list(worker_table, "worker", "egress"),
        setup_egress=_str_list(worker_table, "worker", "setup_egress"),
    )

    setup_table = _table(data, "", "setup", required=True)
    _check_keys(setup_table, "setup", frozenset({"inputs", "run"}))
    setup = SetupSpec(
        inputs=_setup_inputs(root, setup_table),
        run=tuple(
            _command(line, "setup.run")
            for line in _str_list(setup_table, "setup", "run", min_items=1)
        ),
    )

    warm_table = _table(data, "", "warm")
    _check_keys(warm_table, "warm", frozenset({"run"}))
    warm = tuple(
        _command(line, "warm.run")
        for line in _str_list(warm_table, "warm", "run", min_items=1 if warm_table else 0)
    )

    sync_table = _table(data, "", "sync")
    _check_keys(sync_table, "sync", frozenset({"exclude"}))
    env_table = _table(data, "", "env")
    _check_keys(env_table, "env", frozenset({"pass"}))

    tasks_table = _table(data, "", "tasks", required=True)
    tasks = {name: _task(name, body, worker) for name, body in tasks_table.items()}
    if not tasks:
        raise ConfigError("tasks: define at least one task")

    return OffloadConfig(
        root=root,
        worker=worker,
        setup=setup,
        sync_exclude=_str_list(sync_table, "sync", "exclude"),
        env_pass=tuple(
            _env_name(name, "env.pass") for name in _str_list(env_table, "env", "pass")
        ),
        tasks=MappingProxyType(tasks),
        warm=warm,
    )


def _task(name: str, body: object, worker: WorkerSpec) -> TaskSpec:
    path = f"tasks.{name}"
    if not _TASK_NAME.fullmatch(name):
        raise ConfigError(
            f"{path}: invalid task name, use lowercase letters, digits and dashes, "
            "starting with a letter, at most 32 characters"
        )
    table = _as_table(body, path)
    _check_keys(table, path, _TASK_KEYS)
    return TaskSpec(
        name=name,
        run=_command(_str(table, path, "run"), f"{path}.run"),
        timeout_s=_timeout(_str(table, path, "timeout"), f"{path}.timeout"),
        where=_placement(_str(table, path, "where", default="sprite"), f"{path}.where"),
        shards=_int(table, path, "shards", low=1, high=worker.max, default=1),
        artifacts=tuple(
            _relative(item, f"{path}.artifacts")
            for item in _str_list(table, path, "artifacts")
        ),
        env=MappingProxyType(_env(table, path, "env")),
    )


def _setup_inputs(root: Path, table: Mapping[str, object]) -> tuple[str, ...]:
    inputs = tuple(
        _relative(item, "setup.inputs")
        for item in _str_list(table, "setup", "inputs", min_items=1)
    )
    for item in inputs:
        if not (root / item).is_file():
            raise ConfigError(f"setup.inputs: {item} is not a file under {root}")
    return inputs


def _timeout(text: str, where: str) -> int:
    try:
        return parse_timeout(text)
    except ConfigError as error:
        raise ConfigError(f"{where}: {error}") from error


def _placement(value: str, where: str) -> Literal["sprite", "local"]:
    if value == "sprite":
        return "sprite"
    if value == "local":
        return "local"
    raise ConfigError(f"{where}: must be 'sprite' or 'local', got {value!r}")


def _relative(value: str, where: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ConfigError(f"{where}: {value!r} must be relative to the repo root")
    return value


def _command(value: str, where: str) -> str:
    if not value.strip():
        raise ConfigError(f"{where}: command is empty")
    return value


def _env_name(name: str, where: str) -> str:
    if not _ENV_NAME.fullmatch(name):
        raise ConfigError(f"{where}: {name!r} is not an environment variable name")
    return name


def _at(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _check_keys(table: Mapping[str, object], path: str, allowed: frozenset[str]) -> None:
    for key in table:
        if key not in allowed:
            raise ConfigError(f"unknown key {_at(path, key)}")


def _as_table(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{path}: expected a table")
    return value


def _table(
    table: Mapping[str, object], path: str, key: str, *, required: bool = False
) -> Mapping[str, object]:
    value = table.get(key)
    if value is None:
        if required:
            raise ConfigError(f"missing {_at(path, key)}")
        return {}
    return _as_table(value, _at(path, key))


def _str(
    table: Mapping[str, object], path: str, key: str, default: str | None = None
) -> str:
    value = table.get(key)
    if value is None:
        if default is None:
            raise ConfigError(f"missing {_at(path, key)}")
        return default
    if not isinstance(value, str):
        raise ConfigError(f"{_at(path, key)}: expected a string")
    return value


def _int(
    table: Mapping[str, object], path: str, key: str, *, low: int, high: int, default: int
) -> int:
    value = table.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{_at(path, key)}: expected an integer")
    if not low <= value <= high:
        raise ConfigError(f"{_at(path, key)}: must be between {low} and {high}, got {value}")
    return value


def _str_list(
    table: Mapping[str, object], path: str, key: str, *, min_items: int = 0
) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{_at(path, key)}: expected a list of strings")
    if len(value) < min_items:
        raise ConfigError(f"{_at(path, key)}: needs at least {min_items} entry")
    return tuple(value)


def _env(table: Mapping[str, object], path: str, key: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for name, value in _table(table, path, key).items():
        if not isinstance(value, str):
            raise ConfigError(f"{_at(path, key)}.{name}: expected a string")
        env[_env_name(name, _at(path, key))] = value
    return env
