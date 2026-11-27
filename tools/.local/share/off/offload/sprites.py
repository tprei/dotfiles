from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

CALL_TIMEOUT_S = 120
LONG_CALL_TIMEOUT_S = 900
DESTROY_RETRY_WAIT_S = 3
SPRITE_RETRY_WAITS_S = (1, 2)


class SpriteError(Exception):
    pass


class SpriteCallError(SpriteError):
    pass


@dataclass(frozen=True)
class SpriteInfo:
    name: str
    status: str
    url_auth: str


@dataclass(frozen=True)
class Checkpoint:
    id: str
    comment: str


def resolve_org() -> str:
    org = os.environ.get("OFF_ORG", "").strip()
    if not org:
        try:
            org = (Path.home() / ".config" / "off" / "org").read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            org = ""
    if not org:
        raise SpriteError("no Sprites org configured; run just sprites-setup")
    return org


def summarize_output(text: str, lines: int = 4) -> str:
    kept = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(kept[-lines:])


class Sprites:
    def __init__(self, *, binary: str | None = None, org: str | None = None) -> None:
        self._binary = binary or os.environ.get("OFF_SPRITE_BIN") or "sprite"
        self._org = org or resolve_org()

    def list_sprites(self, prefix: str) -> list[SpriteInfo]:
        payload = _retry_idempotent(
            lambda: _json_object(self._call(["list", "-o", self._org, "--json", "--prefix", prefix], CALL_TIMEOUT_S))
        )
        sprites = payload.get("sprites")
        if not isinstance(sprites, list):
            raise SpriteError("unexpected sprite list output: no sprites array")
        return [_sprite_info(item) for item in sprites]

    def create(self, name: str) -> None:
        self._call(["create", "-o", self._org, "--skip-console", name], CALL_TIMEOUT_S)

    def destroy(self, name: str) -> None:
        for attempt in (1, 2):
            self._call(["destroy", "-o", self._org, "--force", name], CALL_TIMEOUT_S)
            if not any(info.name == name for info in self.list_sprites(name)):
                return
            if attempt == 1:
                time.sleep(DESTROY_RETRY_WAIT_S)
        raise SpriteError(f"sprite {name} still exists after two destroy attempts")

    def api(
        self,
        name: str,
        path: str,
        method: str = "GET",
        body: object | None = None,
        *,
        timeout: float = CALL_TIMEOUT_S,
    ) -> str:
        return self._call(["api", "-o", self._org, "-s", name, path, "--", *_curl_args(method, body)], timeout)

    def org_api(self, path: str) -> str:
        return self._call(["api", "-o", self._org, path, "--", "-sSf"], CALL_TIMEOUT_S)

    def checkpoints(self, name: str) -> list[Checkpoint]:
        checkpoints: list[Checkpoint] = []
        for item in _retry_idempotent(lambda: _json_list(self.api(name, "/checkpoints"))):
            record = _as_object(item, "checkpoint object")
            checkpoint_id = _text(record, "id")
            if checkpoint_id != "Current":
                checkpoints.append(Checkpoint(id=checkpoint_id, comment=_optional_text(record, "comment")))
        return checkpoints

    def checkpoint(self, name: str, comment: str, *, existing: Collection[str] = ()) -> Checkpoint:
        """Create a checkpoint; `existing` lists ids taken before, so a same-comment older one is never mistaken for it."""
        events = _events(self.api(name, "/checkpoint", "POST", {"comment": comment}, timeout=LONG_CALL_TIMEOUT_S))
        _require_complete(events, "checkpoint")
        created = next(
            (cp for cp in self.checkpoints(name) if cp.comment == comment and cp.id not in existing), None
        )
        if created is None:
            raise SpriteError(f"checkpoint {comment!r} missing from {name} after create")
        return created

    def restore(self, name: str, checkpoint_id: str) -> None:
        path = f"/checkpoints/{checkpoint_id}/restore"
        events = _retry_idempotent(lambda: _events(self.api(name, path, "POST", timeout=LONG_CALL_TIMEOUT_S)))
        _require_complete(events, "restore")

    def delete_checkpoint(self, name: str, checkpoint_id: str) -> None:
        self.api(name, f"/checkpoints/{checkpoint_id}", "DELETE")

    def set_network(self, name: str, rules: list[dict[str, str]]) -> None:
        self.api(name, "/policy/network", "POST", {"rules": rules})

    def set_privileges(self, name: str, policy: Mapping[str, object]) -> None:
        self.api(name, "/policy/privileges", "POST", policy)

    def set_memory(self, name: str, policy: Mapping[str, object]) -> None:
        self.api(name, "/policy/resources", "POST", policy)

    def ensure_private_url(self, name: str, info: SpriteInfo) -> None:
        if info.url_auth != "sprite":
            self._call(["config", "update", "-o", self._org, "-s", name, "--url-auth", "sprite"], CALL_TIMEOUT_S)

    def exec_argv(
        self, name: str, command: list[str], *, cwd: str, uploads: Sequence[tuple[Path, str]]
    ) -> list[str]:
        argv = [self._binary, "exec", "-o", self._org, "-s", name, "--no-stdin", "--no-port-forward", "--dir", cwd]
        for source, dest in uploads:
            argv += ["--file", f"{source}:{dest}"]
        return [*argv, "--", *command]

    def start_exec(
        self, name: str, command: list[str], *, cwd: str, uploads: Sequence[tuple[Path, str]]
    ) -> subprocess.Popen[str]:
        try:
            return subprocess.Popen(
                self.exec_argv(name, command, cwd=cwd, uploads=uploads),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
            )
        except FileNotFoundError as error:
            raise SpriteError(f"sprite binary not found: {self._binary}") from error

    def rsync_shell(self, name: str) -> str:
        return f"{self._binary} exec -o {self._org} -s {name} --stdin --"

    def _call(self, args: list[str], timeout: float) -> str:
        argv = [self._binary, *args]
        try:
            completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        except FileNotFoundError as error:
            raise SpriteError(f"sprite binary not found: {self._binary}") from error
        except subprocess.TimeoutExpired as error:
            raise SpriteError(f"sprite {args[0]} timed out after {timeout:g}s") from error
        if completed.returncode != 0:
            detail = summarize_output(completed.stderr) or summarize_output(completed.stdout)
            raise SpriteCallError(f"sprite {args[0]} exited {completed.returncode}: {detail}")
        return completed.stdout


T = TypeVar("T")


def _retry_idempotent(call: Callable[[], T]) -> T:
    for wait in SPRITE_RETRY_WAITS_S:
        try:
            return call()
        except SpriteCallError:
            time.sleep(wait)
    return call()


def _curl_args(method: str, body: object | None) -> list[str]:
    args = ["-sSf", "-X", method]
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    return args


def _load(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise SpriteError(f"unexpected sprite output: {error}") from error


def _json_object(text: str) -> dict[str, object]:
    return _as_object(_load(text), "JSON object")


def _json_list(text: str) -> list[object]:
    value = _load(text)
    if not isinstance(value, list):
        raise SpriteError("unexpected sprite output: expected a JSON list")
    return value


def _events(text: str) -> list[dict[str, object]]:
    return [_as_object(_load(line), "NDJSON event") for line in text.splitlines() if line.strip()]


def _require_complete(events: list[dict[str, object]], what: str) -> None:
    for event in events:
        if event.get("type") == "error":
            raise SpriteError(f"{what} failed: {json.dumps(event)}")
    if not any(event.get("type") == "complete" for event in events):
        raise SpriteError(f"{what} ended without a complete event")


def _as_object(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SpriteError(f"unexpected sprite output: expected {what}")
    return value


def _text(record: Mapping[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str):
        raise SpriteError(f"unexpected sprite output: {key} is not a string")
    return value


def _optional_text(record: Mapping[str, object], key: str) -> str:
    value = record.get(key, "")
    if not isinstance(value, str):
        raise SpriteError(f"unexpected sprite output: {key} is not a string")
    return value


def _sprite_info(item: object) -> SpriteInfo:
    record = _as_object(item, "sprite object")
    settings = _as_object(record.get("url_settings"), "url_settings object")
    return SpriteInfo(name=_text(record, "name"), status=_text(record, "status"), url_auth=_text(settings, "auth"))
