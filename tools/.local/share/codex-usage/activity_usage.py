#!/usr/bin/env python3
"""OMP session activity collector for the usage reporter.

Emits privacy-minimal per-session model activity: provider, model, project
slug, observed title, latest in-window timestamp, and summed tokens. No
paths, no prompts, no session content; titles are only ever strings observed
in session headers.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class ActivityRecord(TypedDict):
    session_id: str | None
    provider: str
    model: str
    project: str | None
    title: str | None
    at_ms: int
    tokens: int | None


class ActivityCollection(TypedDict):
    start_ms: int
    end_ms: int
    records: list[ActivityRecord]
    issues: list[str]


ACTIVITY_MAX_RECORDS = 128
_TEXT_MAX_CHARS = 120

_TOKEN_BUCKETS = ("input", "output", "cacheRead", "cacheWrite")
_ORCHESTRATION_BUCKETS = ("input", "output", "cacheRead")


class _UnreadableFile(Exception):
    pass


def _is_token_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and len(value) > 0


def _count_phrase(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural if plural is not None else singular + 's'}"


def _clean_text(value: object, limit: int = _TEXT_MAX_CHARS) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    return text[:limit]


def _project_slug(cwd: object) -> str | None:
    if not isinstance(cwd, str):
        return None
    path = cwd.replace("\\", "/").rstrip("/")
    if path in ("", "/root", Path.home().as_posix().rstrip("/")):
        return None
    parent, _, name = path.rpartition("/")
    if parent.rpartition("/")[2] in ("home", "Users"):
        return None
    name = name.strip()
    return name[:_TEXT_MAX_CHARS] or None


def _parse_iso_ms(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _session_roots(root: Path) -> list[Path]:
    roots = [root / "agent" / "sessions"]
    try:
        children = sorted(root.joinpath("profiles").iterdir(), key=lambda p: p.name)
    except OSError:
        children = []
    for child in children:
        if child.is_dir():
            roots.append(child / "agent" / "sessions")
    return roots


def _session_files(session_dirs: list[Path], dir_errors: list[OSError]) -> Iterator[Path]:
    seen: set[str] = set()
    for session_dir in sorted(session_dirs):
        for current, dirnames, filenames in os.walk(
            session_dir, followlinks=False, onerror=dir_errors.append
        ):
            dirnames[:] = sorted(dirnames)
            for name in sorted(filenames):
                if not name.lower().endswith(".jsonl"):
                    continue
                full = os.path.join(current, name)
                resolved = os.path.realpath(full)
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield Path(full)


def _session_meta(
    title_entry: dict | None, session_entry: dict
) -> dict[str, str | None]:
    session_id = session_entry.get("id")
    return {
        "session_id": session_id if _nonempty(session_id) else None,
        "title": _clean_text(
            title_entry.get("title") if title_entry else None
        )
        or _clean_text(session_entry.get("title")),
        "project": _project_slug(session_entry.get("cwd")),
    }


def _read_header(path: Path) -> tuple[bool, int, dict[str, str | None] | None]:
    checked = 0
    title_entry: dict | None = None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                checked += 1
                try:
                    entry = json.loads(raw)
                except ValueError:
                    return (False, 1, None)
                if not isinstance(entry, dict):
                    return (False, 1, None)
                if checked == 1 and entry.get("type") == "title":
                    title_entry = entry
                    continue
                if entry.get("type") == "session":
                    return (True, 0, _session_meta(title_entry, entry))
                return (False, 0, None)
    except (OSError, UnicodeDecodeError):
        raise _UnreadableFile(path.name)
    return (False, 0, None)


def _candidate_fields(entry: dict) -> tuple | None:
    entry_type = entry.get("type")
    if entry_type == "message":
        message = entry.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            return None
        usage = message.get("usage")
        if usage is None:
            return None
        numeric = message.get("timestamp")
        if _is_number(numeric) and numeric > 0:
            timestamp_ms = int(numeric)
        else:
            timestamp_ms = _parse_iso_ms(entry.get("timestamp"))
        return (message.get("provider"), message.get("model"), usage, timestamp_ms)
    if entry_type == "model_usage":
        usage = entry.get("usage")
        if usage is None:
            return None
        return (
            entry.get("provider"),
            entry.get("model"),
            usage,
            _parse_iso_ms(entry.get("timestamp")),
        )
    return None


def _resolve_tokens(usage: object) -> tuple[int, bool]:
    if not isinstance(usage, dict):
        return (0, False)
    total = usage.get("totalTokens")
    if total is not None:
        if _is_token_int(total):
            return (total, True)
        return (0, False)
    buckets: list[int] = []
    for key in _TOKEN_BUCKETS:
        value = usage.get(key)
        if value is None:
            continue
        if not _is_token_int(value):
            return (0, False)
        buckets.append(value)
    orchestration = usage.get("orchestration")
    if orchestration is not None:
        if not isinstance(orchestration, dict):
            return (0, False)
        for key in _ORCHESTRATION_BUCKETS:
            value = orchestration.get(key)
            if value is None:
                continue
            if not _is_token_int(value):
                return (0, False)
            buckets.append(value)
    if not buckets:
        return (0, False)
    return (sum(buckets), True)


def _entry_activity(
    text: str, start_ms: int, end_ms: int
) -> tuple[str, tuple[str, str, int, int | None] | None]:
    if not text.strip():
        return ("skip", None)
    try:
        entry = json.loads(text)
    except ValueError:
        return ("malformed-line", None)
    if not isinstance(entry, dict):
        return ("malformed-line", None)
    fields = _candidate_fields(entry)
    if fields is None:
        return ("skip", None)
    provider, model, usage, at_ms = fields
    if at_ms is None or at_ms < start_ms or at_ms >= end_ms:
        return ("skip", None)
    if not (_nonempty(provider) and _nonempty(model)):
        return ("malformed", None)
    tokens, tokens_ok = _resolve_tokens(usage)
    if not tokens_ok:
        return ("malformed", (provider, model, at_ms, None))
    return ("ok", (provider, model, at_ms, tokens))


def _file_groups(
    path: Path, start_ms: int, end_ms: int, issues: list[str]
) -> dict[tuple[str, str], dict]:
    groups: dict[tuple[str, str], dict] = {}
    bad_lines = 0
    malformed = 0
    unreadable = False

    def absorb(
        status: str,
        payload: tuple[str, str, int, int | None] | None,
        final: bool,
        complete: bool,
    ) -> None:
        nonlocal bad_lines, malformed
        if status == "malformed-line":
            if not final or complete:
                bad_lines += 1
            return
        if status == "malformed":
            malformed += 1
        if payload is None:
            return
        provider, model, at_ms, tokens = payload
        slot = groups.setdefault(
            (provider, model), {"at_ms": 0, "tokens": 0, "has_valid": False}
        )
        slot["at_ms"] = max(slot["at_ms"], at_ms)
        if tokens is not None:
            slot["tokens"] += tokens
            slot["has_valid"] = True

    try:
        with open(path, "rb") as binary:
            binary.seek(0, os.SEEK_END)
            complete = True
            if binary.tell():
                binary.seek(-1, os.SEEK_END)
                complete = binary.read(1) == b"\n"
        with open(path, "r", encoding="utf-8") as handle:
            pending: str | None = None
            for raw in handle:
                if pending is not None:
                    absorb(*_entry_activity(pending, start_ms, end_ms), False, complete)
                pending = raw
            if pending is not None:
                absorb(*_entry_activity(pending, start_ms, end_ms), True, complete)
    except (OSError, UnicodeDecodeError):
        unreadable = True
    name = path.name
    if unreadable:
        issues.append(f"unreadable file: {name}")
    if bad_lines:
        issues.append(f"{name}: {_count_phrase(bad_lines, 'malformed line')}")
    if malformed:
        issues.append(f"{name}: {_count_phrase(malformed, 'malformed usage record')}")
    return groups


def collect_activity(root: Path, start_ms: int, end_ms: int) -> ActivityCollection:
    root = Path(root)
    if not root.is_dir():
        return {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "records": [],
            "issues": ["session root not found"],
        }
    session_dirs = [entry for entry in _session_roots(root) if entry.is_dir()]
    if not session_dirs:
        return {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "records": [],
            "issues": ["no session directories found"],
        }
    issues: list[str] = []
    dir_errors: list[OSError] = []
    grouped: dict[tuple, dict] = {}
    for path in _session_files(session_dirs, dir_errors):
        try:
            if os.stat(path).st_mtime * 1000 < start_ms:
                continue
        except OSError:
            issues.append(f"unreadable file: {path.name}")
            continue
        try:
            is_session, bad_header, meta = _read_header(path)
        except _UnreadableFile:
            issues.append(f"unreadable file: {path.name}")
            continue
        if bad_header:
            issues.append(f"{path.name}: {_count_phrase(bad_header, 'malformed line')}")
        if not is_session or meta is None:
            continue
        for (provider, model), slot in _file_groups(
            path, start_ms, end_ms, issues
        ).items():
            key = (meta["session_id"], meta["title"], meta["project"], provider, model)
            target = grouped.setdefault(
                key, {"at_ms": 0, "tokens": 0, "has_valid": False}
            )
            target["at_ms"] = max(target["at_ms"], slot["at_ms"])
            target["tokens"] += slot["tokens"]
            target["has_valid"] = target["has_valid"] or slot["has_valid"]
    bad_dirs = set()
    for error in dir_errors:
        filename = getattr(error, "filename", None)
        if isinstance(filename, str) and filename:
            bad_dirs.add(os.path.basename(filename) or filename)
    for name in sorted(bad_dirs):
        issues.append(f"unreadable directory: {name}")
    ranked = sorted(
        grouped.items(),
        key=lambda item: (-item[1]["at_ms"],) + _key_text(item[0]),
    )
    records: list[ActivityRecord] = [
        {
            "session_id": key[0],
            "provider": key[3],
            "model": key[4],
            "project": key[2],
            "title": key[1],
            "at_ms": slot["at_ms"],
            "tokens": slot["tokens"] if slot["has_valid"] else None,
        }
        for key, slot in ranked[:ACTIVITY_MAX_RECORDS]
    ]
    records.sort(
        key=lambda record: (
            record["at_ms"],
            record["provider"],
            record["model"],
            record["session_id"] or "",
        )
    )
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "records": records,
        "issues": issues,
    }


def _validated_activity_record(
    entry: object, start_ms: int, end_ms: int
) -> ActivityRecord | None:
    if not isinstance(entry, dict):
        return None
    session_id = entry.get("session_id")
    if session_id is not None and not _nonempty(session_id):
        return None
    provider = entry.get("provider")
    model = entry.get("model")
    if not (_nonempty(provider) and _nonempty(model)):
        return None
    at_ms = entry.get("at_ms")
    if not isinstance(at_ms, int) or isinstance(at_ms, bool):
        return None
    if at_ms < start_ms or at_ms >= end_ms:
        return None
    tokens = entry.get("tokens")
    if tokens is not None and not _is_token_int(tokens):
        return None
    project = entry.get("project")
    title = entry.get("title")
    if project is not None and not isinstance(project, str):
        return None
    if title is not None and not isinstance(title, str):
        return None
    return {
        "session_id": session_id,
        "provider": provider,
        "model": model,
        "project": _project_slug(project),
        "title": _clean_text(title),
        "at_ms": at_ms,
        "tokens": tokens,
    }


def _validated_activity_records(
    label: str,
    collection: object,
    start_ms: int,
    end_ms: int,
    issues: list[str],
) -> list[ActivityRecord] | None:
    if not isinstance(collection, dict):
        issues.append(f"{label}: invalid activity collection, source ignored")
        return None
    if (
        not isinstance(collection.get("start_ms"), int)
        or not isinstance(collection.get("end_ms"), int)
        or collection.get("start_ms") != start_ms
        or collection.get("end_ms") != end_ms
    ):
        issues.append(f"{label}: activity window mismatch, source ignored")
        return None
    raw_records = collection.get("records")
    raw_issues = collection.get("issues")
    if (
        not isinstance(raw_records, list)
        or not isinstance(raw_issues, list)
        or not all(isinstance(item, str) for item in raw_issues)
    ):
        issues.append(f"{label}: invalid activity collection, source ignored")
        return None
    records: list[ActivityRecord] = []
    skipped = 0
    for entry in raw_records:
        record = _validated_activity_record(entry, start_ms, end_ms)
        if record is None:
            skipped += 1
            continue
        records.append(record)
    if skipped:
        issues.append(
            f"{label}: skipped {_count_phrase(skipped, 'invalid activity record')}"
        )
    return records


def _best_text(values: Iterable[object]) -> str | None:
    observed = [value for value in values if _nonempty(value)]
    return max(observed) if observed else None


def _key_text(key: tuple) -> tuple:
    return tuple((0, None) if part is None else (1, part) for part in key)


def merge_activity(
    collections: list[tuple[str, ActivityCollection]],
    start_ms: int,
    end_ms: int,
    issues: list[str] | None = None,
) -> list[ActivityRecord]:
    sink = issues if issues is not None else []
    grouped: dict[tuple, list[ActivityRecord]] = {}
    for label, collection in collections:
        records = _validated_activity_records(label, collection, start_ms, end_ms, sink)
        if records is None:
            continue
        for item in collection["issues"]:
            sink.append(f"{label}: {item}")
        for record in records:
            if record["session_id"] is not None:
                key = (record["session_id"], record["provider"], record["model"])
            else:
                key = (
                    None,
                    record["provider"],
                    record["model"],
                    record["project"],
                    record["title"],
                    record["at_ms"],
                    record["tokens"],
                )
            grouped.setdefault(key, []).append(record)
    merged: list[ActivityRecord] = []
    for key in sorted(grouped, key=_key_text):
        copies = grouped[key]
        token_values = {copy["tokens"] for copy in copies if copy["tokens"] is not None}
        merged.append(
            {
                "session_id": key[0],
                "provider": key[1],
                "model": key[2],
                "project": _best_text(copy["project"] for copy in copies),
                "title": _best_text(copy["title"] for copy in copies),
                "at_ms": max(copy["at_ms"] for copy in copies),
                "tokens": max(token_values) if token_values else None,
            }
        )
    merged.sort(
        key=lambda record: (
            -record["at_ms"],
            -(record["tokens"] if record["tokens"] is not None else -1),
            record["provider"],
            record["model"],
            record["session_id"] or "",
        )
    )
    return merged[:ACTIVITY_MAX_RECORDS]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=str(Path.home() / ".omp"))
    parser.add_argument("--start-ms", required=True, type=int)
    parser.add_argument("--end-ms", required=True, type=int)
    args = parser.parse_args(argv)
    if args.start_ms < 0 or args.end_ms < 0 or args.start_ms >= args.end_ms:
        parser.error("invalid time window")
    collection = collect_activity(
        Path(args.root).expanduser(), args.start_ms, args.end_ms
    )
    print(json.dumps(collection))
    return 2 if collection["issues"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
