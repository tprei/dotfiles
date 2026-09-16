#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import TypedDict


class HistorySample(TypedDict):
    recorded_at_ms: int
    provider: str
    account_key: str
    limit_id: str
    used_fraction: float


class HistoryCollection(TypedDict):
    start_ms: int
    end_ms: int
    samples: list[HistorySample]
    issues: list[str]


class HistorySnapshot(TypedDict):
    start_ms: int
    end_ms: int
    samples: list[HistorySample]
    sources_ok: list[str]
    issues: list[str]


SQLITE_TIMEOUT_SECONDS = 5


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and len(value) > 0


def _history_dbs(root: Path) -> list[Path]:
    paths = [root / "agent" / "agent.db"]
    try:
        children = sorted(root.joinpath("profiles").iterdir(), key=lambda p: p.name)
    except OSError:
        children = []
    for child in children:
        if child.is_dir():
            paths.append(child / "agent" / "agent.db")
    return paths


def _row_sample(row: tuple) -> HistorySample | None:
    recorded_at, provider, account_key, limit_id, used_fraction = row
    if (
        not _is_int(recorded_at)
        or not _nonempty(provider)
        or not _nonempty(account_key)
        or not _nonempty(limit_id)
        or not _is_number(used_fraction)
    ):
        return None
    return {
        "recorded_at_ms": recorded_at,
        "provider": provider,
        "account_key": account_key,
        "limit_id": limit_id,
        "used_fraction": min(1.0, max(0.0, float(used_fraction))),
    }


def collect_history(root: Path, start_ms: int, end_ms: int) -> HistoryCollection:
    root = Path(root)
    samples: list[HistorySample] = []
    issues: list[str] = []
    for path in _history_dbs(root):
        if not path.is_file():
            continue
        try:
            connection = sqlite3.connect(
                f"file:{path}?mode=ro", uri=True, timeout=SQLITE_TIMEOUT_SECONDS
            )
            try:
                cursor = connection.execute(
                    "SELECT recorded_at, provider, account_key, limit_id, used_fraction"
                    " FROM usage_history"
                    " WHERE recorded_at >= ? AND recorded_at < ?"
                    " AND used_fraction IS NOT NULL ORDER BY recorded_at",
                    (start_ms, end_ms),
                )
                rows = cursor.fetchall()
            finally:
                connection.close()
        except (sqlite3.Error, OSError) as error:
            issues.append(f"{path}: unreadable history ({error})")
            continue
        skipped = 0
        for row in rows:
            sample = _row_sample(row)
            if sample is None:
                skipped += 1
                continue
            samples.append(sample)
        if skipped:
            issues.append(f"{path.name}: skipped {skipped} invalid rows")
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "samples": samples,
        "issues": issues,
    }


def _validated_sample(entry: object, start_ms: int, end_ms: int) -> HistorySample | None:
    if not isinstance(entry, dict):
        return None
    recorded_at_ms = entry.get("recorded_at_ms")
    provider = entry.get("provider")
    account_key = entry.get("account_key")
    limit_id = entry.get("limit_id")
    used_fraction = entry.get("used_fraction")
    if (
        not _is_int(recorded_at_ms)
        or not start_ms <= recorded_at_ms < end_ms
        or not _nonempty(provider)
        or not _nonempty(account_key)
        or not _nonempty(limit_id)
        or not _is_number(used_fraction)
        or not 0.0 <= used_fraction <= 1.0
    ):
        return None
    return {
        "recorded_at_ms": recorded_at_ms,
        "provider": provider,
        "account_key": account_key,
        "limit_id": limit_id,
        "used_fraction": float(used_fraction),
    }


def _validated_samples(
    label: str, collection: object, start_ms: int, end_ms: int, issues: list[str]
) -> list[HistorySample] | None:
    if not isinstance(collection, dict):
        issues.append(f"{label}: invalid collection")
        return None
    if (
        collection.get("start_ms") != start_ms
        or collection.get("end_ms") != end_ms
        or not isinstance(collection.get("start_ms"), int)
        or not isinstance(collection.get("end_ms"), int)
    ):
        issues.append(f"{label}: invalid collection")
        return None
    raw_samples = collection.get("samples")
    raw_issues = collection.get("issues")
    if not isinstance(raw_samples, list) or not isinstance(raw_issues, list):
        issues.append(f"{label}: invalid collection")
        return None
    if not all(isinstance(item, str) for item in raw_issues):
        issues.append(f"{label}: invalid collection")
        return None
    samples: list[HistorySample] = []
    for entry in raw_samples:
        sample = _validated_sample(entry, start_ms, end_ms)
        if sample is None:
            issues.append(f"{label}: invalid collection")
            return None
        samples.append(sample)
    return samples


def merge_history(
    collections: list[tuple[str, HistoryCollection]], start_ms: int, end_ms: int
) -> HistorySnapshot:
    issues: list[str] = []
    sources_ok: list[str] = []
    grouped: dict[tuple[str, str, str, int], HistorySample] = {}
    for label, collection in collections:
        samples = _validated_samples(label, collection, start_ms, end_ms, issues)
        if samples is None:
            continue
        sources_ok.append(label)
        for item in collection["issues"]:
            issues.append(f"{label}: {item}")
        for sample in samples:
            key = (
                sample["provider"],
                sample["limit_id"],
                sample["account_key"],
                sample["recorded_at_ms"],
            )
            if key not in grouped:
                grouped[key] = sample
    merged = [grouped[key] for key in sorted(grouped)]
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "samples": merged,
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
    collection = collect_history(
        Path(args.root).expanduser(), args.start_ms, args.end_ms
    )
    print(json.dumps(collection))
    return 2 if collection["issues"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
