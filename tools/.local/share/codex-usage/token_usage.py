#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class UsageRecord(TypedDict):
    entry_id: str
    timestamp_ms: int
    provider: str
    model: str
    api: str
    tokens: int
    estimated_usd: float | None


class Collection(TypedDict):
    start_ms: int
    end_ms: int
    records: list[UsageRecord]
    issues: list[str]


class ProviderTotal(TypedDict):
    provider: str
    tokens: int
    estimated_usd: float
    unpriced_records: int


class TokenSnapshot(TypedDict):
    start_ms: int
    end_ms: int
    providers: list[ProviderTotal]
    sources_ok: list[str]
    issues: list[str]


_BASELINE_PROVIDERS = ("openai-codex", "anthropic", "google-antigravity", "opencode-go", "zai")
_DISPLAY_PROVIDERS = {"antigravity-cli": "google-antigravity"}
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


def _read_header(path: Path) -> tuple[bool, int]:
    checked = 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                checked += 1
                try:
                    entry = json.loads(raw)
                except ValueError:
                    return (False, 1)
                if not isinstance(entry, dict):
                    return (False, 1)
                if checked == 1 and entry.get("type") == "title":
                    continue
                return (entry.get("type") == "session", 0)
    except (OSError, UnicodeDecodeError):
        raise _UnreadableFile(path.name)
    return (False, 0)


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
        return (
            entry.get("id"),
            message.get("provider"),
            message.get("model"),
            message.get("api"),
            usage,
            timestamp_ms,
        )
    if entry_type == "model_usage":
        usage = entry.get("usage")
        if usage is None:
            return None
        return (
            entry.get("id"),
            entry.get("provider"),
            entry.get("model"),
            entry.get("api"),
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


def _resolve_cost(usage: dict, tokens: int) -> tuple[float | None, bool]:
    cost = usage.get("cost")
    if cost is None:
        total_cost = None
    elif isinstance(cost, dict):
        total_cost = cost.get("total")
    else:
        return (None, False)
    if total_cost is None:
        return (0.0 if tokens == 0 else None, True)
    if _is_number(total_cost):
        if total_cost > 0:
            return (float(total_cost), True)
        if total_cost == 0:
            return (0.0 if tokens == 0 else None, True)
        return (None, False)
    return (None, False)


def _build_record(
    entry: dict, start_ms: int, end_ms: int
) -> tuple[UsageRecord | None, str]:
    fields = _candidate_fields(entry)
    if fields is None:
        return (None, "ignore")
    entry_id, provider, model, api, usage, timestamp_ms = fields
    if timestamp_ms is None or timestamp_ms < start_ms or timestamp_ms >= end_ms:
        return (None, "ignore")
    if not (
        _nonempty(entry_id)
        and _nonempty(provider)
        and _nonempty(model)
        and _nonempty(api)
    ):
        return (None, "malformed")
    tokens, tokens_ok = _resolve_tokens(usage)
    if not tokens_ok:
        return (None, "malformed")
    estimated, cost_ok = _resolve_cost(usage, tokens)
    record: UsageRecord = {
        "entry_id": entry_id,
        "timestamp_ms": timestamp_ms,
        "provider": provider,
        "model": model,
        "api": api,
        "tokens": tokens,
        "estimated_usd": estimated,
    }
    return (record, "ok" if cost_ok else "bad-cost")


def _parse_line(
    text: str, start_ms: int, end_ms: int
) -> tuple[str, UsageRecord | None]:
    if not text.strip():
        return ("skip", None)
    try:
        entry = json.loads(text)
    except ValueError:
        return ("malformed-line", None)
    if not isinstance(entry, dict):
        return ("malformed-line", None)
    record, outcome = _build_record(entry, start_ms, end_ms)
    if outcome == "ignore":
        return ("skip", None)
    if outcome == "malformed":
        return ("malformed-record", None)
    return ("bad-cost" if outcome == "bad-cost" else "ok", record)


def _stream_records(
    path: Path, start_ms: int, end_ms: int
) -> tuple[list[UsageRecord], list[str]]:
    records: list[UsageRecord] = []
    bad_lines = 0
    bad_records = 0
    bad_costs = 0
    truncated = False
    unreadable = False

    def absorb(status: str, record: UsageRecord | None, final: bool) -> None:
        nonlocal bad_lines, bad_records, bad_costs, truncated
        if status == "ok":
            if record is not None:
                records.append(record)
        elif status == "bad-cost":
            if record is not None:
                records.append(record)
            bad_costs += 1
        elif status == "malformed-record":
            bad_records += 1
        elif status == "malformed-line":
            if final and not complete:
                truncated = True
            else:
                bad_lines += 1

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
                    absorb(*_parse_line(pending, start_ms, end_ms), False)
                pending = raw
            if pending is not None:
                absorb(*_parse_line(pending, start_ms, end_ms), True)
    except (OSError, UnicodeDecodeError):
        unreadable = True
    name = path.name
    file_issues: list[str] = []
    if unreadable:
        file_issues.append(f"unreadable file: {name}")
    if bad_lines:
        file_issues.append(f"{name}: {_count_phrase(bad_lines, 'malformed line')}")
    if truncated:
        file_issues.append(f"{name}: incomplete trailing line")
    if bad_records:
        file_issues.append(
            f"{name}: {_count_phrase(bad_records, 'malformed usage record')}"
        )
    if bad_costs:
        file_issues.append(f"{name}: {_count_phrase(bad_costs, 'record')} with invalid cost")
    return (records, file_issues)


def collect_usage(root: Path, start_ms: int, end_ms: int) -> Collection:
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
    records: list[UsageRecord] = []
    issues: list[str] = []
    dir_errors: list[OSError] = []
    for path in _session_files(session_dirs, dir_errors):
        try:
            if os.stat(path).st_mtime * 1000 < start_ms:
                continue
        except OSError:
            issues.append(f"unreadable file: {path.name}")
            continue
        try:
            is_session, bad_header = _read_header(path)
        except _UnreadableFile:
            issues.append(f"unreadable file: {path.name}")
            continue
        if bad_header:
            issues.append(
                f"{path.name}: {_count_phrase(bad_header, 'malformed line')}"
            )
        if not is_session:
            continue
        file_records, file_issues = _stream_records(path, start_ms, end_ms)
        records.extend(file_records)
        issues.extend(file_issues)
    bad_dirs = set()
    for error in dir_errors:
        filename = getattr(error, "filename", None)
        if isinstance(filename, str) and filename:
            bad_dirs.add(os.path.basename(filename) or filename)
    for name in sorted(bad_dirs):
        issues.append(f"unreadable directory: {name}")
    records.sort(
        key=lambda item: (
            item["timestamp_ms"],
            item["entry_id"],
            item["provider"],
            item["model"],
            item["api"],
        )
    )
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "records": records,
        "issues": issues,
    }


def _validated_record(entry: object, start_ms: int, end_ms: int) -> UsageRecord | None:
    if not isinstance(entry, dict):
        return None
    entry_id = entry.get("entry_id")
    provider = entry.get("provider")
    model = entry.get("model")
    api = entry.get("api")
    if not (
        _nonempty(entry_id)
        and _nonempty(provider)
        and _nonempty(model)
        and _nonempty(api)
    ):
        return None
    timestamp_ms = entry.get("timestamp_ms")
    if (
        not isinstance(timestamp_ms, int)
        or isinstance(timestamp_ms, bool)
        or timestamp_ms < start_ms
        or timestamp_ms >= end_ms
    ):
        return None
    tokens = entry.get("tokens")
    if not _is_token_int(tokens):
        return None
    estimated = entry.get("estimated_usd")
    if estimated is None:
        price = None
    elif _is_number(estimated) and estimated >= 0:
        price = float(estimated)
    else:
        return None
    return {
        "entry_id": entry_id,
        "timestamp_ms": timestamp_ms,
        "provider": provider,
        "model": model,
        "api": api,
        "tokens": tokens,
        "estimated_usd": price,
    }


def _validated_records(
    label: str, collection: object, start_ms: int, end_ms: int, issues: list[str]
) -> list[UsageRecord] | None:
    if not isinstance(collection, dict):
        issues.append(f"{label}: invalid collection, source ignored")
        return None
    if (
        collection.get("start_ms") != start_ms
        or collection.get("end_ms") != end_ms
        or not isinstance(collection.get("start_ms"), int)
        or not isinstance(collection.get("end_ms"), int)
    ):
        issues.append(f"{label}: window mismatch, source ignored")
        return None
    raw_records = collection.get("records")
    raw_issues = collection.get("issues")
    if not isinstance(raw_records, list) or not isinstance(raw_issues, list):
        issues.append(f"{label}: invalid collection, source ignored")
        return None
    if not all(isinstance(item, str) for item in raw_issues):
        issues.append(f"{label}: invalid collection, source ignored")
        return None
    records: list[UsageRecord] = []
    for entry in raw_records:
        record = _validated_record(entry, start_ms, end_ms)
        if record is None:
            issues.append(f"{label}: invalid usage record, source ignored")
            return None
        records.append(record)
    return records


def _provider_total(name: str, slot: dict | None) -> ProviderTotal:
    if slot is None:
        return {
            "provider": name,
            "tokens": 0,
            "estimated_usd": 0.0,
            "unpriced_records": 0,
        }
    return {
        "provider": name,
        "tokens": slot["tokens"],
        "estimated_usd": math.fsum(slot["costs"]),
        "unpriced_records": slot["unpriced"],
    }


def merge_usage(
    collections: list[tuple[str, Collection]], start_ms: int, end_ms: int
) -> TokenSnapshot:
    issues: list[str] = []
    sources_ok: list[str] = []
    grouped: dict[tuple, list[UsageRecord]] = {}
    for label, collection in collections:
        records = _validated_records(label, collection, start_ms, end_ms, issues)
        if records is None:
            continue
        sources_ok.append(label)
        for item in collection["issues"]:
            issues.append(f"{label}: {item}")
        for record in records:
            key = (
                record["entry_id"],
                record["timestamp_ms"],
                record["provider"],
                record["model"],
                record["api"],
            )
            grouped.setdefault(key, []).append(record)
    token_conflicts = 0
    price_conflicts = 0
    merged: list[tuple[str, int, float | None]] = []
    for key in sorted(grouped):
        copies = grouped[key]
        token_values = {copy["tokens"] for copy in copies}
        if len(token_values) > 1:
            token_conflicts += 1
            continue
        tokens = next(iter(token_values))
        prices = {
            copy["estimated_usd"]
            for copy in copies
            if copy["estimated_usd"] is not None and copy["estimated_usd"] > 0
        }
        if len(prices) > 1:
            price_conflicts += 1
            continue
        if prices:
            estimated: float | None = next(iter(prices))
        elif tokens == 0 and any(
            copy["estimated_usd"] is not None for copy in copies
        ):
            estimated = 0.0
        else:
            estimated = None
        merged.append((key[2], tokens, estimated))
    totals: dict[str, dict] = {}
    for provider, tokens, estimated in merged:
        display = _DISPLAY_PROVIDERS.get(provider, provider)
        slot = totals.setdefault(
            display, {"tokens": 0, "costs": [], "unpriced": 0, "raw": set()}
        )
        slot["tokens"] += tokens
        slot["raw"].add(provider)
        if estimated is None:
            slot["unpriced"] += 1
        else:
            slot["costs"].append(estimated)
    providers: list[ProviderTotal] = []
    for name in _BASELINE_PROVIDERS:
        providers.append(_provider_total(name, totals.pop(name, None)))
    for name in sorted(totals, key=lambda item: min(totals[item]["raw"])):
        providers.append(_provider_total(name, totals[name]))
    if token_conflicts:
        issues.append(
            f"excluded {_count_phrase(token_conflicts, 'disputed identity', 'disputed identities')} with conflicting tokens"
        )
    if price_conflicts:
        issues.append(
            f"excluded {_count_phrase(price_conflicts, 'disputed identity', 'disputed identities')} with conflicting prices"
        )
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "providers": providers,
        "sources_ok": sources_ok,
        "issues": issues,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-ms", required=True, type=int)
    parser.add_argument("--end-ms", required=True, type=int)
    parser.add_argument("--root", default=str(Path.home() / ".omp"))
    args = parser.parse_args(argv)
    if args.start_ms < 0 or args.end_ms < 0 or args.start_ms >= args.end_ms:
        parser.error("invalid time window")
    collection = collect_usage(
        Path(args.root).expanduser(), args.start_ms, args.end_ms
    )
    print(json.dumps(collection))
    return 2 if collection["issues"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
