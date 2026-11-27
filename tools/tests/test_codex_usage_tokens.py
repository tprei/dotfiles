import contextlib
import gzip
import importlib.machinery
import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
SHARE_DIR = TOOLS / ".local" / "share" / "codex-usage"
COLLECTOR_PATH = SHARE_DIR / "token_usage.py"
HISTORY_PATH = SHARE_DIR / "usage_history.py"
REPORTER_PATH = TOOLS / ".local" / "bin" / "codex-usage-check"

if str(SHARE_DIR) not in sys.path:
    sys.path.insert(0, str(SHARE_DIR))

import dashboard
import token_usage
import usage_history


def load_reporter():
    loader = importlib.machinery.SourceFileLoader(
        "codex_usage_check_under_test", str(REPORTER_PATH)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


reporter = load_reporter()

START_MS = (1_789_000_000_000 // token_usage.DAY_MS) * token_usage.DAY_MS
END_MS = START_MS + 7 * token_usage.DAY_MS
HISTORY_START_MS = (1_789_000_000_000 // token_usage.DAY_MS) * token_usage.DAY_MS
HISTORY_END_MS = HISTORY_START_MS + 7 * token_usage.DAY_MS
BASELINE_PROVIDERS = ["openai-codex", "anthropic", "google-antigravity", "opencode-go", "zai"]
RECORD_KEYS = {"entry_id", "timestamp_ms", "provider", "model", "api", "tokens", "estimated_usd"}
HOUR_MS = 3_600_000
DAY_MS = 86_400_000
FIXED_NOW_MS = 1_789_000_000_000


def iso_z(ms: int) -> str:
    moment = datetime.fromtimestamp(ms // 1000, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


def call_arg(call, index, name):
    if len(call.args) > index:
        return call.args[index]
    return call.kwargs.get(name)


def session_header(session_id="session-1"):
    return {"type": "session", "id": session_id, "timestamp": iso_z(START_MS - 1_000)}


def title_header(text="Unit fixture title"):
    return {"type": "title", "text": text}


def bucket_usage(total_tokens=15, cost_total=0.03, **extra):
    usage = {"input": 10, "output": 5, "totalTokens": total_tokens}
    usage.update(extra)
    if cost_total is not None:
        usage["cost"] = {"total": cost_total}
    return usage


def assistant_entry(entry_id, timestamp_ms, usage=None, provider="zai", model="glm-5.3",
                    api="openai-completions", message_timestamp=None):
    return {
        "type": "message",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "message": {
            "role": "assistant",
            "provider": provider,
            "model": model,
            "api": api,
            "timestamp": timestamp_ms if message_timestamp is None else message_timestamp,
            "usage": bucket_usage() if usage is None else usage,
        },
    }


def model_usage_entry(entry_id, timestamp_ms, usage, provider="anthropic",
                      model="claude-opus", api="anthropic-messages"):
    return {
        "type": "model_usage",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "provider": provider,
        "model": model,
        "api": api,
        "usage": usage,
    }


def user_entry(entry_id, timestamp_ms):
    return {
        "type": "message",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "message": {"role": "user", "content": [{"type": "text", "text": "unit fixture"}]},
    }


def tool_result_entry(entry_id, timestamp_ms):
    return {
        "type": "toolResult",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "toolCallId": "tool-1",
        "output": {
            "usage": {"totalTokens": 999},
            "provider": "zai",
            "model": "phantom",
            "api": "openai-completions",
        },
    }


def merge_record(entry_id="r1", timestamp_ms=None, provider="openai-codex",
                 model="gpt-5.2", api="responses", tokens=100, estimated_usd=0.25):
    return {
        "entry_id": entry_id,
        "timestamp_ms": timestamp_ms if timestamp_ms is not None else START_MS + 1_000,
        "provider": provider,
        "model": model,
        "api": api,
        "tokens": tokens,
        "estimated_usd": estimated_usd,
    }


def merge_collection(records, issues=None):
    return {"start_ms": START_MS, "end_ms": END_MS, "records": records, "issues": issues or []}


def merge_collections(collections):
    return token_usage.merge_usage(collections, START_MS, END_MS)


def provider_total(snapshot, name):
    for total in snapshot["providers"]:
        if total["provider"] == name:
            return total
    return None


def day_total(snapshot, index):
    return snapshot["days"][index]


def day_provider_total(day, name):
    for total in day["providers"]:
        if total["provider"] == name:
            return total
    return None


def empty_token_snapshot(issues=None):
    snapshot = token_usage.merge_usage([("WSL", merge_collection([]))], START_MS, END_MS)
    if issues:
        snapshot["issues"] = [*issues, *snapshot.get("issues", [])]
    return snapshot


def plain_history_snapshot(samples=None, issues=None):
    return {
        "start_ms": START_MS,
        "end_ms": END_MS,
        "samples": list(samples or []),
        "sources_ok": ["WSL"],
        "issues": list(issues or []),
    }


class TempRootMixin(unittest.TestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="omp-token-tests-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_session(self, relative, entries, mtime_ms=None):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(json.dumps(entry) for entry in entries) + "\n"
        path.write_text(text, encoding="utf-8")
        if mtime_ms is not None:
            os.utime(path, (mtime_ms / 1000, mtime_ms / 1000))
        return path

    def write_text_session(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def collect(self, root=None):
        return token_usage.collect_usage(self.root if root is None else root, START_MS, END_MS)

    def record_ids(self, collection):
        return sorted(record["entry_id"] for record in collection["records"])


class CollectUsageWindowTests(TempRootMixin):
    def test_keeps_record_at_start_and_end_minus_one_excludes_end_and_before(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                session_header(),
                assistant_entry("before", START_MS - 1),
                assistant_entry("at-start", START_MS),
                assistant_entry("near-end", END_MS - 1),
                assistant_entry("at-end", END_MS),
            ],
        )
        collection = self.collect()
        self.assertEqual(collection["start_ms"], START_MS)
        self.assertEqual(collection["end_ms"], END_MS)
        self.assertEqual(collection["issues"], [])
        self.assertEqual(self.record_ids(collection), ["at-start", "near-end"])
        self.assertEqual(
            {record["entry_id"]: record["timestamp_ms"] for record in collection["records"]},
            {"at-start": START_MS, "near-end": END_MS - 1},
        )

    def test_file_mtime_strictly_before_window_skips_in_window_records(self):
        self.write_session(
            "agent/sessions/proj/stale.jsonl",
            [session_header(), assistant_entry("stale", START_MS + 500)],
            mtime_ms=START_MS - 3_600_000,
        )
        self.write_session(
            "agent/sessions/proj/fresh.jsonl",
            [session_header(), assistant_entry("fresh", START_MS + 500)],
        )
        collection = self.collect()
        self.assertEqual(self.record_ids(collection), ["fresh"])


class CollectUsageSourceParsingTests(TempRootMixin):
    def test_title_then_session_header_subagent_file_counts_both_entry_kinds(self):
        self.write_session(
            "agent/sessions/proj/sub/subagent-x.jsonl",
            [
                title_header(),
                session_header(),
                assistant_entry("a1", START_MS + 1_000),
                model_usage_entry("m1", START_MS + 2_000, bucket_usage(total_tokens=10, cost_total=0.02)),
            ],
        )
        collection = self.collect()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(self.record_ids(collection), ["a1", "m1"])

    def test_tool_result_and_user_entries_are_not_usage(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                session_header(),
                assistant_entry("a1", START_MS + 1_000),
                tool_result_entry("t1", START_MS + 2_000),
                user_entry("u1", START_MS + 3_000),
            ],
        )
        collection = self.collect()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(self.record_ids(collection), ["a1"])

    def test_non_session_jsonl_is_ignored(self):
        self.write_session(
            "agent/sessions/proj/not-a-session.jsonl",
            [model_usage_entry("m9", START_MS + 1_000, bucket_usage(total_tokens=50))],
        )
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertEqual(collection["issues"], [])

    def test_profiles_and_main_sessions_are_both_scanned(self):
        self.write_session(
            "agent/sessions/main/session.jsonl",
            [session_header(), assistant_entry("a1", START_MS + 1_000)],
        )
        self.write_session(
            "profiles/mix/agent/sessions/proj/session.jsonl",
            [session_header(), model_usage_entry("m1", START_MS + 2_000, bucket_usage())],
        )
        collection = self.collect()
        self.assertEqual(self.record_ids(collection), ["a1", "m1"])

    def test_numeric_message_timestamp_wins_over_envelope(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_header(), assistant_entry("p1", END_MS - 1, message_timestamp=START_MS + 5_000)],
        )
        collection = self.collect()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(collection["records"][0]["timestamp_ms"], START_MS + 5_000)

    def test_zero_message_timestamp_falls_back_to_envelope_iso(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_header(), assistant_entry("e1", START_MS + 7_000, message_timestamp=0)],
        )
        collection = self.collect()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(collection["records"][0]["timestamp_ms"], START_MS + 7_000)

    def test_failed_request_with_usage_still_counts(self):
        entry = assistant_entry("err-1", START_MS + 1_000, usage=bucket_usage(total_tokens=20, cost_total=0.05))
        entry["message"]["stopReason"] = "error"
        entry["message"]["errorMessage"] = "upstream 500"
        self.write_session("agent/sessions/proj/session.jsonl", [session_header(), entry])
        collection = self.collect()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(self.record_ids(collection), ["err-1"])


class CollectUsageAccountingTests(TempRootMixin):
    def antigravity_collection(self, usage):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                session_header(),
                assistant_entry(
                    "agy-1",
                    START_MS + 1_000,
                    provider="antigravity-cli",
                    model="gemini-3-pro",
                    api="antigravity-cli",
                    usage=usage,
                ),
            ],
        )
        return self.collect()

    def test_authoritative_total_tokens_beats_bucket_sum_and_reasoning(self):
        usage = {
            "input": 268_633,
            "output": 45_255,
            "cacheRead": 4_721_799,
            "totalTokens": 313_888,
            "reasoningTokens": 268_000,
            "cost": {"total": 0},
        }
        collection = self.antigravity_collection(usage)
        self.assertEqual(collection["issues"], [])
        self.assertEqual(collection["records"][0]["tokens"], 313_888)

    def test_missing_total_derives_from_buckets_including_orchestration(self):
        usage = {
            "input": 10,
            "output": 5,
            "cacheRead": 2,
            "cacheWrite": 1,
            "orchestration": {"input": 3, "output": 4, "cacheRead": 5},
            "cost": {"total": 0.01},
        }
        collection = self.antigravity_collection(usage)
        self.assertEqual(collection["issues"], [])
        self.assertEqual(collection["records"][0]["tokens"], 30)

    def test_boolean_total_is_invalid_and_not_fabricated(self):
        collection = self.antigravity_collection({"totalTokens": True, "input": 7})
        self.assertEqual(collection["records"], [])
        self.assertTrue(collection["issues"])

    def test_missing_all_counters_is_issue_not_zero(self):
        collection = self.antigravity_collection({"cost": {"total": 0.05}})
        self.assertEqual(collection["records"], [])
        self.assertTrue(collection["issues"])

    def test_positive_recorded_cost_is_preserved(self):
        usage = {"input": 100, "output": 0, "totalTokens": 100, "cost": {"total": 0.2585}}
        collection = self.antigravity_collection(usage)
        self.assertEqual(collection["records"][0]["estimated_usd"], 0.2585)

    def test_zero_tokens_without_cost_is_priced_zero_not_unpriced(self):
        usage = {"input": 0, "output": 0, "totalTokens": 0}
        collection = self.antigravity_collection(usage)
        self.assertEqual(collection["issues"], [])
        self.assertEqual(collection["records"][0]["tokens"], 0)
        self.assertEqual(collection["records"][0]["estimated_usd"], 0.0)

    def test_zero_price_on_positive_usage_is_unpriced_not_free(self):
        usage = {
            "input": 268_633,
            "output": 45_255,
            "cacheRead": 4_721_799,
            "totalTokens": 313_888,
            "cost": {"total": 0},
        }
        collection = self.antigravity_collection(usage)
        self.assertEqual(collection["issues"], [])
        self.assertIsNone(collection["records"][0]["estimated_usd"])

    def test_missing_cost_on_positive_usage_is_unpriced(self):
        usage = {"input": 5, "output": 0, "totalTokens": 5}
        collection = self.antigravity_collection(usage)
        self.assertIsNone(collection["records"][0]["estimated_usd"])

    def test_malformed_cost_is_unpriced_with_issue(self):
        usage = {"input": 5, "output": 0, "totalTokens": 5, "cost": {"total": "free"}}
        collection = self.antigravity_collection(usage)
        self.assertIsNone(collection["records"][0]["estimated_usd"])
        self.assertTrue(collection["issues"])

    def test_negative_cost_is_issue_even_on_zero_tokens(self):
        usage = {"input": 0, "output": 0, "totalTokens": 0, "cost": {"total": -0.5}}
        collection = self.antigravity_collection(usage)
        self.assertTrue(collection["issues"])
        self.assertEqual(sum(record["tokens"] for record in collection["records"]), 0)
        self.assertTrue(all(record["estimated_usd"] is None for record in collection["records"]))

    def test_records_without_required_identity_are_rejected_with_issues(self):
        missing_api = model_usage_entry("m1", START_MS + 1_000, bucket_usage(), api="")
        missing_id = model_usage_entry("m2", START_MS + 2_000, bucket_usage())
        del missing_id["id"]
        self.write_session(
            "agent/sessions/proj/empty-api.jsonl",
            [session_header(), missing_api],
        )
        self.write_session(
            "agent/sessions/proj/missing-id.jsonl",
            [session_header(), missing_id],
        )
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertTrue(collection["issues"])

    def test_incomplete_trailing_line_keeps_earlier_records(self):
        complete = json.dumps(session_header()) + "\n" + json.dumps(assistant_entry("a1", START_MS + 1_000)) + "\n"
        self.write_text_session(
            "agent/sessions/proj/live.jsonl",
            complete + '{"type": "message", "id": "partial"',
        )
        collection = self.collect()
        self.assertEqual(self.record_ids(collection), ["a1"])
        self.assertTrue(collection["issues"])

    def test_malformed_completed_line_yields_issue_but_keeps_valid_records(self):
        entries = [
            session_header(),
            assistant_entry("a1", START_MS + 1_000),
            assistant_entry("a2", START_MS + 2_000),
        ]
        lines = [json.dumps(entries[0]), json.dumps(entries[1]), '{"type": "message"', json.dumps(entries[2])]
        self.write_text_session("agent/sessions/proj/mixed.jsonl", "\n".join(lines) + "\n")
        collection = self.collect()
        self.assertEqual(self.record_ids(collection), ["a1", "a2"])
        self.assertTrue(collection["issues"])

    def test_unreadable_file_yields_issue_but_other_files_still_count(self):
        blocked = self.write_session(
            "agent/sessions/proj/locked.jsonl",
            [session_header(), assistant_entry("locked", START_MS + 1_000)],
        )
        self.write_session(
            "agent/sessions/proj/open.jsonl",
            [session_header(), assistant_entry("open", START_MS + 1_000)],
        )
        os.chmod(blocked, 0o000)
        self.addCleanup(os.chmod, blocked, 0o644)
        collection = self.collect()
        self.assertEqual(self.record_ids(collection), ["open"])
        self.assertTrue(collection["issues"])

    def test_empty_session_directories_are_valid_zero_usage(self):
        (self.root / "agent" / "sessions" / "proj").mkdir(parents=True)
        (self.root / "profiles" / "mix" / "agent" / "sessions").mkdir(parents=True)
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertEqual(collection["issues"], [])

    def test_missing_root_is_collection_issue_not_zero(self):
        collection = self.collect(self.root / "absent")
        self.assertEqual(collection["records"], [])
        self.assertTrue(collection["issues"])
        self.assertEqual(collection["start_ms"], START_MS)
        self.assertEqual(collection["end_ms"], END_MS)

    def test_root_without_session_directories_is_collection_issue(self):
        (self.root / "unrelated").mkdir()
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertTrue(collection["issues"])

    def test_collection_and_record_wire_schema(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_header(), assistant_entry("a1", START_MS + 1_000)],
        )
        collection = self.collect()
        self.assertEqual(set(collection), {"start_ms", "end_ms", "records", "issues"})
        self.assertEqual(set(collection["records"][0]), RECORD_KEYS)
        self.assertEqual(collection["records"][0]["provider"], "zai")
        self.assertIsInstance(collection["records"][0]["tokens"], int)


class CollectorCliTests(TempRootMixin):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(COLLECTOR_PATH), *arguments],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def cli_arguments(self, root=None):
        return [
            "--start-ms", str(START_MS),
            "--end-ms", str(END_MS),
            "--root", str(self.root if root is None else root),
        ]

    def test_emits_single_json_collection_and_exits_zero(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_header(), assistant_entry("a1", START_MS + 1_000)],
        )
        result = self.run_cli(*self.cli_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"start_ms", "end_ms", "records", "issues"})
        self.assertEqual([record["entry_id"] for record in payload["records"]], ["a1"])
        self.assertEqual(set(payload["records"][0]), RECORD_KEYS)

    def test_empty_usage_exits_zero(self):
        (self.root / "agent" / "sessions" / "proj").mkdir(parents=True)
        result = self.run_cli(*self.cli_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["records"], [])
        self.assertEqual(payload["issues"], [])

    def test_unavailable_root_exits_two_with_usable_json(self):
        result = self.run_cli(*self.cli_arguments(root=self.root / "missing"))
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["records"], [])
        self.assertTrue(payload["issues"])

    def test_argument_errors_exit_two_without_json(self):
        cases = [
            [],
            ["--start-ms", str(START_MS)],
            self.cli_arguments() + ["--bogus"],
            ["--start-ms", "-5", "--end-ms", str(END_MS), "--root", str(self.root)],
            ["--start-ms", str(END_MS), "--end-ms", str(START_MS), "--root", str(self.root)],
            ["--start-ms", str(END_MS), "--end-ms", str(END_MS), "--root", str(self.root)],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout.strip(), "")

def write_history_db(path: Path, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE usage_history ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "recorded_at INTEGER NOT NULL, "
            "provider TEXT NOT NULL, "
            "account_key TEXT NOT NULL, "
            "email TEXT, "
            "account_id TEXT, "
            "limit_id TEXT NOT NULL, "
            "label TEXT NOT NULL, "
            "window_label TEXT, "
            "used_fraction REAL, "
            "status TEXT, "
            "resets_at INTEGER"
            ")"
        )
        conn.executemany(
            "INSERT INTO usage_history "
            "(recorded_at, provider, account_key, limit_id, label, used_fraction) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )


class UsageHistoryCollectorTests(TempRootMixin, unittest.TestCase):
    def collect_history(self, root=None):
        return usage_history.collect_history(
            self.root if root is None else root, START_MS, END_MS
        )

    def test_merges_rows_from_root_and_profile_databases(self):
        write_history_db(
            self.root / "agent" / "agent.db",
            [(START_MS + 1_000, "openai-codex", "acct1", "limit1", "label1", 0.25)],
        )
        write_history_db(
            self.root / "profiles" / "mix" / "agent" / "agent.db",
            [(START_MS + 2_000, "anthropic", "acct2", "limit2", "label2", 0.50)],
        )
        collection = self.collect_history()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(collection["start_ms"], START_MS)
        self.assertEqual(collection["end_ms"], END_MS)
        self.assertEqual(
            collection["samples"],
            [
                {
                    "recorded_at_ms": START_MS + 1_000,
                    "provider": "openai-codex",
                    "account_key": "acct1",
                    "limit_id": "limit1",
                    "used_fraction": 0.25,
                },
                {
                    "recorded_at_ms": START_MS + 2_000,
                    "provider": "anthropic",
                    "account_key": "acct2",
                    "limit_id": "limit2",
                    "used_fraction": 0.50,
                },
            ],
        )

    def test_excludes_out_of_window_rows(self):
        rows = [
            (START_MS - 1, "openai-codex", "acct", "limit1", "label1", 0.1),
            (START_MS, "openai-codex", "acct", "limit1", "label1", 0.2),
            (END_MS - 1, "openai-codex", "acct", "limit1", "label1", 0.3),
            (END_MS, "openai-codex", "acct", "limit1", "label1", 0.4),
        ]
        write_history_db(self.root / "agent" / "agent.db", rows)
        collection = self.collect_history()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(
            [s["recorded_at_ms"] for s in collection["samples"]],
            [START_MS, END_MS - 1],
        )

    def test_excludes_null_used_fraction_without_counting_as_invalid(self):
        rows = [
            (START_MS + 1_000, "openai-codex", "acct", "limit1", "label1", None),
            (START_MS + 2_000, "openai-codex", "acct", "limit1", "label1", 0.5),
        ]
        write_history_db(self.root / "agent" / "agent.db", rows)
        collection = self.collect_history()
        self.assertEqual(collection["issues"], [])
        self.assertEqual(len(collection["samples"]), 1)
        self.assertEqual(collection["samples"][0]["used_fraction"], 0.5)

    def test_invalid_row_with_empty_provider_is_skipped_with_issue(self):
        rows = [
            (START_MS + 1_000, "", "acct", "limit1", "label1", 0.5),
            (START_MS + 2_000, "openai-codex", "acct", "limit1", "label1", 0.5),
        ]
        write_history_db(self.root / "agent" / "agent.db", rows)
        collection = self.collect_history()
        self.assertEqual(collection["issues"], ["agent.db: skipped 1 invalid rows"])
        self.assertEqual(len(collection["samples"]), 1)
        self.assertEqual(collection["samples"][0]["provider"], "openai-codex")

    def test_clamps_used_fraction_bounds(self):
        rows = [
            (START_MS + 1_000, "openai-codex", "acct", "limit1", "label1", 1.4),
            (START_MS + 2_000, "anthropic", "acct", "limit2", "label2", -0.2),
        ]
        write_history_db(self.root / "agent" / "agent.db", rows)
        collection = self.collect_history()
        self.assertEqual(collection["issues"], [])
        self.assertEqual([s["used_fraction"] for s in collection["samples"]], [1.0, 0.0])

    def test_root_without_databases_returns_empty_samples_and_no_issues(self):
        collection = self.collect_history()
        self.assertEqual(collection["samples"], [])
        self.assertEqual(collection["issues"], [])

    def test_unreadable_database_records_issue_and_keeps_valid_database(self):
        corrupt_path = self.root / "agent" / "agent.db"
        corrupt_path.parent.mkdir(parents=True, exist_ok=True)
        corrupt_path.write_text("not-a-sqlite-database", encoding="utf-8")
        write_history_db(
            self.root / "profiles" / "mix" / "agent" / "agent.db",
            [(START_MS + 1_000, "anthropic", "acct", "limit1", "label1", 0.5)],
        )
        collection = self.collect_history()
        self.assertEqual(len(collection["samples"]), 1)
        self.assertEqual(collection["samples"][0]["provider"], "anthropic")
        self.assertEqual(len(collection["issues"]), 1)
        self.assertIn("unreadable history", collection["issues"][0])


class UsageHistoryCliTests(TempRootMixin, unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(HISTORY_PATH), *arguments],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def cli_arguments(self, root=None):
        return [
            "--start-ms", str(START_MS),
            "--end-ms", str(END_MS),
            "--root", str(self.root if root is None else root),
        ]

    def test_clean_root_exits_zero_and_emits_json_samples(self):
        write_history_db(
            self.root / "agent" / "agent.db",
            [(START_MS + 1_000, "openai-codex", "acct", "limit1", "label1", 0.25)],
        )
        result = self.run_cli(*self.cli_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"start_ms", "end_ms", "samples", "issues"})
        self.assertEqual(len(payload["samples"]), 1)
        self.assertEqual(payload["issues"], [])

    def test_corrupt_database_exits_two_with_issue(self):
        corrupt = self.root / "agent" / "agent.db"
        corrupt.parent.mkdir(parents=True, exist_ok=True)
        corrupt.write_text("corrupt-data", encoding="utf-8")
        result = self.run_cli(*self.cli_arguments())
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["samples"], [])
        self.assertTrue(payload["issues"])
        self.assertIn("unreadable history", payload["issues"][0])

    def test_invalid_range_exits_two_with_stderr(self):
        result = self.run_cli("--start-ms", "5", "--end-ms", "5", "--root", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stderr.strip(), "")

class MergeUsageTests(unittest.TestCase):
    def test_snapshot_schema_and_baseline_providers_on_empty_sources(self):
        snapshot = merge_collections(
            [("WSL", merge_collection([])), ("mini-1", merge_collection([]))]
        )
        self.assertEqual(set(snapshot), {"start_ms", "end_ms", "providers", "days", "sources_ok", "issues"})
        self.assertEqual(snapshot["start_ms"], START_MS)
        self.assertEqual(snapshot["end_ms"], END_MS)
        self.assertEqual([total["provider"] for total in snapshot["providers"]], BASELINE_PROVIDERS)
        for total in snapshot["providers"]:
            self.assertEqual(
                set(total),
                {"provider", "tokens", "estimated_usd", "unpriced_records", "unpriced_tokens", "unpriced_estimated_usd"},
            )
            self.assertEqual(total["tokens"], 0)
            self.assertEqual(total["estimated_usd"], 0.0)
            self.assertEqual(total["unpriced_records"], 0)
            self.assertEqual(total["unpriced_tokens"], 0)
            self.assertEqual(total["unpriced_estimated_usd"], 0.0)
        self.assertEqual(len(snapshot["days"]), 7)
        for index, day in enumerate(snapshot["days"]):
            self.assertEqual(set(day), {"start_ms", "end_ms", "providers", "tokens", "estimated_usd", "unpriced_records"})
            self.assertEqual(day["start_ms"], START_MS + index * token_usage.DAY_MS)
            self.assertEqual(day["end_ms"], START_MS + (index + 1) * token_usage.DAY_MS)
            self.assertEqual([total["provider"] for total in day["providers"]], BASELINE_PROVIDERS)
            for total in day["providers"]:
                self.assertEqual(
                    set(total),
                    {"provider", "tokens", "estimated_usd", "unpriced_records", "unpriced_tokens", "unpriced_estimated_usd"},
                )
                self.assertEqual(total["tokens"], 0)
                self.assertEqual(total["estimated_usd"], 0.0)
                self.assertEqual(total["unpriced_records"], 0)
                self.assertEqual(total["unpriced_tokens"], 0)
                self.assertEqual(total["unpriced_estimated_usd"], 0.0)
            self.assertEqual(day["tokens"], 0)
            self.assertEqual(day["estimated_usd"], 0.0)
            self.assertEqual(day["unpriced_records"], 0)
        self.assertEqual(sorted(snapshot["sources_ok"]), ["WSL", "mini-1"])
        self.assertEqual(snapshot["issues"], [])

    def test_extra_providers_appended_sorted_after_baseline(self):
        records = [
            merge_record("r1", provider="mistral"),
            merge_record("r2", provider="azure-openai"),
        ]
        snapshot = merge_collections([("WSL", merge_collection(records))])
        self.assertEqual(
            [total["provider"] for total in snapshot["providers"]],
            BASELINE_PROVIDERS + ["azure-openai", "mistral"],
        )
        self.assertEqual(
            [total["provider"] for total in snapshot["days"][0]["providers"]],
            BASELINE_PROVIDERS + ["azure-openai", "mistral"],
        )
        self.assertEqual(day_provider_total(snapshot["days"][0], "mistral")["tokens"], 100)
        self.assertEqual(day_provider_total(snapshot["days"][0], "azure-openai")["tokens"], 100)

    def test_fork_duplicate_with_reset_price_counts_once_with_positive_price(self):
        local = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.25)])
        remote = merge_collection([merge_record("r1", tokens=100, estimated_usd=None)])
        snapshot = merge_collections([("WSL", local), ("mini-1", remote)])
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(snapshot["issues"], [])
        self.assertEqual(total["tokens"], 100)
        self.assertEqual(total["estimated_usd"], 0.25)
        self.assertEqual(total["unpriced_records"], 0)

    def test_duplicate_plus_distinct_call_sums_tokens_and_costs(self):
        local = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.25)])
        remote = merge_collection(
            [
                merge_record("r1", tokens=100, estimated_usd=None),
                merge_record("r2", tokens=50, estimated_usd=0.10),
            ]
        )
        snapshot = merge_collections([("WSL", local), ("mini-1", remote)])
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(total["tokens"], 150)
        self.assertAlmostEqual(total["estimated_usd"], 0.35, places=9)
        self.assertEqual(total["unpriced_records"], 0)

    def test_explicit_zero_price_duplicate_also_keeps_positive_price(self):
        local = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.25)])
        remote = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.0)])
        snapshot = merge_collections([("WSL", local), ("mini-1", remote)])
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(snapshot["issues"], [])
        self.assertEqual(total["tokens"], 100)
        self.assertEqual(total["estimated_usd"], 0.25)
        self.assertEqual(total["unpriced_records"], 0)

    def test_conflicting_token_duplicates_are_excluded_with_issue(self):
        local = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.25)])
        remote = merge_collection([merge_record("r1", tokens=200, estimated_usd=0.25)])
        snapshot = merge_collections([("WSL", local), ("mini-1", remote)])
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(total["tokens"], 0)
        self.assertTrue(snapshot["issues"])
        self.assertEqual(sorted(snapshot["sources_ok"]), ["WSL", "mini-1"])

    def test_conflicting_positive_prices_are_excluded_with_issue(self):
        local = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.25)])
        remote = merge_collection([merge_record("r1", tokens=100, estimated_usd=0.30)])
        snapshot = merge_collections([("WSL", local), ("mini-1", remote)])
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(total["tokens"], 0)
        self.assertEqual(total["estimated_usd"], 0.0)
        self.assertTrue(snapshot["issues"])

    def test_zero_token_zero_cost_record_is_not_unpriced(self):
        records = [merge_record("r0", tokens=0, estimated_usd=0.0)]
        snapshot = merge_collections([("WSL", merge_collection(records))])
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(snapshot["issues"], [])
        self.assertEqual(total["tokens"], 0)
        self.assertEqual(total["estimated_usd"], 0.0)
        self.assertEqual(total["unpriced_records"], 0)

    def test_antigravity_cli_maps_into_google_antigravity_after_dedup(self):
        records = [
            merge_record(
                "agy-1",
                provider="antigravity-cli",
                model="gemini-3-pro",
                api="antigravity-cli",
                tokens=313_888,
                estimated_usd=None,
            ),
            merge_record("ga-1", provider="google-antigravity", tokens=10, estimated_usd=0.25),
        ]
        snapshot = merge_collections([("WSL", merge_collection(records))])
        total = provider_total(snapshot, "google-antigravity")
        self.assertEqual(total["tokens"], 313_898)
        self.assertEqual(total["estimated_usd"], 0.25)
        self.assertEqual(total["unpriced_records"], 1)
        self.assertIsNone(provider_total(snapshot, "antigravity-cli"))

    def test_source_collection_issues_propagate_into_snapshot(self):
        local = merge_collection(
            [merge_record("r1", tokens=100, estimated_usd=0.25)],
            issues=["proj/live.jsonl: 1 incomplete trailing line"],
        )
        snapshot = merge_collections([("WSL", local), ("mini-1", merge_collection([]))])
        self.assertIn("WSL: proj/live.jsonl: 1 incomplete trailing line", snapshot["issues"])
        self.assertEqual(provider_total(snapshot, "openai-codex")["tokens"], 100)

    def test_malformed_collection_is_failed_source_not_empty_usage(self):
        broken = {"start_ms": START_MS, "end_ms": END_MS, "records": None, "issues": []}
        snapshot = merge_collections(
            [("WSL", merge_collection([merge_record()])), ("mini-1", broken)]
        )
        self.assertEqual(sorted(snapshot["sources_ok"]), ["WSL"])
        self.assertTrue(snapshot["issues"])
        self.assertEqual(provider_total(snapshot, "openai-codex")["tokens"], 100)

    def test_window_mismatch_is_failed_source(self):
        skewed = merge_collection([merge_record("r9", tokens=500, estimated_usd=None)])
        skewed["end_ms"] = END_MS + 1
        snapshot = merge_collections(
            [("WSL", merge_collection([merge_record()])), ("mini-1", skewed)]
        )
        self.assertEqual(sorted(snapshot["sources_ok"]), ["WSL"])
        self.assertTrue(snapshot["issues"])
        self.assertEqual(provider_total(snapshot, "openai-codex")["tokens"], 100)

    def test_known_costs_are_summed_exactly(self):
        records = [
            merge_record(f"r{index}", tokens=1, estimated_usd=0.1) for index in range(10)
        ]
        snapshot = merge_collections([("WSL", merge_collection(records))])
        self.assertEqual(provider_total(snapshot, "openai-codex")["estimated_usd"], 1.0)

    def test_records_in_two_day_bins_split_daily_and_aggregate_totals(self):
        day_ms = token_usage.DAY_MS
        records = [
            merge_record("day0-priced", timestamp_ms=START_MS + 1_000, tokens=100, estimated_usd=0.25),
            merge_record("day0-unpriced", timestamp_ms=START_MS + 2_000, tokens=40, estimated_usd=None),
            merge_record(
                "day3-priced",
                timestamp_ms=START_MS + 3 * day_ms + 1_000,
                provider="anthropic",
                model="claude-opus",
                api="anthropic-messages",
                tokens=70,
                estimated_usd=0.10,
            ),
            merge_record(
                "day3-unpriced",
                timestamp_ms=START_MS + 3 * day_ms + 2_000,
                provider="anthropic",
                model="claude-opus",
                api="anthropic-messages",
                tokens=30,
                estimated_usd=None,
            ),
        ]
        snapshot = merge_collections([("WSL", merge_collection(records))])
        self.assertEqual(len(snapshot["days"]), 7)
        first = day_total(snapshot, 0)
        fourth = day_total(snapshot, 3)
        self.assertEqual(day_provider_total(first, "openai-codex")["tokens"], 140)
        self.assertAlmostEqual(day_provider_total(first, "openai-codex")["estimated_usd"], 0.25, places=9)
        self.assertEqual(day_provider_total(first, "openai-codex")["unpriced_records"], 1)
        self.assertEqual(first["tokens"], 140)
        self.assertAlmostEqual(first["estimated_usd"], 0.25, places=9)
        self.assertEqual(first["unpriced_records"], 1)
        self.assertEqual(day_provider_total(fourth, "anthropic")["tokens"], 100)
        self.assertAlmostEqual(day_provider_total(fourth, "anthropic")["estimated_usd"], 0.10, places=9)
        self.assertEqual(day_provider_total(fourth, "anthropic")["unpriced_records"], 1)
        self.assertEqual(fourth["tokens"], 100)
        self.assertAlmostEqual(fourth["estimated_usd"], 0.10, places=9)
        self.assertEqual(fourth["unpriced_records"], 1)
        for index in (1, 2, 4, 5, 6):
            self.assertEqual(day_total(snapshot, index)["tokens"], 0)
            self.assertEqual(day_total(snapshot, index)["unpriced_records"], 0)
        self.assertEqual(provider_total(snapshot, "openai-codex")["tokens"], 140)
        self.assertAlmostEqual(provider_total(snapshot, "openai-codex")["estimated_usd"], 0.25, places=9)
        self.assertEqual(provider_total(snapshot, "openai-codex")["unpriced_records"], 1)
        self.assertEqual(provider_total(snapshot, "anthropic")["tokens"], 100)
        self.assertAlmostEqual(provider_total(snapshot, "anthropic")["estimated_usd"], 0.10, places=9)
        self.assertEqual(provider_total(snapshot, "anthropic")["unpriced_records"], 1)


    def test_unpriced_tokens_carry_estimated_cost_for_known_models(self):
        day_ms = token_usage.DAY_MS
        records = [
            merge_record(
                "est-glm",
                provider="opencode-go",
                model="glm-5.3",
                api="opencode",
                tokens=1_000_000,
                estimated_usd=None,
            ),
            merge_record(
                "est-agy",
                timestamp_ms=START_MS + day_ms,
                provider="antigravity-cli",
                model="gemini-3.8-flash",
                api="antigravity-cli",
                tokens=2_000_000,
                estimated_usd=None,
            ),
            merge_record(
                "est-unknown",
                timestamp_ms=START_MS + 2 * day_ms,
                provider="zai",
                model="glm-x",
                api="openai-completions",
                tokens=500_000,
                estimated_usd=None,
            ),
        ]
        snapshot = merge_collections([("WSL", merge_collection(records))])
        go = provider_total(snapshot, "opencode-go")
        self.assertEqual(go["unpriced_tokens"], 1_000_000)
        self.assertAlmostEqual(go["unpriced_estimated_usd"], 0.315, places=9)
        ga = provider_total(snapshot, "google-antigravity")
        self.assertEqual(ga["unpriced_tokens"], 2_000_000)
        self.assertAlmostEqual(ga["unpriced_estimated_usd"], 0.2484, places=9)
        zai = provider_total(snapshot, "zai")
        self.assertEqual(zai["unpriced_tokens"], 500_000)
        self.assertEqual(zai["unpriced_estimated_usd"], 0.0)
        day_go = day_provider_total(day_total(snapshot, 0), "opencode-go")
        self.assertEqual(day_go["unpriced_tokens"], 1_000_000)
        self.assertAlmostEqual(day_go["unpriced_estimated_usd"], 0.315, places=9)
        day_ga = day_provider_total(day_total(snapshot, 1), "google-antigravity")
        self.assertEqual(day_ga["unpriced_tokens"], 2_000_000)
        self.assertAlmostEqual(day_ga["unpriced_estimated_usd"], 0.2484, places=9)

def history_sample(
    recorded_at_ms=None,
    provider="openai-codex",
    account_key="acct",
    limit_id="openai-codex:primary",
    used_fraction=0.5,
):
    return {
        "recorded_at_ms": HISTORY_START_MS + 1_000 if recorded_at_ms is None else recorded_at_ms,
        "provider": provider,
        "account_key": account_key,
        "limit_id": limit_id,
        "used_fraction": used_fraction,
    }


def history_collection(samples, issues=None):
    return {
        "start_ms": HISTORY_START_MS,
        "end_ms": HISTORY_END_MS,
        "samples": samples,
        "issues": issues or [],
    }


class MergeHistoryTests(unittest.TestCase):
    def test_identical_sample_across_sources_collapses_to_one(self):
        sample = history_sample(recorded_at_ms=HISTORY_START_MS + 1_000)
        local = history_collection([sample])
        remote = history_collection([dict(sample)])
        snapshot = usage_history.merge_history(
            [("WSL", local), ("mini-1", remote)], HISTORY_START_MS, HISTORY_END_MS
        )
        self.assertEqual(snapshot["samples"], [sample])
        self.assertEqual(snapshot["sources_ok"], ["WSL", "mini-1"])
        self.assertEqual(snapshot["issues"], [])

    def test_distinct_account_keys_both_survive(self):
        sample_wsl = history_sample(account_key="acct-wsl")
        sample_mini = history_sample(account_key="acct-mini")
        snapshot = usage_history.merge_history(
            [("WSL", history_collection([sample_wsl])), ("mini-1", history_collection([sample_mini]))],
            HISTORY_START_MS,
            HISTORY_END_MS,
        )
        self.assertEqual(len(snapshot["samples"]), 2)
        self.assertEqual({s["account_key"] for s in snapshot["samples"]}, {"acct-wsl", "acct-mini"})

    def test_start_ms_mismatch_yields_invalid_collection_issue_and_excludes_source(self):
        skewed = history_collection([history_sample()])
        skewed["start_ms"] = HISTORY_START_MS + 1
        snapshot = usage_history.merge_history(
            [("WSL", history_collection([history_sample()])), ("mini-1", skewed)],
            HISTORY_START_MS,
            HISTORY_END_MS,
        )
        self.assertEqual(snapshot["sources_ok"], ["WSL"])
        self.assertIn("mini-1: invalid collection", snapshot["issues"])

    def test_sample_with_fraction_above_one_rejects_collection_wholesale(self):
        bad = history_collection([history_sample(used_fraction=1.5)])
        valid = history_collection([history_sample(used_fraction=0.5)])
        snapshot = usage_history.merge_history(
            [("WSL", valid), ("mini-1", bad)],
            HISTORY_START_MS,
            HISTORY_END_MS,
        )
        self.assertEqual(snapshot["sources_ok"], ["WSL"])
        self.assertIn("mini-1: invalid collection", snapshot["issues"])
        self.assertEqual(len(snapshot["samples"]), 1)

    def test_source_issues_are_prefixed_with_label(self):
        local = history_collection([history_sample()], issues=["agent.db: skipped 1 invalid rows"])
        snapshot = usage_history.merge_history(
            [("WSL", local)],
            HISTORY_START_MS,
            HISTORY_END_MS,
        )
        self.assertIn("WSL: agent.db: skipped 1 invalid rows", snapshot["issues"])

    def test_sources_ok_preserves_input_order(self):
        c1 = history_collection([])
        c2 = history_collection([])
        snapshot = usage_history.merge_history(
            [("mini-1", c1), ("WSL", c2)],
            HISTORY_START_MS,
            HISTORY_END_MS,
        )
        self.assertEqual(snapshot["sources_ok"], ["mini-1", "WSL"])

    def test_output_samples_are_sorted(self):
        s1 = history_sample(provider="zai", recorded_at_ms=HISTORY_START_MS + 2_000)
        s2 = history_sample(provider="anthropic", recorded_at_ms=HISTORY_START_MS + 1_000)
        snapshot = usage_history.merge_history(
            [("WSL", history_collection([s1, s2]))],
            HISTORY_START_MS,
            HISTORY_END_MS,
        )
        self.assertEqual(
            [s["provider"] for s in snapshot["samples"]],
            ["anthropic", "zai"],
        )


class RelayDirMixin(TempRootMixin):
    def setUp(self):
        super().setUp()
        self.relay_dir = self.root / "relay"
        relay_patcher = mock.patch.dict(
            os.environ, {reporter.RELAY_DIR_ENV: str(self.relay_dir), reporter.RELAY_SOURCES_ENV: ""}
        )
        relay_patcher.start()
        self.addCleanup(relay_patcher.stop)

    def write_relay_bytes(self, name, data):
        self.relay_dir.mkdir(parents=True, exist_ok=True)
        path = self.relay_dir / f"{name}{reporter.RELAY_SUFFIX}"
        path.write_bytes(data)
        return path

    def write_relay_file(self, name, text):
        return self.write_relay_bytes(name, gzip.compress(text.encode("utf-8")))

    def write_bundle(self, name, bundle):
        return self.write_relay_file(name, json.dumps(bundle))


class CollectTokenSnapshotWindowTests(RelayDirMixin):
    def test_collects_thirty_utc_dates_with_partial_today(self):
        now_ms = int(datetime(2026, 9, 14, 15, 20, tzinfo=timezone.utc).timestamp() * 1000)
        start_ms = int(datetime(2026, 8, 16, tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(start_ms % token_usage.DAY_MS, 0)
        first_record = merge_record("window-start", timestamp_ms=start_ms, tokens=100, estimated_usd=0.25)
        last_record = merge_record("partial-today", timestamp_ms=now_ms - 1_000, tokens=40, estimated_usd=None)
        requested_windows = []

        def local_collection(requested_start, requested_end):
            requested_windows.append(("WSL", requested_start, requested_end))
            return "WSL", {"start_ms": requested_start, "end_ms": requested_end, "records": [dict(first_record)], "issues": []}, []

        def remote_collection(host, source, requested_start, requested_end):
            requested_windows.append(("mini-1", requested_start, requested_end))
            return "mini-1", {"start_ms": requested_start, "end_ms": requested_end, "records": [dict(last_record)], "issues": []}, []

        with mock.patch.object(reporter, "local_token_collection", side_effect=local_collection), mock.patch.object(
            reporter, "check_ssh_host", return_value="mini-1"
        ), mock.patch.object(
            reporter, "collector_source", return_value=b"collector-source"
        ), mock.patch.object(
            reporter, "remote_collection", side_effect=remote_collection
        ):
            snapshot = reporter.collect_token_snapshot(now_ms)

        self.assertEqual(sorted(requested_windows), sorted([("WSL", start_ms, now_ms), ("mini-1", start_ms, now_ms)]))
        self.assertEqual(snapshot["start_ms"], start_ms)
        self.assertEqual(snapshot["end_ms"], now_ms)
        self.assertEqual(len(snapshot["days"]), 30)
        first_day, last_day = snapshot["days"][0], snapshot["days"][-1]
        self.assertEqual(
            datetime.fromtimestamp(first_day["start_ms"] / 1000, tz=timezone.utc),
            datetime(2026, 8, 16, tzinfo=timezone.utc),
        )
        self.assertEqual(
            datetime.fromtimestamp(last_day["start_ms"] / 1000, tz=timezone.utc),
            datetime(2026, 9, 14, tzinfo=timezone.utc),
        )
        self.assertEqual(last_day["end_ms"], now_ms)
        self.assertEqual(first_day["tokens"], 100)
        self.assertEqual(last_day["tokens"], 40)
        self.assertEqual([day["tokens"] for day in snapshot["days"][1:-1]], [0] * 28)
        total = provider_total(snapshot, "openai-codex")
        self.assertEqual(total["tokens"], 140)
        self.assertAlmostEqual(total["estimated_usd"], 0.25, places=9)
        self.assertEqual(total["unpriced_records"], 1)
        self.assertEqual(sorted(snapshot["sources_ok"]), ["WSL", "mini-1"])
        self.assertEqual(snapshot["issues"], [])

class CollectHistorySnapshotTests(RelayDirMixin):
    def test_history_window_covers_seven_days_ending_now(self):
        now_ms = 1_789_000_000_000
        start_ms = now_ms - 7 * DAY_MS
        requested_windows = []
        wsl_sample = history_sample(recorded_at_ms=start_ms + 1_000, used_fraction=0.1)
        mini_sample = history_sample(
            recorded_at_ms=start_ms + 2_000,
            provider="zai",
            limit_id="zai:tokens:5h",
            used_fraction=0.2,
        )

        def local_history(requested_start, requested_end):
            requested_windows.append(("WSL", requested_start, requested_end))
            collection = {
                "start_ms": requested_start,
                "end_ms": requested_end,
                "samples": [dict(wsl_sample)],
                "issues": [],
            }
            return "WSL", collection, []

        def remote_history(host, source, requested_start, requested_end):
            requested_windows.append(("mini-1", requested_start, requested_end))
            collection = {
                "start_ms": requested_start,
                "end_ms": requested_end,
                "samples": [dict(mini_sample)],
                "issues": [],
            }
            return "mini-1", collection, []

        with mock.patch.object(reporter, "local_history_collection", side_effect=local_history), mock.patch.object(
            reporter, "check_ssh_host", return_value="mini-1"
        ), mock.patch.object(
            reporter, "collector_source", return_value=b"collector-source"
        ), mock.patch.object(
            reporter, "remote_collection", side_effect=remote_history
        ):
            snapshot = reporter.collect_history_snapshot(now_ms)

        self.assertEqual(sorted(requested_windows), sorted([("WSL", start_ms, now_ms), ("mini-1", start_ms, now_ms)]))
        self.assertEqual(snapshot["start_ms"], start_ms)
        self.assertEqual(snapshot["end_ms"], now_ms)
        self.assertEqual(sorted(snapshot["sources_ok"]), ["WSL", "mini-1"])
        self.assertEqual(snapshot["samples"], [wsl_sample, mini_sample])
        self.assertEqual(snapshot["issues"], [])

    def test_unconfigured_ssh_host_keeps_local_samples_without_issue(self):
        now_ms = 1_789_000_000_000
        start_ms = now_ms - 7 * DAY_MS
        wsl_sample = history_sample(recorded_at_ms=start_ms + 1_000, used_fraction=0.1)

        def local_history(requested_start, requested_end):
            collection = {
                "start_ms": requested_start,
                "end_ms": requested_end,
                "samples": [dict(wsl_sample)],
                "issues": [],
            }
            return "WSL", collection, []

        with mock.patch.object(reporter, "local_history_collection", side_effect=local_history), mock.patch.object(
            reporter, "check_ssh_host", return_value=None
        ), mock.patch.object(reporter, "collector_source") as collector, mock.patch.object(
            reporter, "remote_collection"
        ) as remote:
            snapshot = reporter.collect_history_snapshot(now_ms)

        collector.assert_not_called()
        remote.assert_not_called()
        self.assertEqual(snapshot["issues"], [])
        self.assertEqual(snapshot["sources_ok"], ["WSL"])
        self.assertEqual(snapshot["samples"], [wsl_sample])

    def test_gather_issues_precede_merge_issues(self):
        now_ms = 1_789_000_000_000
        start_ms = now_ms - 7 * DAY_MS
        wsl_sample = history_sample(recorded_at_ms=start_ms + 1_000, used_fraction=0.1)

        def local_history(requested_start, requested_end):
            collection = {
                "start_ms": requested_start,
                "end_ms": requested_end,
                "samples": [dict(wsl_sample)],
                "issues": ["agent.db: skipped 1 invalid rows"],
            }
            return "WSL", collection, []

        def remote_history(host, source, requested_start, requested_end):
            return "mini-1", None, ["mini-1 unavailable: ssh timed out"]

        with mock.patch.object(reporter, "local_history_collection", side_effect=local_history), mock.patch.object(
            reporter, "check_ssh_host", return_value="mini-1"
        ), mock.patch.object(
            reporter, "collector_source", return_value=b"collector-source"
        ), mock.patch.object(
            reporter, "remote_collection", side_effect=remote_history
        ):
            snapshot = reporter.collect_history_snapshot(now_ms)

        self.assertEqual(snapshot["sources_ok"], ["WSL"])
        self.assertEqual(
            snapshot["issues"],
            ["mini-1 unavailable: ssh timed out", "WSL: agent.db: skipped 1 invalid rows"],
        )


class GatherCollectionsTests(unittest.TestCase):
    def test_collector_source_failure_reports_unavailable_and_returns_local_collection(self):
        local = history_collection([history_sample()])

        def local_history(requested_start, requested_end):
            return "WSL", local, []

        with mock.patch.object(reporter, "check_ssh_host", return_value="mbn@mini-1.tail.ts.net"), mock.patch.object(
            reporter, "collector_source", side_effect=reporter.UsageError("collector unreadable: x", 1)
        ), mock.patch.object(reporter, "remote_collection") as remote:
            collections, issues = reporter.gather_collections(
                HISTORY_PATH, local_history, HISTORY_START_MS, HISTORY_END_MS
            )

        remote.assert_not_called()
        self.assertEqual(collections, [("WSL", local)])
        self.assertEqual(issues, ["mini-1 unavailable: collector unreadable"])


def relay_section(collections=None, issues=None):
    return {"start_ms": 0, "end_ms": 1, "collections": collections or [], "issues": issues or []}


def relay_bundle(source="WSL", generated_at_ms=FIXED_NOW_MS, tokens=None, history=None):
    return {
        "schema": 1,
        "source": source,
        "generated_at_ms": generated_at_ms,
        "tokens": tokens or relay_section(),
        "history": history or relay_section(),
    }


class SourceLabelTests(unittest.TestCase):
    def test_override_is_stripped_and_used(self):
        with mock.patch.dict(os.environ, {reporter.SOURCE_LABEL_ENV: " WSL "}):
            self.assertEqual(reporter.local_source_label(), "WSL")

    def test_invalid_override_is_an_error_not_a_hostname_fallback(self):
        with mock.patch.dict(os.environ, {reporter.SOURCE_LABEL_ENV: "bad label!"}), \
                self.assertRaises(reporter.UsageError) as raised:
            reporter.local_source_label()
        self.assertEqual(raised.exception.exit_code, 1)

    def test_hostname_first_label_is_used_without_override(self):
        with mock.patch.dict(os.environ), mock.patch.object(
            reporter.socket, "gethostname", return_value="prei-box.tail.ts.net"
        ):
            os.environ.pop(reporter.SOURCE_LABEL_ENV, None)
            self.assertEqual(reporter.local_source_label(), "prei-box")

    def test_unsafe_hostname_is_an_error(self):
        with mock.patch.dict(os.environ), mock.patch.object(reporter.socket, "gethostname", return_value="a;b"):
            os.environ.pop(reporter.SOURCE_LABEL_ENV, None)
            with self.assertRaises(reporter.UsageError):
                reporter.local_source_label()

    def test_remote_label_drops_user_and_domain(self):
        self.assertEqual(reporter.remote_label("mbn@mini-1.tail.ts.net"), "mini-1")


class RelayCollectionsTests(RelayDirMixin):
    def test_missing_relay_directory_yields_nothing_when_no_source_is_expected(self):
        self.assertEqual(reporter.relay_collections("tokens", 0, 1, FIXED_NOW_MS), ([], []))

    def test_expected_source_without_a_bundle_is_reported_missing(self):
        with mock.patch.dict(os.environ, {reporter.RELAY_SOURCES_ENV: "WSL, mini-1"}):
            collections, issues = reporter.relay_collections("tokens", 0, 1, FIXED_NOW_MS)
        self.assertEqual(collections, [])
        self.assertEqual(issues, ["WSL relay missing", "mini-1 relay missing"])

    def test_present_expected_source_is_not_reported_missing(self):
        self.write_bundle("WSL", relay_bundle())
        with mock.patch.dict(os.environ, {reporter.RELAY_SOURCES_ENV: "WSL"}):
            _, issues = reporter.relay_collections("tokens", 0, 1, FIXED_NOW_MS)
        self.assertEqual(issues, [])

    def test_future_dated_bundle_reports_clock_skew(self):
        self.write_bundle("WSL", relay_bundle(generated_at_ms=FIXED_NOW_MS + 3 * HOUR_MS))
        _, issues = reporter.relay_collections("tokens", 0, 1, FIXED_NOW_MS)
        self.assertEqual(issues, ["WSL relay clock 3h ahead"])

    def test_malformed_timestamps_reach_the_merge_validator(self):
        record = {**merge_record("bad", timestamp_ms=FIXED_NOW_MS - HOUR_MS), "timestamp_ms": "5"}
        collection = {"start_ms": 0, "end_ms": 1, "records": [record], "issues": []}
        self.write_bundle("WSL", relay_bundle(tokens=relay_section([{"source": "WSL", "collection": collection}])))
        collections, _ = reporter.relay_collections("tokens", 0, FIXED_NOW_MS, FIXED_NOW_MS)
        self.assertEqual(collections[0][1]["records"], [record])

    def test_token_records_are_kept_only_inside_reader_window(self):
        window_start = FIXED_NOW_MS - 7 * DAY_MS
        inside = merge_record("inside", timestamp_ms=window_start)
        last_inside = merge_record("last-inside", timestamp_ms=FIXED_NOW_MS - 1)
        collection = {
            "start_ms": 0,
            "end_ms": 1,
            "records": [
                merge_record("before", timestamp_ms=window_start - 1),
                inside,
                last_inside,
                merge_record("at-end", timestamp_ms=FIXED_NOW_MS),
            ],
            "issues": [],
        }
        self.write_bundle("WSL", relay_bundle(tokens=relay_section([{"source": "WSL", "collection": collection}])))

        collections, issues = reporter.relay_collections("tokens", window_start, FIXED_NOW_MS, FIXED_NOW_MS)

        self.assertEqual(issues, [])
        self.assertEqual(
            collections,
            [("WSL", {"start_ms": window_start, "end_ms": FIXED_NOW_MS, "records": [inside, last_inside], "issues": []})],
        )

    def test_history_samples_are_kept_only_inside_reader_window(self):
        window_start = FIXED_NOW_MS - 7 * DAY_MS
        inside = history_sample(recorded_at_ms=window_start)
        collection = {
            "start_ms": 0,
            "end_ms": 1,
            "samples": [
                history_sample(recorded_at_ms=window_start - 1),
                inside,
                history_sample(recorded_at_ms=FIXED_NOW_MS),
            ],
            "issues": [],
        }
        self.write_bundle("WSL", relay_bundle(history=relay_section([{"source": "WSL", "collection": collection}])))

        collections, issues = reporter.relay_collections("history", window_start, FIXED_NOW_MS, FIXED_NOW_MS)

        self.assertEqual(issues, [])
        self.assertEqual(
            collections,
            [("WSL", {"start_ms": window_start, "end_ms": FIXED_NOW_MS, "samples": [inside], "issues": []})],
        )

    def test_stale_bundle_reports_age_and_keeps_its_data(self):
        window_start = FIXED_NOW_MS - 7 * DAY_MS
        generated_at_ms = FIXED_NOW_MS - (reporter.RELAY_STALE_MS + 60_000)
        collection = {"start_ms": 0, "end_ms": 1, "records": [], "issues": []}
        self.write_bundle(
            "WSL",
            relay_bundle(
                generated_at_ms=generated_at_ms,
                tokens=relay_section([{"source": "WSL", "collection": collection}], ["mini-1 unavailable: ssh timed out"]),
            ),
        )

        collections, issues = reporter.relay_collections("tokens", window_start, FIXED_NOW_MS, FIXED_NOW_MS)

        self.assertEqual(issues, ["WSL relay 16m old", "mini-1 unavailable: ssh timed out"])
        self.assertEqual(
            collections,
            [("WSL", {"start_ms": window_start, "end_ms": FIXED_NOW_MS, "records": [], "issues": []})],
        )

    def test_unreadable_bundles_are_reported_and_skipped(self):
        self.write_relay_file("broken", "{not json")
        self.write_bundle("wrong-schema", {**relay_bundle(), "schema": 2})
        self.write_relay_bytes("truncated", gzip.compress(json.dumps(relay_bundle()).encode("utf-8"))[:40])
        self.write_relay_file("nested", "[" * 200_000)

        collections, issues = reporter.relay_collections("tokens", 0, 1, FIXED_NOW_MS)

        self.assertEqual(collections, [])
        self.assertEqual(
            issues,
            ["broken relay unreadable", "nested relay unreadable", "truncated relay unreadable", "wrong-schema relay unreadable"],
        )


class RelayRoundTripTests(RelayDirMixin):
    def test_wsl_bundle_merges_into_openclaw_snapshots(self):
        now_ms = int(datetime(2026, 9, 14, 15, 20, tzinfo=timezone.utc).timestamp() * 1000)
        wsl_token = merge_record("wsl-token", timestamp_ms=now_ms - 3_000, tokens=10, estimated_usd=0.1)
        mini_token = merge_record("mini-token", timestamp_ms=now_ms - 2_000, tokens=20, estimated_usd=0.2)
        openclaw_token = merge_record("openclaw-token", timestamp_ms=now_ms - 1_000, tokens=30, estimated_usd=0.3)
        wsl_sample = history_sample(recorded_at_ms=now_ms - 3_000, used_fraction=0.1)
        openclaw_sample = history_sample(recorded_at_ms=now_ms - 1_000, used_fraction=0.2)

        def wsl_gather(source_path, local, start_ms, end_ms):
            if source_path == reporter.TOKEN_USAGE_PATH:
                return [
                    ("WSL", {"start_ms": start_ms, "end_ms": end_ms, "records": [wsl_token], "issues": []}),
                    ("mini-1", {"start_ms": start_ms, "end_ms": end_ms, "records": [mini_token], "issues": []}),
                ], []
            return [("WSL", {"start_ms": start_ms, "end_ms": end_ms, "samples": [wsl_sample], "issues": []})], []

        with mock.patch.dict(os.environ, {reporter.SOURCE_LABEL_ENV: "WSL"}), mock.patch.object(
            reporter, "gather_collections", side_effect=wsl_gather
        ):
            bundle = reporter.build_relay_bundle(now_ms)
        self.write_bundle("WSL", bundle)

        def openclaw_gather(source_path, local, start_ms, end_ms):
            if source_path == reporter.TOKEN_USAGE_PATH:
                return [("openclaw", {"start_ms": start_ms, "end_ms": end_ms, "records": [openclaw_token], "issues": []})], []
            return [("openclaw", {"start_ms": start_ms, "end_ms": end_ms, "samples": [openclaw_sample], "issues": []})], []

        with mock.patch.dict(os.environ, {reporter.SOURCE_LABEL_ENV: "openclaw"}), mock.patch.object(
            reporter, "gather_collections", side_effect=openclaw_gather
        ):
            tokens = reporter.collect_token_snapshot(now_ms)
            history = reporter.collect_history_snapshot(now_ms)

        self.assertEqual(sorted(tokens["sources_ok"]), ["WSL", "mini-1", "openclaw"])
        self.assertEqual(tokens["issues"], [])
        total = provider_total(tokens, "openai-codex")
        self.assertEqual(total["tokens"], 60)
        self.assertAlmostEqual(total["estimated_usd"], 0.6, places=9)
        self.assertEqual(sorted(history["sources_ok"]), ["WSL", "openclaw"])
        self.assertEqual(history["issues"], [])
        self.assertEqual(
            sorted(sample["recorded_at_ms"] for sample in history["samples"]),
            [now_ms - 3_000, now_ms - 1_000],
        )


class TelegramStateMixin(TempRootMixin):
    def setUp(self):
        super().setUp()
        self.state_path = self.root / "state" / "state.json"
        state_patcher = mock.patch.object(reporter, "CODEX_STATE_PATH", self.state_path)
        state_patcher.start()
        self.addCleanup(state_patcher.stop)
        self.config = {"bot_token": "unit-test-token", "chat_id": "42"}

    def write_state(self, state):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self):
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def telegram_error(self, description, code=400):
        body = json.dumps({"ok": False, "error_code": code, "description": description})
        return urllib.error.HTTPError(
            "https://api.telegram.org/bot-unit-test/method",
            code,
            description,
            {"Content-Type": "application/json"},
            io.BytesIO(body.encode("utf-8")),
        )


class BuildDashboardTests(unittest.TestCase):
    NOW_MS = FIXED_NOW_MS

    def report(self, provider, limits, plan=None):
        entry = {"provider": provider, "limits": limits}
        if plan is not None:
            entry["metadata"] = {"planType": plan}
        return entry

    def sample(self, recorded_at_ms, used_fraction, provider="openai-codex", limit_id="openai-codex:primary"):
        return {
            "recorded_at_ms": recorded_at_ms,
            "provider": provider,
            "account_key": "acct",
            "limit_id": limit_id,
            "used_fraction": used_fraction,
        }

    def test_groups_windows_by_provider_and_account_in_report_order(self):
        payload = {
            "generatedAt": self.NOW_MS - 60_000,
            "reports": [
                self.report(
                    "openai-codex",
                    [window_limit(limit_id="openai-codex:primary", label="7 days", resets_at_ms=self.NOW_MS + 5 * HOUR_MS, used_fraction=0.24)],
                    plan="Pro",
                ),
                self.report(
                    "openai-codex",
                    [window_limit(limit_id="weekly", label="Weekly limit", resets_at_ms=self.NOW_MS + 6 * DAY_MS, used_fraction=0.9)],
                    plan="Team",
                ),
                self.report(
                    "mistral",
                    [window_limit(limit_id="mistral:primary", label="Monthly", resets_at_ms=self.NOW_MS + 3 * DAY_MS, used_fraction=0.1)],
                ),
            ],
        }
        view = reporter.build_dashboard(payload, empty_token_snapshot(), plain_history_snapshot(), self.NOW_MS)
        providers = [quota.provider for quota in view.quotas]
        self.assertEqual(len([name for name in providers if name == "openai-codex"]), 2)
        self.assertIn("mistral", providers)
        codex = [quota for quota in view.quotas if quota.provider == "openai-codex"]
        self.assertEqual(codex[0].plan, "Pro")
        self.assertEqual(codex[1].plan, "Team")
        window = codex[0].windows[0]
        self.assertEqual(window.label, "7 days")
        self.assertAlmostEqual(window.used_percent, 24.0)
        self.assertEqual(window.reset_ms, self.NOW_MS + 5 * HOUR_MS)
        self.assertEqual(window.status, "ok")
        self.assertIsNotNone(window.pace)

    def test_redacted_same_provider_reports_stay_separate_groups_without_cross_coupling(self):
        now = self.NOW_MS

        def history_for(limit_id, fractions):
            return [
                {
                    "recorded_at_ms": now - (2 - index) * HOUR_MS,
                    "provider": "anthropic",
                    "account_key": "acct",
                    "limit_id": limit_id,
                    "used_fraction": fraction,
                }
                for index, fraction in enumerate(fractions)
            ]

        payload = {
            "generatedAt": now - 60_000,
            "reports": [
                {
                    "provider": "anthropic",
                    "metadata": {"planType": "Pro"},
                    "limits": [
                        forecast_limit(
                            limit_id="anthropic:5h",
                            label="Claude 5 Hour",
                            used_fraction=0.40,
                            resets_at_ms=now + 2 * HOUR_MS,
                            duration_ms=5 * HOUR_MS,
                        ),
                        forecast_limit(
                            limit_id="anthropic:7d",
                            label="Claude 7 Day",
                            used_fraction=0.90,
                            resets_at_ms=now + 6 * DAY_MS,
                            duration_ms=7 * DAY_MS,
                        ),
                    ],
                },
                {
                    "provider": "anthropic",
                    "metadata": {"planType": "Team"},
                    "limits": [
                        forecast_limit(
                            limit_id="anthropic-b:7d",
                            label="Claude 7 Day (B)",
                            used_fraction=0.10,
                            resets_at_ms=now + 5 * DAY_MS,
                            duration_ms=7 * DAY_MS,
                        ),
                        forecast_limit(
                            limit_id="anthropic-b:5h",
                            label="Claude 5 Hour (B)",
                            used_fraction=0.40,
                            resets_at_ms=now + 2 * HOUR_MS,
                            duration_ms=5 * HOUR_MS,
                        ),
                    ],
                },
            ],
        }
        history = plain_history_snapshot(
            samples=(
                history_for("anthropic:5h", (0.00, 0.20, 0.40))
                + history_for("anthropic-b:5h", (0.00, 0.20, 0.40))
                + history_for("anthropic:7d", (0.10, 0.15, 0.20))
                + history_for("anthropic-b:7d", (0.10, 0.15, 0.20))
            )
        )
        view = reporter.build_dashboard(payload, None, history, now)
        groups = [quota for quota in view.quotas if quota.provider == "anthropic"]
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].plan, "Pro")
        self.assertEqual(groups[1].plan, "Team")
        for quota in groups:
            resets = [window.reset_ms for window in quota.windows]
            self.assertEqual(resets, sorted(resets))
        short_verdicts = [
            next(
                window.pace.verdict
                for window in quota.windows
                if window.reset_ms == now + 2 * HOUR_MS
            )
            for quota in groups
        ]
        self.assertEqual(short_verdicts, ["GATED", "ON PACE"])

    def test_windows_within_an_account_are_sorted_by_reset(self):
        payload = usage_payload(
            limits=[
                window_limit(limit_id="late", label="Late", resets_at_ms=self.NOW_MS + 2 * DAY_MS, used_fraction=0.1),
                window_limit(limit_id="early", label="Early", resets_at_ms=self.NOW_MS + DAY_MS, used_fraction=0.2),
            ]
        )
        view = reporter.build_dashboard(payload, None, plain_history_snapshot(), self.NOW_MS)
        self.assertEqual(
            [window.reset_ms for window in view.quotas[0].windows],
            [self.NOW_MS + DAY_MS, self.NOW_MS + 2 * DAY_MS],
        )

    def test_generated_at_becomes_quota_updated_ms(self):
        payload = usage_payload()
        payload["generatedAt"] = self.NOW_MS - 60_000
        view = reporter.build_dashboard(payload, None, None, self.NOW_MS)
        self.assertEqual(view.quota_updated_ms, self.NOW_MS - 60_000)

    def test_window_length_and_hourly_spark_reach_the_view(self):
        payload = usage_payload(
            limits=[forecast_limit(resets_at_ms=self.NOW_MS + 6 * DAY_MS, duration_ms=7 * DAY_MS)]
        )
        history = plain_history_snapshot(samples=[self.sample(self.NOW_MS - 2 * HOUR_MS, 0.10), self.sample(self.NOW_MS - 30 * 60_000, 0.24)])
        window = reporter.build_dashboard(payload, None, history, self.NOW_MS).quotas[0].windows[0]
        self.assertEqual(window.window_ms, 7 * DAY_MS)
        self.assertEqual(len(window.pace.spark), 48)
        self.assertIsNone(window.pace.spark[0])
        self.assertAlmostEqual(window.pace.spark[-1], 0.24)

    def test_missing_payload_marks_quota_issue_without_quotas(self):
        view = reporter.build_dashboard(None, empty_token_snapshot(), plain_history_snapshot(), self.NOW_MS)
        self.assertTrue(view.quota_issue)
        self.assertEqual(view.quotas, [])
        self.assertIsNone(view.quota_updated_ms)
        self.assertIsNotNone(view.tokens)
        self.assertFalse(view.history_partial)

    def test_missing_tokens_and_history_mark_sections_unavailable(self):
        view = reporter.build_dashboard(usage_payload(), None, None, self.NOW_MS)
        self.assertIsNone(view.tokens)
        self.assertEqual(view.history_sources, [])
        self.assertTrue(view.history_partial)

    def test_history_sources_and_partial_flag_follow_snapshot(self):
        payload = usage_payload()
        clean = reporter.build_dashboard(payload, None, plain_history_snapshot(), self.NOW_MS)
        self.assertEqual(clean.history_sources, ["WSL"])
        self.assertFalse(clean.history_partial)
        flagged = reporter.build_dashboard(
            payload, None, plain_history_snapshot(issues=["agent.db: boom"]), self.NOW_MS
        )
        self.assertEqual(flagged.history_sources, ["WSL"])
        self.assertTrue(flagged.history_partial)

    def test_tokens_snapshot_passes_through_unchanged(self):
        snapshot = empty_token_snapshot()
        view = reporter.build_dashboard(usage_payload(), snapshot, None, self.NOW_MS)
        self.assertIs(view.tokens, snapshot)

    def test_windows_without_history_show_no_data_pace(self):
        payload = usage_payload(
            limits=[
                window_limit(limit_id="openai-codex:primary", label="7 days", resets_at_ms=self.NOW_MS + DAY_MS, used_fraction=0.4)
            ]
        )
        view = reporter.build_dashboard(payload, None, plain_history_snapshot(), self.NOW_MS)
        pace = view.quotas[0].windows[0].pace
        self.assertEqual(pace.verdict, "NO DATA")
        self.assertIsNone(pace.projected_percent)

    def test_unknown_used_fraction_is_no_data_window(self):
        payload = usage_payload(
            limits=[
                window_limit(limit_id="openai-codex:primary", label="7 days", resets_at_ms=self.NOW_MS + DAY_MS, used_fraction=None)
            ]
        )
        view = reporter.build_dashboard(payload, None, plain_history_snapshot(), self.NOW_MS)
        window = view.quotas[0].windows[0]
        self.assertIsNone(window.used_percent)
        self.assertEqual(window.pace.verdict, "NO DATA")

    def test_exhausted_status_maps_to_exhausted_pace(self):
        payload = usage_payload(
            limits=[
                window_limit(limit_id="openai-codex:primary", label="7 days", resets_at_ms=self.NOW_MS + DAY_MS, used_fraction=0.2, status="exhausted")
            ]
        )
        view = reporter.build_dashboard(payload, None, plain_history_snapshot(), self.NOW_MS)
        self.assertEqual(view.quotas[0].windows[0].pace.verdict, "EXHAUSTED")

    def test_coupled_short_window_gates_through_the_full_pipeline(self):
        payload = usage_payload(
            provider="anthropic",
            limits=[
                forecast_limit(
                    limit_id="anthropic:5h",
                    label="Claude 5 Hour",
                    used_fraction=0.40,
                    resets_at_ms=self.NOW_MS + HOUR_MS,
                    duration_ms=5 * HOUR_MS,
                ),
                forecast_limit(
                    limit_id="anthropic:7d",
                    label="Claude 7 Day",
                    used_fraction=0.50,
                    resets_at_ms=self.NOW_MS + 2 * HOUR_MS,
                    duration_ms=7 * DAY_MS,
                ),
            ],
        )
        history = plain_history_snapshot(
            samples=[
                self.sample(self.NOW_MS - 2 * HOUR_MS, 0.00, provider="anthropic", limit_id="anthropic:5h"),
                self.sample(self.NOW_MS - HOUR_MS, 0.20, provider="anthropic", limit_id="anthropic:5h"),
                self.sample(self.NOW_MS, 0.40, provider="anthropic", limit_id="anthropic:5h"),
                self.sample(self.NOW_MS - 2 * HOUR_MS, 0.26, provider="anthropic", limit_id="anthropic:7d"),
                self.sample(self.NOW_MS - HOUR_MS, 0.38, provider="anthropic", limit_id="anthropic:7d"),
                self.sample(self.NOW_MS, 0.50, provider="anthropic", limit_id="anthropic:7d"),
            ]
        )
        view = reporter.build_dashboard(payload, None, history, self.NOW_MS)
        short, long = view.quotas[0].windows
        self.assertEqual(short.pace.verdict, "GATED")
        self.assertAlmostEqual(short.pace.projected_percent, 60.0)
        self.assertEqual(long.pace.verdict, "ON PACE")


class RenderDashboardTests(unittest.TestCase):
    def view(self):
        pace = dashboard.Pace(
            verdict="ON PACE",
            projected_percent=60.0,
            rate="+1.0%/h",
            detail="keep going · ~60% by reset",
            exhaust_in_ms=None,
        )
        window = dashboard.QuotaWindow(
            label="7 days",
            used_percent=24.0,
            reset_ms=FIXED_NOW_MS + DAY_MS,
            status="ok",
            pace=pace,
        )
        quota = dashboard.ProviderQuota(
            provider="openai-codex",
            account="account 1",
            plan="Pro",
            windows=[window],
        )
        return dashboard.Dashboard(
            now_ms=FIXED_NOW_MS,
            quota_updated_ms=FIXED_NOW_MS - 60_000,
            quotas=[quota],
            quota_issue=None,
            tokens=None,
            history_sources=["WSL"],
            history_partial=False,
        )

    def test_pipes_svg_through_ffmpeg_and_returns_png_bytes(self):
        with mock.patch.object(reporter, "subprocess") as subprocess_mock:
            subprocess_mock.run.return_value = subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=0, stdout=b"png-bytes", stderr=b""
            )
            image = reporter.render_dashboard(self.view())
        self.assertEqual(image, b"png-bytes")
        run_call = subprocess_mock.run.call_args
        command = call_arg(run_call, 0, "args")
        self.assertTrue(str(command[0]).endswith("ffmpeg"))
        self.assertIn("image2pipe", command)
        self.assertIn("png", command)
        svg = call_arg(run_call, 1, "input").decode("utf-8")
        self.assertIn("<svg", svg)
        self.assertIn("OpenAI Codex", svg)
        self.assertIn("7 days", svg)

    def test_ffmpeg_failure_raises_usage_error_with_exit_two(self):
        with mock.patch.object(reporter, "subprocess") as subprocess_mock:
            subprocess_mock.run.return_value = subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=1, stdout=b"", stderr=b"boom"
            )
            with self.assertRaises(reporter.UsageError) as raised:
                reporter.render_dashboard(self.view())
        self.assertEqual(raised.exception.exit_code, 2)

    def test_missing_ffmpeg_raises_usage_error_with_exit_one(self):
        with mock.patch.object(reporter, "subprocess") as subprocess_mock:
            subprocess_mock.run.side_effect = FileNotFoundError("ffmpeg")
            with self.assertRaises(reporter.UsageError) as raised:
                reporter.render_dashboard(self.view())
        self.assertEqual(raised.exception.exit_code, 1)

    def test_ffmpeg_runs_with_the_bundled_fontconfig(self):
        with mock.patch.object(reporter, "subprocess") as subprocess_mock:
            subprocess_mock.run.return_value = subprocess.CompletedProcess(
                args=["ffmpeg"], returncode=0, stdout=b"png-bytes", stderr=b""
            )
            reporter.render_dashboard(self.view())
        env = subprocess_mock.run.call_args.kwargs["env"]
        self.assertEqual(env["FONTCONFIG_FILE"], str(reporter.FONTCONFIG_PATH))

    def test_missing_logo_assets_raise_usage_error_with_exit_one(self):
        events = [dashboard.ResetEvent("openai-codex", "7 days", "weekly", 1.0, FIXED_NOW_MS - DAY_MS, 0.0, FIXED_NOW_MS + 6 * DAY_MS, "")]
        with tempfile.TemporaryDirectory() as logo_dir, \
                mock.patch.object(dashboard, "_LOGO_DIR", Path(logo_dir)):
            dashboard._logo.cache_clear()
            self.addCleanup(dashboard._logo.cache_clear)
            for render in (reporter.render_dashboard, reporter.render_forecast):
                with self.assertRaises(reporter.UsageError) as raised:
                    render(self.view())
                self.assertEqual(raised.exception.exit_code, 1)
            with self.assertRaises(reporter.UsageError) as raised:
                reporter.render_reset(events, FIXED_NOW_MS)
            self.assertEqual(raised.exception.exit_code, 1)


class PublishDashboardTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.config = {"bot_token": "unit-test-token", "chat_id": "42"}
        self.payload = usage_payload(
            limits=[window_limit(resets_at_ms=FIXED_NOW_MS + DAY_MS, used_fraction=0.24)]
        )
        self.tokens = empty_token_snapshot()
        self.history = plain_history_snapshot()
        usage_patcher = mock.patch.object(reporter, "run_omp_usage", return_value=self.payload)
        token_patcher = mock.patch.object(reporter, "collect_token_snapshot", return_value=self.tokens)
        history_patcher = mock.patch.object(reporter, "collect_history_snapshot", return_value=self.history)
        render_patcher = mock.patch.object(reporter, "render_dashboard", return_value=b"rendered-image")
        forecast_patcher = mock.patch.object(reporter, "render_forecast", return_value=b"rendered-forecast")
        update_patcher = mock.patch.object(reporter, "update_pinned", return_value=True)
        announce_patcher = mock.patch.object(reporter, "announce_window_resets", return_value=0)
        self.run_usage = usage_patcher.start()
        self.collect_tokens = token_patcher.start()
        self.collect_history = history_patcher.start()
        self.render = render_patcher.start()
        self.render_forecast = forecast_patcher.start()
        self.update = update_patcher.start()
        self.announce = announce_patcher.start()
        for patcher in (usage_patcher, token_patcher, history_patcher, render_patcher, forecast_patcher, update_patcher, announce_patcher):
            self.addCleanup(patcher.stop)

    def rendered_view(self):
        self.render.assert_called_once()
        return self.render.call_args.args[0]

    def updates_for(self, message_key):
        return [call for call in self.update.call_args_list if call.kwargs["message_key"] == message_key]

    def test_successful_run_updates_usage_then_predictions(self):
        self.assertEqual(reporter.publish_dashboard(self.config), 0)
        view = self.rendered_view()
        self.assertEqual(len(view.quotas), 1)
        self.assertEqual(view.history_sources, ["WSL"])
        self.assertFalse(view.history_partial)
        self.assertIsNone(view.quota_issue)
        usage, predictions = self.updates_for(reporter.LIMITS_STATE_KEY), self.updates_for(reporter.FORECAST_STATE_KEY)
        self.assertEqual(len(usage), 1)
        self.assertEqual(len(predictions), 1)
        self.assertEqual(self.update.call_args_list[0], usage[0])
        self.assertEqual(call_arg(usage[0], 0, "config"), self.config)
        self.assertEqual(call_arg(usage[0], 1, "image"), b"rendered-image")
        self.assertIn("OMP usage", call_arg(usage[0], 2, "caption"))
        self.assertEqual(usage[0].kwargs["pinned_key"], reporter.PINNED_STATE_KEY)
        self.assertFalse(usage[0].kwargs["force_pin"])
        self.assertEqual(call_arg(predictions[0], 1, "image"), b"rendered-forecast")
        self.assertIn("OMP predictions", call_arg(predictions[0], 2, "caption"))
        self.assertEqual(predictions[0].kwargs["pinned_key"], reporter.FORECAST_PINNED_STATE_KEY)
        self.assertIs(self.render_forecast.call_args.args[0], view)
        self.announce.assert_called_once_with(self.config, self.payload)

    def test_token_collector_failure_still_updates_with_missing_tokens(self):
        self.collect_tokens.side_effect = reporter.UsageError("mini-1 unavailable: ssh timed out", 2)
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        view = self.rendered_view()
        self.assertIsNone(view.tokens)
        self.assertIsNone(view.quota_issue)
        self.assertEqual(len(self.updates_for(reporter.LIMITS_STATE_KEY)), 1)
        self.assertEqual(len(self.updates_for(reporter.FORECAST_STATE_KEY)), 1)
        self.announce.assert_called_once_with(self.config, self.payload)

    def test_partial_token_sources_mark_the_snapshot(self):
        self.collect_tokens.return_value = empty_token_snapshot(issues=["mini-1 unavailable: ssh timed out"])
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        view = self.rendered_view()
        self.assertTrue(view.tokens["issues"])
        self.assertEqual(self.update.call_count, 2)

    def test_quota_failure_updates_usage_only_and_skips_predictions_and_resets(self):
        self.run_usage.side_effect = reporter.UsageError("OMP usage timed out after 60s", 2)
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        view = self.rendered_view()
        self.assertTrue(view.quota_issue)
        self.assertEqual(view.quotas, [])
        self.assertIs(view.tokens, self.tokens)
        self.assertEqual(len(self.updates_for(reporter.LIMITS_STATE_KEY)), 1)
        self.assertEqual(self.updates_for(reporter.FORECAST_STATE_KEY), [])
        self.render_forecast.assert_not_called()
        self.announce.assert_not_called()

    def test_history_failure_marks_history_partial(self):
        self.collect_history.side_effect = reporter.UsageError("mini-1 unavailable: ssh connection failed", 2)
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        view = self.rendered_view()
        self.assertEqual(view.history_sources, [])
        self.assertTrue(view.history_partial)
        self.assertEqual(self.update.call_count, 2)

    def test_predictions_render_failure_keeps_usage_update_and_reset_alert(self):
        self.render_forecast.side_effect = reporter.UsageError("failed to load dashboard assets: logo missing", 1)
        self.assertEqual(reporter.publish_dashboard(self.config), 1)
        self.assertEqual(len(self.updates_for(reporter.LIMITS_STATE_KEY)), 1)
        self.assertEqual(self.updates_for(reporter.FORECAST_STATE_KEY), [])
        self.announce.assert_called_once_with(self.config, self.payload)

    def test_predictions_update_failure_exits_two_without_blocking_other_steps(self):
        def update(config, image, caption, *, message_key, pinned_key, force_pin=False):
            return message_key != reporter.FORECAST_STATE_KEY

        self.update.side_effect = update
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        self.assertEqual(self.update.call_count, 2)
        self.announce.assert_called_once_with(self.config, self.payload)

    def test_everything_unavailable_keeps_last_image_without_update(self):
        self.run_usage.side_effect = reporter.UsageError("OMP usage timed out after 60s", 2)
        self.collect_tokens.side_effect = reporter.UsageError("mini-1 unavailable: ssh timed out", 2)
        self.collect_history.side_effect = reporter.UsageError("mini-1 unavailable: ssh timed out", 2)
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        self.update.assert_not_called()
        self.render.assert_not_called()
        self.announce.assert_not_called()

    def test_fatal_payload_failure_keeps_available_tokens_and_exits_one(self):
        self.run_usage.side_effect = reporter.UsageError("OMP payload has no reports", 1)
        self.assertEqual(reporter.publish_dashboard(self.config), 1)
        self.update.assert_called_once()
        self.announce.assert_not_called()

    def test_reset_announcement_failure_exits_two_after_both_updates(self):
        self.announce.return_value = 2
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        self.assertEqual(self.update.call_count, 2)

    def test_failed_usage_update_exits_two_without_predictions_or_reset(self):
        self.update.side_effect = lambda config, image, caption, **kwargs: False
        self.assertEqual(reporter.publish_dashboard(self.config), 2)
        self.assertEqual(self.update.call_count, 1)
        self.announce.assert_not_called()

    def test_force_pin_flows_through_to_both_photos(self):
        reporter.publish_dashboard(self.config, force_pin=True)
        self.assertEqual(self.update.call_count, 2)
        self.assertTrue(all(call.kwargs["force_pin"] for call in self.update.call_args_list))


class RunModesTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.config = {"bot_token": "unit-test-token", "chat_id": "42"}

    def test_run_json_prints_quota_payload_unchanged(self):
        payload = {"reports": [{"provider": "zai", "limits": []}]}
        with mock.patch.object(reporter, "run_omp_usage", return_value=payload), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(reporter.run_json(), 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)

    def test_run_telegram_requires_configured_credentials(self):
        with mock.patch.object(reporter, "load_config", return_value=None), \
                mock.patch.object(reporter, "publish_dashboard") as publish:
            self.assertEqual(reporter.run_telegram(), 1)
        publish.assert_not_called()

    def test_run_telegram_delegates_to_publication(self):
        with mock.patch.object(reporter, "load_config", return_value=self.config), \
                mock.patch.object(reporter, "publish_dashboard", return_value=0) as publish:
            self.assertEqual(reporter.run_telegram(), 0)
        publish.assert_called_once()
        self.assertEqual(publish.call_args.args, (self.config,))
        self.assertFalse(publish.call_args.kwargs.get("force_pin", False))

    def test_setup_telegram_requires_configured_credentials(self):
        with mock.patch.object(reporter, "load_config", return_value=None), \
                mock.patch.object(reporter, "tg_call") as api, \
                mock.patch.object(reporter, "publish_dashboard") as publish:
            self.assertEqual(reporter.setup_telegram(), 1)
        api.assert_not_called()
        publish.assert_not_called()

    def test_setup_telegram_verifies_bot_then_publishes_with_explicit_pin(self):
        with mock.patch.object(reporter, "load_config", return_value=self.config), \
                mock.patch.object(
                    reporter, "tg_call", return_value={"ok": True, "result": {"username": "unitbot"}}
                ) as api, \
                mock.patch.object(reporter, "publish_dashboard", return_value=0) as publish, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reporter.setup_telegram(), 0)
        self.assertEqual(call_arg(api.call_args, 1, "method"), "getMe")
        publish.assert_called_once()
        self.assertTrue(publish.call_args.kwargs.get("force_pin"))

    def test_setup_telegram_rejects_bad_credentials_without_publishing(self):
        with mock.patch.object(reporter, "load_config", return_value=self.config), \
                mock.patch.object(
                    reporter,
                    "tg_call",
                    side_effect=urllib.error.HTTPError(
                        "https://api.telegram.org/bot-x/getMe", 401, "Unauthorized", {}, io.BytesIO(b"{}")
                    ),
                ), \
                mock.patch.object(reporter, "publish_dashboard") as publish, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(reporter.setup_telegram(), 1)
        publish.assert_not_called()


class RunRelayTests(unittest.TestCase):
    def test_pushes_bundle_over_ssh_and_returns_zero(self):
        bundle = relay_bundle(source="WSL")
        with mock.patch.object(reporter, "build_relay_bundle", return_value=bundle), mock.patch.object(
            reporter.subprocess, "run", return_value=subprocess.CompletedProcess(args=[], returncode=0)
        ) as run:
            self.assertEqual(reporter.run_relay("openclaw"), 0)
        self.assertEqual(
            run.call_args.args[0],
            [
                reporter.TOKEN_SSH_BINARY,
                "-T",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "ConnectTimeout=10",
                "openclaw",
                "umask 077 && mkdir -p .local/state/codex-usage/relay && "
                "cat > .local/state/codex-usage/relay/.WSL.tmp && "
                f"python3 -c '{reporter.RELAY_REMOTE_CHECK}' .local/state/codex-usage/relay/.WSL.tmp && "
                "mv .local/state/codex-usage/relay/.WSL.tmp .local/state/codex-usage/relay/WSL.json.gz",
            ],
        )
        self.assertEqual(json.loads(gzip.decompress(run.call_args.kwargs["input"])), bundle)
        self.assertEqual(run.call_args.kwargs["timeout"], 60)
        self.assertIs(run.call_args.kwargs["check"], False)

    def test_nonzero_ssh_exit_returns_two(self):
        with mock.patch.object(reporter, "build_relay_bundle", return_value=relay_bundle()), mock.patch.object(
            reporter.subprocess, "run", return_value=subprocess.CompletedProcess(args=[], returncode=255)
        ), contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(reporter.run_relay("openclaw"), 2)
        self.assertEqual(stderr.getvalue(), "codex-usage-check: relay ssh exited 255\n")

    def test_ssh_timeout_returns_two(self):
        with mock.patch.object(reporter, "build_relay_bundle", return_value=relay_bundle()), mock.patch.object(
            reporter.subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=60)
        ), contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(reporter.run_relay("openclaw"), 2)
        self.assertEqual(stderr.getvalue(), "codex-usage-check: relay ssh timed out\n")

    def test_ssh_os_error_returns_two(self):
        with mock.patch.object(reporter, "build_relay_bundle", return_value=relay_bundle()), mock.patch.object(
            reporter.subprocess, "run", side_effect=OSError("ssh missing")
        ), contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(reporter.run_relay("openclaw"), 2)
        self.assertEqual(stderr.getvalue(), "codex-usage-check: relay ssh failed: ssh missing\n")

    def test_dash_prefixed_host_is_rejected_before_ssh(self):
        with mock.patch.object(reporter, "build_relay_bundle") as build, mock.patch.object(
            reporter.subprocess, "run"
        ) as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(reporter.run_relay("-oProxyCommand=x"), 1)
        build.assert_not_called()
        run.assert_not_called()


class RelayModeTests(unittest.TestCase):
    def test_relay_runs_without_telegram_lock(self):
        with mock.patch.object(reporter, "run_relay", return_value=0) as relay, mock.patch.object(
            reporter, "acquire_update_lock"
        ) as lock:
            self.assertEqual(reporter.main(["--relay", "openclaw"]), 0)
        relay.assert_called_once_with("openclaw")
        lock.assert_not_called()

    def test_relay_requires_exactly_one_host(self):
        with mock.patch.object(reporter, "run_relay") as relay, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(reporter.main(["--relay"]), 1)
            self.assertEqual(reporter.main(["--relay", "-oProxyCommand=x"]), 1)
        relay.assert_not_called()

    def test_relay_cannot_combine_with_telegram(self):
        with mock.patch.object(reporter, "run_relay") as relay, mock.patch.object(
            reporter, "acquire_update_lock"
        ) as lock, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(reporter.main(["--relay", "openclaw", "--telegram"]), 1)
        relay.assert_not_called()
        lock.assert_not_called()


class MultipartFormTests(unittest.TestCase):
    def test_boolean_fields_encode_as_lowercase_wire_values(self):
        body, boundary = reporter.multipart_form(
            {"chat_id": "42", "disable_notification": True, "caption": "<b>hi</b>"},
            "photo",
            "omp-usage.png",
            b"image-bytes",
        )
        self.assertIn(b'name="disable_notification"\r\n\r\ntrue\r\n', body)
        self.assertIn(b'name="caption"\r\n\r\n<b>hi</b>\r\n', body)
        self.assertIn(b"image-bytes", body)
        self.assertTrue(body.endswith(b"--" + boundary.encode("ascii") + b"--\r\n"))

    def test_file_part_carries_png_media_with_content_type(self):
        body, _ = reporter.multipart_form({}, "photo", "omp-usage.png", b"png-data")
        self.assertIn(
            b'Content-Disposition: form-data; name="photo"; filename="omp-usage.png"\r\n'
            b"Content-Type: image/png\r\n\r\n"
            b"png-data\r\n",
            body,
        )


class UpdatePinnedTests(TelegramStateMixin):
    CAPTION_A = "<b>OMP usage</b> · checked 2026-11-25 20:00 UTC"
    CAPTION_B = "<b>OMP usage</b> · checked 2026-11-25 21:00 UTC"

    def setUp(self):
        super().setUp()
        self.image = b"unit-image"

    def publish(self, caption, **kwargs):
        return reporter.update_pinned(
            self.config,
            self.image,
            caption,
            message_key=reporter.LIMITS_STATE_KEY,
            pinned_key=reporter.PINNED_STATE_KEY,
            **kwargs,
        )

    def photo_payload(self, message_id):
        return {"ok": True, "result": {"message_id": message_id}}

    def upload_methods(self, upload):
        return [call_arg(call, 1, "method") for call in upload.call_args_list]

    def api_methods(self, api):
        return [call_arg(call, 1, "method") for call in api.call_args_list]

    def test_edit_reuses_photo_with_html_caption_and_no_repeated_pin(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111, "reset_watch": {"keep": {}}})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = self.photo_payload(0)
            api.return_value = {"ok": True, "result": {}}
            self.assertTrue(self.publish(self.CAPTION_A))
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(call_arg(upload.call_args, 1, "method"), "editMessageMedia")
        fields = call_arg(upload.call_args, 2, "fields")
        self.assertEqual(fields["chat_id"], "42")
        self.assertEqual(fields["message_id"], 111)
        self.assertNotIn("caption", fields)
        self.assertNotIn("parse_mode", fields)
        media = json.loads(fields["media"])
        self.assertEqual(media["type"], "photo")
        self.assertEqual(media["media"], "attach://photo")
        self.assertEqual(media["caption"], self.CAPTION_A)
        self.assertEqual(media["parse_mode"], "HTML")
        self.assertEqual(call_arg(upload.call_args, 5, "media"), self.image)
        self.assertNotIn("pinChatMessage", self.api_methods(api))
        self.assertNotIn("sendMessage", self.api_methods(api))
        self.assertEqual(
            self.read_state(),
            {"message_id": 111, "pinned_message_id": 111, "reset_watch": {"keep": {}}},
        )

    def test_caption_change_edits_in_place_without_resend_or_repin(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = self.photo_payload(0)
            self.assertTrue(self.publish(self.CAPTION_A))
            self.assertTrue(self.publish(self.CAPTION_B))
        self.assertEqual(
            [json.loads(call_arg(call, 2, "fields")["media"])["caption"] for call in upload.call_args_list],
            [self.CAPTION_A, self.CAPTION_B],
        )
        api.assert_not_called()

    def test_unchanged_edit_counts_as_success_without_new_post(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.side_effect = self.telegram_error("Bad Request: message is not modified")
            self.assertTrue(self.publish(self.CAPTION_A))
        upload.assert_called_once()
        api.assert_not_called()
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_legacy_photo_without_pin_record_is_pinned_once(self):
        self.write_state({"message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = self.photo_payload(0)
            api.return_value = {"ok": True, "result": {}}
            self.assertTrue(self.publish(self.CAPTION_A))
            self.assertTrue(self.publish(self.CAPTION_A))
        pins = [call for call in api.call_args_list if call_arg(call, 1, "method") == "pinChatMessage"]
        self.assertEqual(len(pins), 1)
        self.assertEqual(call_arg(pins[0], 2, "params")["message_id"], 111)
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_deleted_only_failure_replaces_photo_quietly(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111, "note": "keep"})
        pin_state = []

        def api_handle(*args, **kwargs):
            method = args[1] if len(args) > 1 else kwargs.get("method")
            if method == "pinChatMessage":
                pin_state.append(self.read_state())
            return {"ok": True, "result": {}}

        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call", side_effect=api_handle) as api:
            upload.side_effect = [
                self.telegram_error("Bad Request: message to edit not found"),
                self.photo_payload(555),
            ]
            self.assertTrue(self.publish(self.CAPTION_A))
        self.assertEqual(
            self.upload_methods(upload),
            ["editMessageMedia", "sendPhoto"],
        )
        self.assertEqual(pin_state[0]["message_id"], 555)
        self.assertEqual(self.api_methods(api), ["pinChatMessage"])
        self.assertEqual(call_arg(api.call_args, 2, "params")["message_id"], 555)
        self.assertEqual(self.read_state(), {"message_id": 555, "pinned_message_id": 555, "note": "keep"})

    def test_retired_images_are_deleted_after_canonical_pin_succeeds(self):
        self.write_state({
            "message_id": 111,
            "pinned_message_id": 111,
            "tokens_message_id": 42,
            "forecast_message_id": 43,
            "reset_watch": {"keep": {}},
        })
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = self.photo_payload(0)
            api.return_value = {"ok": True, "result": {}}
            self.assertTrue(self.publish(self.CAPTION_A))
        deletions = [
            call_arg(call, 2, "params")["message_id"]
            for call in api.call_args_list
            if call_arg(call, 1, "method") == "deleteMessage"
        ]
        self.assertEqual(deletions, [42])
        self.assertNotIn(111, deletions)
        self.assertEqual(
            self.read_state(),
            {"message_id": 111, "pinned_message_id": 111, "forecast_message_id": 43, "reset_watch": {"keep": {}}},
        )

    def test_aged_retired_image_is_unpinned_when_delete_is_refused(self):
        self.write_state({"message_id": 111, "pinned_message_id": 42, "tokens_message_id": 42})
        seen = []

        def api_handle(*args, **kwargs):
            method = args[1] if len(args) > 1 else kwargs.get("method")
            params = args[2] if len(args) > 2 else (kwargs.get("params") or {})
            seen.append((method, params.get("message_id")))
            if method == "deleteMessage":
                raise self.telegram_error("Bad Request: message can't be deleted")
            return {"ok": True, "result": {}}

        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call", side_effect=api_handle):
            upload.return_value = self.photo_payload(0)
            self.assertTrue(self.publish(self.CAPTION_A))
        self.assertIn(("deleteMessage", 42), seen)
        self.assertIn(("unpinChatMessage", 42), seen)
        self.assertNotIn(("deleteMessage", 111), seen)
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_transient_cleanup_failure_retries_without_new_posts_or_canonical_damage(self):
        self.write_state({
            "message_id": 111,
            "pinned_message_id": 111,
            "tokens_message_id": 42,
            "reset_watch": {"keep": {}},
        })
        deletions = []

        def api_handle(*args, **kwargs):
            method = args[1] if len(args) > 1 else kwargs.get("method")
            params = args[2] if len(args) > 2 else (kwargs.get("params") or {})
            if method == "deleteMessage":
                deletions.append(params.get("message_id"))
                if len(deletions) == 1:
                    raise OSError("temporarily unreachable")
            return {"ok": True, "result": {}}

        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call", side_effect=api_handle):
            upload.return_value = self.photo_payload(0)
            self.assertTrue(self.publish(self.CAPTION_A))
            self.assertEqual(self.read_state()["tokens_message_id"], 42)
            self.assertEqual(self.read_state()["message_id"], 111)
            self.assertTrue(self.publish(self.CAPTION_B))
        self.assertEqual(deletions, [42, 42])
        self.assertEqual(self.upload_methods(upload), ["editMessageMedia", "editMessageMedia"])
        self.assertNotIn("tokens_message_id", self.read_state())
        self.assertEqual(self.read_state()["reset_watch"], {"keep": {}})

    def test_corrupt_state_is_rejected_without_posting(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text("not-json{{", encoding="utf-8")
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            with self.assertRaises(reporter.UsageError) as raised:
                self.publish(self.CAPTION_A)
        self.assertEqual(raised.exception.exit_code, 2)
        upload.assert_not_called()
        api.assert_not_called()
        self.assertEqual(self.state_path.read_text(encoding="utf-8"), "not-json{{")

    def test_generic_edit_failure_keeps_saved_id_without_new_post(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.side_effect = self.telegram_error("Bad Request: chat not found")
            self.assertFalse(self.publish(self.CAPTION_A))
        upload.assert_called_once()
        api.assert_not_called()
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_network_failure_on_edit_keeps_saved_id_without_new_post(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.side_effect = TimeoutError("telegram timed out")
            self.assertFalse(self.publish(self.CAPTION_A))
        upload.assert_called_once()
        api.assert_not_called()
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_rate_limited_edit_keeps_saved_id_without_new_post(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.side_effect = self.telegram_error("Too Many Requests: retry after 5", code=429)
            self.assertFalse(self.publish(self.CAPTION_A))
        upload.assert_called_once()
        api.assert_not_called()
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_pin_permission_failure_keeps_durable_id_and_avoids_duplicate(self):
        self.write_state({"message_id": 111})
        rights = {"granted": False}

        def api_handle(*args, **kwargs):
            method = args[1] if len(args) > 1 else kwargs.get("method")
            if method == "pinChatMessage" and not rights["granted"]:
                raise reporter.TelegramError("Telegram pinChatMessage failed: not enough rights")
            return {"ok": True, "result": {}}

        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call", side_effect=api_handle):
            upload.return_value = self.photo_payload(0)
            self.assertFalse(self.publish(self.CAPTION_A))
            self.assertEqual(self.read_state(), {"message_id": 111})
            rights["granted"] = True
            self.assertTrue(self.publish(self.CAPTION_A))
        self.assertEqual(self.upload_methods(upload), ["editMessageMedia", "editMessageMedia"])
        self.assertEqual(self.read_state(), {"message_id": 111, "pinned_message_id": 111})

    def test_initial_send_persists_id_then_pins_quietly(self):
        pin_params = []

        def api_handle(*args, **kwargs):
            method = args[1] if len(args) > 1 else kwargs.get("method")
            params = args[2] if len(args) > 2 else (kwargs.get("params") or {})
            if method == "pinChatMessage":
                pin_params.append(params)
            return {"ok": True, "result": {}}

        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call", side_effect=api_handle):
            upload.return_value = self.photo_payload(777)
            self.assertTrue(self.publish(self.CAPTION_A))
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(call_arg(upload.call_args, 1, "method"), "sendPhoto")
        fields = call_arg(upload.call_args, 2, "fields")
        self.assertEqual(fields["chat_id"], "42")
        self.assertEqual(fields["caption"], self.CAPTION_A)
        self.assertEqual(fields["parse_mode"], "HTML")
        self.assertIs(fields["disable_notification"], True)
        self.assertEqual(call_arg(upload.call_args, 5, "media"), self.image)
        self.assertEqual(pin_params, [{"chat_id": "42", "message_id": 777, "disable_notification": True}])
        self.assertEqual(self.read_state(), {"message_id": 777, "pinned_message_id": 777})

    def test_initial_pin_failure_keeps_sent_id_and_pins_on_next_run(self):
        rights = {"granted": False}

        def api_handle(*args, **kwargs):
            method = args[1] if len(args) > 1 else kwargs.get("method")
            if method == "pinChatMessage" and not rights["granted"]:
                raise reporter.TelegramError("Telegram pinChatMessage failed: no rights")
            return {"ok": True, "result": {}}

        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call", side_effect=api_handle):
            upload.return_value = self.photo_payload(777)
            self.assertFalse(self.publish(self.CAPTION_A))
            self.assertEqual(self.read_state(), {"message_id": 777})
            rights["granted"] = True
            self.assertTrue(self.publish(self.CAPTION_A))
        self.assertEqual(self.upload_methods(upload), ["sendPhoto", "editMessageMedia"])
        self.assertEqual(self.read_state(), {"message_id": 777, "pinned_message_id": 777})

    def test_force_pin_repins_the_canonical_message(self):
        self.write_state({"message_id": 111, "pinned_message_id": 111})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = self.photo_payload(0)
            api.return_value = {"ok": True, "result": {}}
            self.assertTrue(self.publish(self.CAPTION_A, force_pin=True))
        self.assertEqual(self.api_methods(api), ["pinChatMessage"])
        self.assertEqual(call_arg(api.call_args, 2, "params")["message_id"], 111)

    def test_predictions_photo_uses_its_own_keys_and_is_never_retired(self):
        self.write_state({
            "message_id": 111,
            "pinned_message_id": 111,
            "forecast_message_id": 222,
            "tokens_message_id": 42,
        })
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = self.photo_payload(0)
            api.return_value = {"ok": True, "result": {}}
            for _ in range(2):
                self.assertTrue(reporter.update_pinned(
                    self.config,
                    self.image,
                    self.CAPTION_A,
                    message_key=reporter.FORECAST_STATE_KEY,
                    pinned_key=reporter.FORECAST_PINNED_STATE_KEY,
                ))
        self.assertEqual([call_arg(call, 2, "fields")["message_id"] for call in upload.call_args_list], [222, 222])
        calls = [(call_arg(call, 1, "method"), call_arg(call, 2, "params")["message_id"]) for call in api.call_args_list]
        self.assertEqual(calls.count(("pinChatMessage", 222)), 1)
        self.assertIn(("deleteMessage", 42), calls)
        self.assertNotIn(("deleteMessage", 222), calls)
        self.assertNotIn(("deleteMessage", 111), calls)
        self.assertEqual(self.read_state(), {
            "message_id": 111,
            "pinned_message_id": 111,
            "forecast_message_id": 222,
            "forecast_pinned_message_id": 222,
        })


def window_limit(
    limit_id="openai-codex:primary",
    label="7 days",
    window_label="7 days",
    window_id="weekly",
    duration_ms=604800000,
    resets_at_ms=None,
    used_fraction=0.0,
    unit="percent",
    used=None,
    limit=None,
    status="ok",
):
    window = {"id": window_id, "label": window_label}
    if duration_ms is not None:
        window["durationMs"] = duration_ms
    if resets_at_ms is not None:
        window["resetsAt"] = resets_at_ms
    amount = {"unit": unit, "usedFraction": used_fraction}
    if used is not None:
        amount["used"] = used
    if limit is not None:
        amount["limit"] = limit
    return {"id": limit_id, "label": label, "window": window, "amount": amount, "status": status}


def usage_payload(provider="openai-codex", limits=None):
    return {
        "generatedAt": 1,
        "reports": [{"provider": provider, "limits": limits if limits is not None else []}],
    }


class LongWindowKindTests(unittest.TestCase):
    def test_duration_ms_classifies_weekly_and_monthly(self):
        self.assertEqual(reporter.long_window_kind(window_limit(duration_ms=604800000)), "weekly")
        self.assertEqual(reporter.long_window_kind(window_limit(duration_ms=2592000000)), "monthly")

    def test_missing_duration_falls_back_to_window_text(self):
        self.assertEqual(reporter.long_window_kind(window_limit(duration_ms=None, window_id="", window_label="Monthly", label="Zread Quota")), "monthly")
        self.assertEqual(reporter.long_window_kind(window_limit(duration_ms=None, window_id="", window_label="Weekly", label="Zread Quota")), "weekly")
        self.assertIsNone(reporter.long_window_kind(window_limit(duration_ms=None, window_id="", window_label="Quarterly", label="Zread Quota")))

    def test_short_windows_are_never_tracked(self):
        for duration_ms in (18_000_000, 86_400_000, 302_399_999):
            self.assertIsNone(reporter.long_window_kind(window_limit(duration_ms=duration_ms)))


class DetectWindowResetsTests(unittest.TestCase):
    NOW_MS = FIXED_NOW_MS

    def entry(self, used, resets_at_ms):
        return {
            "provider": "openai-codex",
            "kind": "weekly",
            "label": "7 days",
            "amount_text": "",
            "resets_at_ms": resets_at_ms,
            "used": used,
            "seen_at_ms": self.NOW_MS,
        }

    def watch(self, used, resets_at_ms):
        return {"openai-codex:0:openai-codex:primary": self.entry(used, resets_at_ms)}

    def current(self, used=0.0, resets_at_ms=None):
        resets = self.NOW_MS + 7 * DAY_MS if resets_at_ms is None else resets_at_ms
        return self.watch(used, resets)

    def test_forward_jump_with_drop_announces_closed_window(self):
        old_resets = self.NOW_MS - 1_000
        resets = reporter.detect_window_resets(self.watch(1.0, old_resets), self.current())
        self.assertEqual(len(resets), 1)
        self.assertEqual(resets[0]["closed_used"], 1.0)
        self.assertEqual(resets[0]["closed_at_ms"], old_resets)
        self.assertEqual(resets[0]["fresh_used"], 0.0)
        self.assertEqual(resets[0]["kind"], "weekly")
        self.assertEqual(resets[0]["label"], "7 days")

    def test_forward_jump_without_drop_is_ignored(self):
        self.assertEqual(
            reporter.detect_window_resets(self.watch(0.95, self.NOW_MS), self.current(used=0.94)),
            [],
        )

    def test_drop_without_forward_jump_is_ignored(self):
        same = self.NOW_MS + 7 * DAY_MS
        self.assertEqual(
            reporter.detect_window_resets(self.watch(0.95, same), self.current(used=0.0, resets_at_ms=same)),
            [],
        )

    def test_reset_time_drift_within_tolerance_is_ignored(self):
        self.assertEqual(
            reporter.detect_window_resets(
                self.watch(0.95, self.NOW_MS), self.current(used=0.0, resets_at_ms=self.NOW_MS + 30_000)
            ),
            [],
        )

    def test_unused_closed_window_is_not_announced(self):
        self.assertEqual(
            reporter.detect_window_resets(self.watch(0.03, self.NOW_MS - 1_000), self.current()),
            [],
        )

    def test_missing_baseline_is_not_a_reset(self):
        self.assertEqual(reporter.detect_window_resets({}, self.current()), [])
        self.assertEqual(
            reporter.detect_window_resets({"zai:0:other": self.entry(1.0, 1)}, self.current()),
            [],
        )

    def test_events_sort_by_provider_then_label(self):
        previous = {}
        current = {}
        for provider, label in (
            ("anthropic", "Claude 7 Day"),
            ("anthropic", "Claude 7 Day (Fable)"),
            ("zai", "Zread Quota"),
        ):
            key = f"{provider}:0:{provider}:{label}"
            previous[key] = {
                "provider": provider,
                "kind": "weekly",
                "label": label,
                "amount_text": "",
                "resets_at_ms": self.NOW_MS - 1_000,
                "used": 0.9,
                "seen_at_ms": self.NOW_MS,
            }
            current[key] = dict(previous[key], resets_at_ms=self.NOW_MS + DAY_MS, used=0.0)
        resets = reporter.detect_window_resets(previous, current)
        self.assertEqual(
            [(reset["provider"], reset["label"]) for reset in resets],
            [
                ("anthropic", "Claude 7 Day"),
                ("anthropic", "Claude 7 Day (Fable)"),
                ("zai", "Zread Quota"),
            ],
        )


class ResetMessageTests(unittest.TestCase):
    def event(self, **overrides):
        event = {
            "provider": "openai-codex",
            "kind": "weekly",
            "label": "7 days",
            "amount_text": "",
            "closed_used": 1.0,
            "closed_at_ms": 1_789_000_000_000,
            "resets_at_ms": 1_789_000_000_000 + 7 * DAY_MS,
            "fresh_used": 0.0,
        }
        event.update(overrides)
        return event

    def test_weekly_reset_text_marks_closed_usage(self):
        text = reporter.reset_message([self.event()])
        self.assertIn("<b>OpenAI Codex</b>", text)
        self.assertIn("closed at <b>100.0%</b> used", text)
        self.assertIn("fresh window resets <b>", text)

    def test_titles_follow_the_announced_kinds(self):
        self.assertIn(
            "<b>Monthly limit reset</b>",
            reporter.reset_message([self.event(kind="monthly")]),
        )
        self.assertIn(
            "<b>Limit resets</b>",
            reporter.reset_message([self.event(), self.event(kind="monthly", provider="zai", label="Monthly")]),
        )

    def test_amounts_are_appended_when_available(self):
        text = reporter.reset_message([self.event(amount_text="940/1,000 requests")])
        self.assertIn("(940/1,000 requests)", text)

    def test_batched_text_never_exceeds_the_telegram_limit(self):
        providers = ("anthropic", "google-antigravity", "openai-codex", "opencode-go", "zai")
        events = [
            self.event(provider=provider, label=f"Long limit name {index} of {provider}")
            for provider in providers
            for index in range(8)
        ]
        text = reporter.reset_message(events)
        self.assertLessEqual(len(text), reporter.CAPTION_MAX_CHARS)
        self.assertRegex(text, r"\n\+\d+ more$")

    def test_window_amount_text_accepts_float_amounts(self):
        self.assertEqual(
            reporter.window_amount_text({"unit": "requests", "used": 940.0, "limit": 1000}),
            "940/1,000 requests",
        )
        self.assertEqual(
            reporter.window_amount_text({"unit": "credits", "used": 12.5, "limit": 500.0}),
            "12.5/500 credits",
        )
        self.assertEqual(reporter.window_amount_text({"unit": "requests", "used": "9", "limit": 10}), "")


class ResetAnnouncementTests(TelegramStateMixin):
    KEY = "openai-codex:0:openai-codex:primary"
    BASE_MS = FIXED_NOW_MS

    def setUp(self):
        super().setUp()

    def read_watch(self):
        return self.read_state().get("reset_watch")

    def payload(self, used_fraction=0.0, resets_offset_ms=7 * DAY_MS):
        return usage_payload(
            limits=[
                window_limit(
                    resets_at_ms=self.BASE_MS + resets_offset_ms,
                    used_fraction=used_fraction,
                )
            ]
        )

    def closed_watch(self, used=1.0):
        return {
            self.KEY: {
                "provider": "openai-codex",
                "kind": "weekly",
                "label": "7 days",
                "amount_text": "",
                "resets_at_ms": self.BASE_MS - HOUR_MS,
                "used": used,
                "seen_at_ms": self.BASE_MS - 300_000,
            }
        }

    def test_tracked_label_prefers_limit_label_over_window_label(self):
        limit = window_limit(
            limit_id="anthropic:7d:fable",
            label="Claude 7 Day (Fable)",
            window_label="7 Day",
            resets_at_ms=self.BASE_MS + 7 * DAY_MS,
        )
        tracked = reporter.tracked_window_limits(
            usage_payload(provider="anthropic", limits=[limit]), self.BASE_MS
        )
        self.assertEqual(tracked["anthropic:0:anthropic:7d:fable"]["label"], "Claude 7 Day (Fable)")

    def test_accounts_with_shared_limit_ids_are_not_tracked(self):
        spent = window_limit(
            limit_id="weekly",
            label="Weekly limit",
            window_label="Weekly",
            resets_at_ms=self.BASE_MS + 2 * DAY_MS,
            used_fraction=1.0,
        )
        fresh = window_limit(
            limit_id="weekly",
            label="Weekly limit",
            window_label="Weekly",
            resets_at_ms=self.BASE_MS + 7 * DAY_MS,
            used_fraction=0.0,
        )
        shared = {"reports": [{"provider": "opencode-go", "limits": [spent]}, {"provider": "opencode-go", "limits": [fresh]}]}
        self.assertEqual(reporter.tracked_window_limits(shared, self.BASE_MS), {})
        distinct = {
            "reports": [
                {"provider": "opencode-go", "limits": [spent]},
                {"provider": "opencode-go", "limits": [dict(fresh, id="monthly")]},
            ]
        }
        tracked = reporter.tracked_window_limits(distinct, self.BASE_MS)
        self.assertEqual(sorted(tracked), ["opencode-go:0:weekly", "opencode-go:1:monthly"])
        self.assertEqual(tracked["opencode-go:0:weekly"]["used"], 1.0)
        self.assertEqual(tracked["opencode-go:1:monthly"]["used"], 0.0)

    def test_first_run_records_baseline_without_messaging(self):
        with mock.patch.object(reporter, "tg_call") as api, \
                mock.patch.object(reporter, "tg_upload") as upload:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        api.assert_not_called()
        upload.assert_not_called()
        watch = self.read_watch()
        self.assertEqual(list(watch), [self.KEY])
        self.assertEqual(watch[self.KEY]["used"], 0.0)
        self.assertEqual(watch[self.KEY]["kind"], "weekly")

    def test_window_rollover_sends_one_notifying_photo_and_updates_watch(self):
        self.write_state({"message_id": 5, "reset_watch": self.closed_watch()})
        with mock.patch.object(reporter, "tg_upload") as upload, \
                mock.patch.object(reporter, "tg_call") as api:
            upload.return_value = {"ok": True, "result": {"message_id": 9}}
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        upload.assert_called_once()
        self.assertEqual(call_arg(upload.call_args, 0, "bot_token"), "unit-test-token")
        self.assertEqual(call_arg(upload.call_args, 1, "method"), "sendPhoto")
        fields = call_arg(upload.call_args, 2, "fields")
        self.assertEqual(fields["chat_id"], "42")
        self.assertIs(fields["disable_notification"], False)
        self.assertIn("Weekly limit reset", fields["caption"])
        self.assertIn("OpenAI Codex", fields["caption"])
        image = call_arg(upload.call_args, 5, "media")
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        api.assert_not_called()
        self.assertEqual(self.read_watch()[self.KEY]["resets_at_ms"], self.BASE_MS + 7 * DAY_MS)
        self.assertEqual(self.read_state()["message_id"], 5)

    def test_weekly_and_monthly_resets_batch_into_one_photo(self):
        watch = self.closed_watch()
        monthly_key = "zai:0:zai:monthly"
        watch[monthly_key] = {
            "provider": "zai",
            "kind": "monthly",
            "label": "Monthly",
            "amount_text": "",
            "resets_at_ms": self.BASE_MS - HOUR_MS,
            "used": 1.0,
            "seen_at_ms": self.BASE_MS - 300_000,
        }
        payload = {
            "generatedAt": 1,
            "reports": [
                {
                    "provider": "openai-codex",
                    "limits": [window_limit(resets_at_ms=self.BASE_MS + 7 * DAY_MS, used_fraction=0.0)],
                },
                {
                    "provider": "zai",
                    "limits": [
                        window_limit(
                            limit_id="zai:monthly",
                            label="Monthly",
                            window_label="Monthly",
                            duration_ms=30 * DAY_MS,
                            resets_at_ms=self.BASE_MS + 30 * DAY_MS,
                            used_fraction=0.0,
                        )
                    ],
                },
            ],
        }
        self.write_state({"reset_watch": watch})
        with mock.patch.object(reporter, "tg_upload") as upload:
            upload.return_value = {"ok": True, "result": {"message_id": 9}}
            self.assertEqual(reporter.announce_window_resets(self.config, payload), 0)
        upload.assert_called_once()
        caption = call_arg(upload.call_args, 2, "fields")["caption"]
        self.assertIn("Limit resets", caption)
        self.assertIn("OpenAI Codex", caption)
        self.assertIn("ZAI", caption)
        self.assertEqual(sorted(self.read_watch()), sorted([self.KEY, monthly_key]))

    def test_failed_send_returns_two_and_retries_next_run(self):
        self.write_state({"reset_watch": self.closed_watch()})
        with mock.patch.object(
            reporter, "tg_upload", side_effect=reporter.TelegramError("Telegram sendPhoto failed")
        ) as upload:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 2)
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 2)
        self.assertEqual(upload.call_count, 2)
        self.assertEqual(self.read_watch(), self.closed_watch())

    def test_render_failure_returns_one_and_keeps_watch_for_retry(self):
        self.write_state({"reset_watch": self.closed_watch()})
        with mock.patch.object(reporter, "render_reset") as render, \
                mock.patch.object(reporter, "tg_upload", return_value={"ok": True, "result": {"message_id": 9}}) as upload:
            render.side_effect = [reporter.UsageError("failed to load dashboard assets: logo missing", 1), b"reset-image"]
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 1)
            upload.assert_not_called()
            self.assertEqual(self.read_watch(), self.closed_watch())
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        upload.assert_called_once()

    def test_reset_events_convert_fractions_to_percents(self):
        closed_at = self.BASE_MS - HOUR_MS
        resets_at = self.BASE_MS + 7 * DAY_MS
        event = reporter.reset_events([{
            "provider": "openai-codex",
            "kind": "weekly",
            "label": "7 days",
            "amount_text": "940/1,000 requests",
            "closed_used": 0.92,
            "closed_at_ms": closed_at,
            "resets_at_ms": resets_at,
            "fresh_used": 0.02,
        }])[0]
        self.assertEqual(
            (event.provider, event.label, event.kind, event.closed_used_percent, event.fresh_used_percent),
            ("openai-codex", "7 days", "weekly", 92.0, 2.0),
        )
        self.assertEqual((event.closed_at_ms, event.resets_at_ms, event.amount_text), (closed_at, resets_at, "940/1,000 requests"))

    def test_below_floor_rollover_updates_watch_without_messaging(self):
        watch = self.closed_watch(used=0.03)
        self.write_state({"reset_watch": watch})
        with mock.patch.object(reporter, "tg_upload") as upload:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        upload.assert_not_called()
        self.assertEqual(self.read_watch()[self.KEY]["used"], 0.0)

    def test_short_windows_are_not_tracked(self):
        limit = window_limit(
            limit_id="zai:tokens:5h",
            label="ZAI 5 Hours Token Quota",
            window_label="5 Hours",
            window_id="5h",
            duration_ms=18_000_000,
            resets_at_ms=self.BASE_MS + HOUR_MS,
            used_fraction=0.5,
        )
        with mock.patch.object(reporter, "tg_call") as api:
            self.assertEqual(
                reporter.announce_window_resets(self.config, usage_payload(provider="zai", limits=[limit])),
                0,
            )
        api.assert_not_called()
        self.assertFalse(self.state_path.exists())

    def test_stale_entries_past_ttl_are_pruned_on_save(self):
        now_ms = time.time_ns() // 1_000_000
        self.write_state(
            {
                "reset_watch": {
                    "gone:0:x": {
                        "provider": "gone",
                        "kind": "weekly",
                        "label": "old",
                        "amount_text": "",
                        "resets_at_ms": 1,
                        "used": 0.5,
                        "seen_at_ms": now_ms - reporter.RESET_WATCH_TTL_MS - 1_000,
                    }
                }
            }
        )
        with mock.patch.object(reporter, "tg_call") as api:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        api.assert_not_called()
        self.assertEqual(list(self.read_watch()), [self.KEY])


def forecast_limit(
    used_fraction=0.24,
    resets_at_ms=None,
    duration_ms=None,
    status="ok",
    limit_id="openai-codex:primary",
    label="7 days",
):
    limit = {
        "id": limit_id,
        "label": label,
        "status": status,
        "window": {
            "label": label,
            "resetsAt": resets_at_ms,
        },
        "scope": {"tier": "default"},
        "amount": {
            "unit": "percent",
            "usedFraction": used_fraction,
        },
    }
    if duration_ms is not None:
        limit["window"]["durationMs"] = duration_ms
    return limit


def forecast_snapshot(
    series,
    provider="openai-codex",
    limit_id="openai-codex:primary",
    account_key="acct",
):
    samples = [
        {
            "recorded_at_ms": t,
            "provider": provider,
            "account_key": account_key,
            "limit_id": limit_id,
            "used_fraction": frac,
        }
        for t, frac in series
    ]
    return {
        "start_ms": series[0][0] if series else 0,
        "end_ms": series[-1][0] if series else 0,
        "samples": samples,
        "sources_ok": ["WSL"],
        "issues": [],
    }

class HistorySeriesTests(unittest.TestCase):
    NOW_MS = FIXED_NOW_MS

    def snapshot(self, samples):
        return {
            "start_ms": self.NOW_MS - 7 * DAY_MS,
            "end_ms": self.NOW_MS,
            "samples": samples,
            "sources_ok": ["WSL", "mini-1"],
            "issues": [],
        }

    def sample(self, recorded_at_ms, used_fraction, account_key="acct"):
        return {
            "recorded_at_ms": recorded_at_ms,
            "provider": "openai-codex",
            "account_key": account_key,
            "limit_id": "openai-codex:primary",
            "used_fraction": used_fraction,
        }

    def test_samples_from_every_account_key_join_one_series(self):
        snapshot = self.snapshot(
            [
                self.sample(self.NOW_MS - 3 * HOUR_MS, 0.10, "oauth|account:a"),
                self.sample(self.NOW_MS - 2 * HOUR_MS, 0.20, "oauth|account:a|email:x"),
                self.sample(self.NOW_MS - 1 * HOUR_MS, 0.30, "oauth|account:a|email:x|org:y"),
            ]
        )
        series = reporter.history_series(snapshot, "openai-codex", "openai-codex:primary")
        self.assertEqual(
            series,
            [
                (self.NOW_MS - 3 * HOUR_MS, 0.10),
                (self.NOW_MS - 2 * HOUR_MS, 0.20),
                (self.NOW_MS - 1 * HOUR_MS, 0.30),
            ],
        )

    def test_shared_quota_reported_twice_collapses_to_the_higher_fraction(self):
        snapshot = self.snapshot(
            [
                self.sample(self.NOW_MS - HOUR_MS, 0.61, "api_key|secret:one"),
                self.sample(self.NOW_MS - HOUR_MS, 0.64, "api_key|secret:two"),
            ]
        )
        series = reporter.history_series(snapshot, "openai-codex", "openai-codex:primary")
        self.assertEqual(series, [(self.NOW_MS - HOUR_MS, 0.64)])

    def test_burn_rate_uses_the_full_cross_account_series(self):
        series = reporter.history_series(
            self.snapshot(
                [
                    self.sample(self.NOW_MS - 24 * HOUR_MS, 0.0, "oauth|account:a"),
                    self.sample(self.NOW_MS - 12 * HOUR_MS, 0.12, "oauth|account:a|email:x"),
                ]
            ),
            "openai-codex",
            "openai-codex:primary",
        )
        rate = reporter.burn_rate(series, self.NOW_MS, 0.24, 24 * HOUR_MS)
        self.assertAlmostEqual(rate, 0.01, places=4)

    def test_other_providers_and_limits_are_excluded(self):
        snapshot = self.snapshot(
            [
                self.sample(self.NOW_MS - HOUR_MS, 0.10),
                {
                    "recorded_at_ms": self.NOW_MS - HOUR_MS,
                    "provider": "anthropic",
                    "account_key": "acct",
                    "limit_id": "openai-codex:primary",
                    "used_fraction": 0.99,
                },
                {
                    "recorded_at_ms": self.NOW_MS - HOUR_MS,
                    "provider": "openai-codex",
                    "account_key": "acct",
                    "limit_id": "openai-codex:spark:primary",
                    "used_fraction": 0.88,
                },
            ]
        )
        series = reporter.history_series(snapshot, "openai-codex", "openai-codex:primary")
        self.assertEqual(series, [(self.NOW_MS - HOUR_MS, 0.10)])


def forecast_shape(
    verdict="NO DATA",
    used=None,
    resets_at_ms=None,
    projected=None,
    exhaust_in_ms=None,
):
    return {
        "provider": "openai-codex",
        "limit_id": "openai-codex:primary",
        "label": "7 days",
        "used": used,
        "resets_at_ms": resets_at_ms,
        "window_ms": 7 * DAY_MS,
        "rate_per_hour": None,
        "projected": projected,
        "exhaust_in_ms": exhaust_in_ms,
        "verdict": verdict,
        "coupled_limit_id": None,
        "coupled_window_ms": None,
        "coupled_ratio": None,
        "coupled_burn": None,
        "coupled_room": None,
    }


class ForecastModelTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.now_ms = FIXED_NOW_MS

    def test_linear_usage_over_twenty_four_hours_projects_run_out(self):
        duration_ms = 7 * DAY_MS
        resets_at_ms = self.now_ms + 6 * DAY_MS
        series = [(self.now_ms - 24 * HOUR_MS, 0.0)]
        limit = forecast_limit(
            used_fraction=0.24,
            resets_at_ms=resets_at_ms,
            duration_ms=duration_ms,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertAlmostEqual(f["rate_per_hour"], 0.01, places=4)
        self.assertEqual(f["projected"], 1.0)
        self.assertEqual(f["verdict"], "RUN OUT")
        self.assertIsNotNone(f["exhaust_in_ms"])
        self.assertAlmostEqual(f["exhaust_in_ms"], 76 * HOUR_MS, delta=60_000)
        self.assertEqual(len(f["spark"]), 48)
        self.assertIsNone(f["spark"][0])
        self.assertTrue(any(v is not None for v in f["spark"]))

    def test_flat_history_verdict_is_spare(self):
        series = [(self.now_ms - 24 * HOUR_MS, 0.15)]
        limit = forecast_limit(
            used_fraction=0.15,
            resets_at_ms=self.now_ms + 24 * HOUR_MS,
            duration_ms=7 * DAY_MS,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertEqual(f["rate_per_hour"], 0.0)
        self.assertEqual(f["projected"], 0.15)
        self.assertIsNone(f["exhaust_in_ms"])
        self.assertEqual(f["verdict"], "SPARE")

    def test_reset_inside_lookback_uses_only_post_drop_samples(self):
        series = [
            (self.now_ms - 20 * HOUR_MS, 0.90),
            (self.now_ms - 10 * HOUR_MS, 0.05),
        ]
        limit = forecast_limit(
            used_fraction=0.15,
            resets_at_ms=self.now_ms + 48 * HOUR_MS,
            duration_ms=7 * DAY_MS,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertAlmostEqual(f["rate_per_hour"], 0.01, places=4)

    def test_used_at_one_is_exhausted(self):
        limit = forecast_limit(
            used_fraction=1.0,
            resets_at_ms=self.now_ms + 10 * HOUR_MS,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot([]), self.now_ms)
        self.assertEqual(f["verdict"], "EXHAUSTED")

    def test_history_span_under_one_hour_is_no_data(self):
        series = [(self.now_ms - 30 * 60 * 1_000, 0.10)]
        limit = forecast_limit(
            used_fraction=0.12,
            resets_at_ms=self.now_ms + 10 * HOUR_MS,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot(series), self.now_ms)
        self.assertIsNone(f["rate_per_hour"])
        self.assertEqual(f["verdict"], "NO DATA")

    def test_missing_used_fraction_is_no_data(self):
        limit = forecast_limit(
            used_fraction=None,
            resets_at_ms=self.now_ms + 10 * HOUR_MS,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot([]), self.now_ms)
        self.assertIsNone(f["used"])
        self.assertEqual(f["verdict"], "NO DATA")

    def test_short_window_duration_selects_short_lookback(self):
        duration_ms = 5 * HOUR_MS
        series = [
            (self.now_ms - 10 * HOUR_MS, 0.0),
            (self.now_ms - 2 * HOUR_MS, 0.10),
        ]
        limit = forecast_limit(
            used_fraction=0.20,
            resets_at_ms=self.now_ms + 3 * HOUR_MS,
            duration_ms=duration_ms,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertAlmostEqual(f["rate_per_hour"], 0.05, places=4)
        rate_text = reporter.fmt_rate(f)
        self.assertEqual(rate_text, "+5.0%/h")
        self.assertTrue(rate_text.endswith("%/h"))

    def test_projected_between_eighty_five_and_one_hundred_is_hot(self):
        series = [(self.now_ms - 24 * HOUR_MS, 0.0)]
        limit = forecast_limit(
            used_fraction=0.30,
            resets_at_ms=self.now_ms + 48 * HOUR_MS,
            duration_ms=7 * DAY_MS,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot(series), self.now_ms)
        self.assertEqual(f["verdict"], "HOT")
        self.assertAlmostEqual(f["projected"], 0.9, places=3)

    def test_projected_between_fifty_and_eighty_five_is_on_pace(self):
        series = [(self.now_ms - 24 * HOUR_MS, 0.0)]
        limit = forecast_limit(
            used_fraction=0.20,
            resets_at_ms=self.now_ms + 48 * HOUR_MS,
            duration_ms=7 * DAY_MS,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot(series), self.now_ms)
        self.assertEqual(f["verdict"], "ON PACE")
        self.assertAlmostEqual(f["projected"], 0.6, places=3)


class ForecastRowsTests(unittest.TestCase):
    NOW_MS = FIXED_NOW_MS

    def test_each_sorted_limit_yields_one_forecast_in_order(self):
        limits = [
            forecast_limit(limit_id="zai:early", label="Early", resets_at_ms=self.NOW_MS + 1_000_000),
            forecast_limit(limit_id="zai:late", label="Late", resets_at_ms=self.NOW_MS + 10_000_000),
        ]
        rows = reporter.forecast_rows("zai", limits, forecast_snapshot([]), self.NOW_MS)
        self.assertEqual([f["limit_id"] for f in rows], ["zai:early", "zai:late"])
        self.assertTrue(all(f["provider"] == "zai" for f in rows))
        self.assertTrue(all(f["verdict"] == "NO DATA" for f in rows))

    def test_empty_limits_yield_no_forecasts(self):
        self.assertEqual(
            reporter.forecast_rows("zai", [], forecast_snapshot([]), self.NOW_MS),
            [],
        )

    def test_short_window_couples_to_long_window_within_provider(self):
        limits = [
            forecast_limit(
                limit_id="anthropic:5h",
                label="Claude 5 Hour",
                used_fraction=0.46,
                resets_at_ms=self.NOW_MS + 2 * HOUR_MS,
                duration_ms=5 * HOUR_MS,
            ),
            forecast_limit(
                limit_id="anthropic:7d",
                label="Claude 7 Day",
                used_fraction=0.51,
                resets_at_ms=self.NOW_MS + 6 * DAY_MS,
                duration_ms=7 * DAY_MS,
            ),
        ]
        samples = [
            {
                "recorded_at_ms": self.NOW_MS - HOUR_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "anthropic:5h",
                "used_fraction": 0.00,
            },
            {
                "recorded_at_ms": self.NOW_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "anthropic:5h",
                "used_fraction": 0.50,
            },
            {
                "recorded_at_ms": self.NOW_MS - HOUR_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "anthropic:7d",
                "used_fraction": 0.10,
            },
            {
                "recorded_at_ms": self.NOW_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "anthropic:7d",
                "used_fraction": 0.20,
            },
        ]
        snapshot = {
            "start_ms": self.NOW_MS - 7 * DAY_MS,
            "end_ms": self.NOW_MS,
            "samples": samples,
            "sources_ok": ["WSL"],
            "issues": [],
        }
        rows = reporter.forecast_rows("anthropic", limits, snapshot, self.NOW_MS)
        short, long = rows
        self.assertEqual(short["limit_id"], "anthropic:5h")
        self.assertEqual(short["coupled_limit_id"], "anthropic:7d")
        self.assertAlmostEqual(short["coupled_ratio"], 0.2, places=3)
        self.assertIsNone(long["coupled_limit_id"])


class WindowCouplingTests(unittest.TestCase):
    NOW_MS = FIXED_NOW_MS
    HOUR_MS = HOUR_MS

    def coupled_snapshot(self, short_series, long_series, provider="anthropic", long_id="anthropic:7d"):
        samples = [
            {
                "recorded_at_ms": t,
                "provider": provider,
                "account_key": "acct",
                "limit_id": "anthropic:5h",
                "used_fraction": frac,
            }
            for t, frac in short_series
        ] + [
            {
                "recorded_at_ms": t,
                "provider": provider,
                "account_key": "acct",
                "limit_id": long_id,
                "used_fraction": frac,
            }
            for t, frac in long_series
        ]
        return {
            "start_ms": self.NOW_MS - 7 * DAY_MS,
            "end_ms": self.NOW_MS,
            "samples": samples,
            "sources_ok": ["WSL"],
            "issues": [],
        }

    def test_coupled_gain_ratio_pools_rising_intervals(self):
        short = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.10),
            (self.NOW_MS - self.HOUR_MS, 0.45),
            (self.NOW_MS, 0.76),
        ]
        long = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.20),
            (self.NOW_MS - self.HOUR_MS, 0.235),
            (self.NOW_MS, 0.266),
        ]
        ratio, support = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertAlmostEqual(ratio, 0.1, places=3)
        self.assertAlmostEqual(support, 0.66, places=3)

    def test_coupled_gain_ratio_pairs_samples_within_tolerance(self):
        short = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.00),
            (self.NOW_MS - self.HOUR_MS, 0.30),
            (self.NOW_MS, 0.60),
        ]
        long = [
            (self.NOW_MS - 2 * self.HOUR_MS + 60_000, 0.10),
            (self.NOW_MS - self.HOUR_MS - 60_000, 0.16),
            (self.NOW_MS + 60_000, 0.22),
        ]
        ratio, support = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertAlmostEqual(ratio, 0.2, places=3)
        self.assertAlmostEqual(support, 0.60, places=3)

    def test_coupled_gain_ratio_skips_reset_intervals(self):
        short = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.00),
            (self.NOW_MS - self.HOUR_MS, 0.40),
            (self.NOW_MS, 0.80),
        ]
        long = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.20),
            (self.NOW_MS - self.HOUR_MS, 0.10),
            (self.NOW_MS, 0.24),
        ]
        ratio, support = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertAlmostEqual(ratio, 0.35, places=3)
        self.assertAlmostEqual(support, 0.40, places=3)

    def test_coupled_gain_ratio_requires_minimum_support(self):
        short = [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.20)]
        long = [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.12)]
        ratio, support = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertIsNone(ratio)
        self.assertAlmostEqual(support, 0.10, places=3)

    def test_coupled_gain_ratio_rejects_ratio_above_one(self):
        short = [(self.NOW_MS - self.HOUR_MS, 0.00), (self.NOW_MS, 0.50)]
        long = [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.85)]
        ratio, _ = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertIsNone(ratio)

    def test_coupled_gain_ratio_rejects_flat_long_window(self):
        short = [
            (self.NOW_MS - self.HOUR_MS, 0.10),
            (self.NOW_MS, 0.60),
        ]
        long = [
            (self.NOW_MS - self.HOUR_MS, 0.01),
            (self.NOW_MS, 0.01),
        ]
        ratio, _ = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertIsNone(ratio)

    def test_pair_series_pairs_nearest_timestamp_within_tolerance(self):
        pairs = reporter.pair_series([(100, 0.5)], [(75, 0.05), (110, 0.9)], 30)
        self.assertEqual(pairs, [(100, 0.5, 0.9)])

    def test_coupled_gain_ratio_accepts_ratio_of_one(self):
        short = [(self.NOW_MS - self.HOUR_MS, 0.0), (self.NOW_MS, 0.3)]
        long = [(self.NOW_MS - self.HOUR_MS, 0.1), (self.NOW_MS, 0.4)]
        ratio, _ = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 1.0, places=6)

    def test_coupled_gain_ratio_skips_interval_with_hidden_dip(self):
        short = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.10),
            (self.NOW_MS - self.HOUR_MS, 0.02),
            (self.NOW_MS, 0.50),
        ]
        long = [
            (self.NOW_MS - 2 * self.HOUR_MS, 0.20),
            (self.NOW_MS, 0.26),
        ]
        ratio, support = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertIsNone(ratio)
        self.assertAlmostEqual(support, 0.0, places=3)

    def test_coupled_gain_ratio_skips_interval_longer_than_short_window(self):
        short = [(self.NOW_MS - 7 * self.HOUR_MS, 0.00), (self.NOW_MS, 0.50)]
        long = [(self.NOW_MS - 7 * self.HOUR_MS, 0.10), (self.NOW_MS, 0.20)]
        ratio, support = reporter.coupled_gain_ratio(short, long, 5 * self.HOUR_MS)
        self.assertIsNone(ratio)
        self.assertAlmostEqual(support, 0.0, places=3)

    def short_forecast(self, verdict="SPARE", used=0.24, **extra):
        f = forecast_shape(verdict=verdict, used=used, projected=used)
        f["provider"] = "anthropic"
        f["limit_id"] = "anthropic:5h"
        f["window_ms"] = 5 * self.HOUR_MS
        f.update(extra)
        return f

    def long_forecast(self, used=0.50, limit_id="anthropic:7d", projected=None):
        f = forecast_shape(verdict="ON PACE", used=used, projected=projected)
        f["provider"] = "anthropic"
        f["limit_id"] = limit_id
        f["window_ms"] = 7 * 24 * self.HOUR_MS
        return f

    def test_apply_window_coupling_prices_burn_and_keeps_spare_when_room_covers_it(self):
        short = self.short_forecast(used=0.24)
        long = self.long_forecast(used=0.50)
        snapshot = self.coupled_snapshot(
            [(self.NOW_MS - self.HOUR_MS, 0.00), (self.NOW_MS, 0.50)],
            [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.20)],
        )
        result = reporter.apply_window_coupling([short, long], snapshot)
        self.assertEqual(result[0]["coupled_limit_id"], "anthropic:7d")
        self.assertAlmostEqual(result[0]["coupled_ratio"], 0.2, places=3)
        self.assertAlmostEqual(result[0]["coupled_burn"], 0.2 * 0.76, places=3)
        self.assertAlmostEqual(result[0]["coupled_room"], 0.5, places=3)
        self.assertEqual(result[0]["verdict"], "SPARE")

    def test_apply_window_coupling_gates_when_burn_exceeds_room(self):
        short = self.short_forecast(used=0.24)
        long = self.long_forecast(used=0.90, projected=0.95)
        snapshot = self.coupled_snapshot(
            [(self.NOW_MS - self.HOUR_MS, 0.00), (self.NOW_MS, 0.50)],
            [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.20)],
        )
        result = reporter.apply_window_coupling([short, long], snapshot)
        self.assertEqual(result[0]["verdict"], "GATED")
        self.assertAlmostEqual(result[0]["coupled_burn"], 0.152, places=3)
        self.assertAlmostEqual(result[0]["coupled_room"], 0.05, places=3)

    def test_apply_window_coupling_prices_the_binding_long_window(self):
        def snapshot_with_two_longs():
            samples = []
            for limit_id, fractions in (
                ("anthropic:5h", (0.00, 0.50)),
                ("anthropic:7d", (0.10, 0.20)),
                ("anthropic:7d:fable", (0.10, 0.30)),
            ):
                samples.extend(
                    {
                        "recorded_at_ms": self.NOW_MS - self.HOUR_MS if index == 0 else self.NOW_MS,
                        "provider": "anthropic",
                        "account_key": "acct",
                        "limit_id": limit_id,
                        "used_fraction": fraction,
                    }
                    for index, fraction in enumerate(fractions)
                )
            return {
                "start_ms": self.NOW_MS - 7 * DAY_MS,
                "end_ms": self.NOW_MS,
                "samples": samples,
                "sources_ok": ["WSL"],
                "issues": [],
            }

        short = self.short_forecast(used=0.24)
        roomy = self.long_forecast(used=0.10, limit_id="anthropic:7d")
        tight = self.long_forecast(used=0.80, limit_id="anthropic:7d:fable")
        snapshot = snapshot_with_two_longs()
        for order in ([short, roomy, tight], [short, tight, roomy]):
            result = reporter.apply_window_coupling(list(order), snapshot)
            self.assertEqual(result[0]["coupled_limit_id"], "anthropic:7d:fable")
            self.assertAlmostEqual(result[0]["coupled_ratio"], 0.4, places=3)
            self.assertAlmostEqual(result[0]["coupled_burn"], 0.4 * 0.76, places=3)
            self.assertAlmostEqual(result[0]["coupled_room"], 0.2, places=3)
            self.assertEqual(result[0]["verdict"], "GATED")

    def test_apply_window_coupling_prefers_the_comoving_long_window(self):
        short = self.short_forecast(used=0.24)
        exhausted = self.long_forecast(used=1.0, limit_id="openai-codex:primary")
        comoving = self.long_forecast(used=0.40, limit_id="openai-codex:spark:secondary")
        samples = [
            {
                "recorded_at_ms": self.NOW_MS - self.HOUR_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "anthropic:5h",
                "used_fraction": 0.00,
            },
            {
                "recorded_at_ms": self.NOW_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "anthropic:5h",
                "used_fraction": 0.50,
            },
            {
                "recorded_at_ms": self.NOW_MS - self.HOUR_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "openai-codex:primary",
                "used_fraction": 1.0,
            },
            {
                "recorded_at_ms": self.NOW_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "openai-codex:primary",
                "used_fraction": 1.0,
            },
            {
                "recorded_at_ms": self.NOW_MS - self.HOUR_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "openai-codex:spark:secondary",
                "used_fraction": 0.10,
            },
            {
                "recorded_at_ms": self.NOW_MS,
                "provider": "anthropic",
                "account_key": "acct",
                "limit_id": "openai-codex:spark:secondary",
                "used_fraction": 0.20,
            },
        ]
        snapshot = {
            "start_ms": self.NOW_MS - 7 * DAY_MS,
            "end_ms": self.NOW_MS,
            "samples": samples,
            "sources_ok": ["WSL"],
            "issues": [],
        }
        result = reporter.apply_window_coupling([short, exhausted, comoving], snapshot)
        self.assertEqual(result[0]["coupled_limit_id"], "openai-codex:spark:secondary")

    def test_apply_window_coupling_skips_without_confident_ratio(self):
        short = self.short_forecast(used=0.24)
        long = self.long_forecast(used=0.50)
        snapshot = self.coupled_snapshot(
            [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.15)],
            [(self.NOW_MS - self.HOUR_MS, 0.10), (self.NOW_MS, 0.15)],
        )
        result = reporter.apply_window_coupling([short, long], snapshot)
        self.assertEqual(result[0]["verdict"], "SPARE")
        self.assertIsNone(result[0]["coupled_limit_id"])
        self.assertIsNone(result[0]["coupled_burn"])

    def test_fmt_window_short_labels_hours_days_and_unknown(self):
        self.assertEqual(reporter.fmt_window_short(5 * self.HOUR_MS), "5h")
        self.assertEqual(reporter.fmt_window_short(7 * 24 * self.HOUR_MS), "7d")
        self.assertEqual(reporter.fmt_window_short(None), "long")
        self.assertEqual(reporter.fmt_window_short(0), "long")


class FmtDurationTests(unittest.TestCase):
    def test_zero_and_negative_durations_read_as_now(self):
        self.assertEqual(reporter.fmt_duration(0), "~now")
        self.assertEqual(reporter.fmt_duration(-1), "~now")
        self.assertEqual(reporter.fmt_duration(-HOUR_MS), "~now")

    def test_minute_boundaries_round_up_to_singular_and_plural(self):
        self.assertEqual(reporter.fmt_duration(60_000), "~in 1 minute")
        self.assertEqual(reporter.fmt_duration(120_000), "~in 2 minutes")
        self.assertEqual(reporter.fmt_duration(3_599_000), "~in 60 minutes")

    def test_hour_boundaries_round_up_to_singular_and_plural(self):
        self.assertEqual(reporter.fmt_duration(3_600_000), "~in 1 hour")
        self.assertEqual(reporter.fmt_duration(7_200_000), "~in 2 hours")

    def test_day_boundaries_round_up_to_singular_and_plural(self):
        self.assertEqual(reporter.fmt_duration(DAY_MS), "~in 1 day")
        self.assertEqual(reporter.fmt_duration(2 * DAY_MS), "~in 2 days")

    def test_reset_estimate_three_hours_out_matches_duration_text(self):
        resets_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + 3 * HOUR_MS
        self.assertEqual(reporter.fmt_reset_estimate(resets_at_ms), "~in 3 hours")
        self.assertEqual(reporter.fmt_reset_estimate(resets_at_ms), reporter.fmt_duration(3 * HOUR_MS))


class ForecastAdviceTests(unittest.TestCase):
    NOW_MS = FIXED_NOW_MS

    def test_run_out_advice_counts_exhaustion_and_gap_before_reset(self):
        shape = forecast_shape(
            verdict="RUN OUT",
            used=0.5,
            resets_at_ms=self.NOW_MS + 7 * DAY_MS,
            projected=1.0,
            exhaust_in_ms=5 * DAY_MS,
        )
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "tone it down · hits 100% ~in 5 days, ~in 2 days before reset",
        )

    def test_run_out_advice_clamps_gap_before_reset_at_now(self):
        shape = forecast_shape(
            verdict="RUN OUT",
            used=0.5,
            resets_at_ms=self.NOW_MS + 2 * DAY_MS,
            projected=1.0,
            exhaust_in_ms=5 * DAY_MS,
        )
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "tone it down · hits 100% ~in 5 days, ~now before reset",
        )

    def test_advice_uses_passed_now_not_wall_clock(self):
        now_ms = 1_600_000_000_000
        shape = forecast_shape(
            verdict="RUN OUT",
            used=0.5,
            resets_at_ms=now_ms + 7 * DAY_MS,
            projected=1.0,
            exhaust_in_ms=5 * DAY_MS,
        )
        self.assertEqual(
            reporter.forecast_advice(shape, now_ms),
            "tone it down · hits 100% ~in 5 days, ~in 2 days before reset",
        )

    def test_exhausted_advice_names_reset_three_days_out(self):
        resets_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + 3 * DAY_MS
        shape = forecast_shape(verdict="EXHAUSTED", used=1.0, resets_at_ms=resets_at_ms)
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "exhausted · wait, resets ~in 3 days",
        )

    def test_exhausted_advice_without_reset_time_is_bare_wait(self):
        shape = forecast_shape(verdict="EXHAUSTED", used=1.0, resets_at_ms=None)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "exhausted · wait")

    def test_hot_advice_reports_projected_percent(self):
        shape = forecast_shape(verdict="HOT", used=0.7, projected=0.92)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "ease off · ~92% by reset")

    def test_on_pace_advice_reports_projected_percent(self):
        shape = forecast_shape(verdict="ON PACE", used=0.5, projected=0.69)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "keep going · ~69% by reset")

    def test_spare_advice_reports_spare_percent(self):
        shape = forecast_shape(verdict="SPARE", used=0.24, projected=0.24)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "crank it up · ~76% spare by reset")

    def test_no_data_without_usage_reports_no_usage(self):
        self.assertEqual(reporter.forecast_advice(forecast_shape(), self.NOW_MS), "no usage reported")

    def test_no_data_with_usage_reports_insufficient_history(self):
        shape = forecast_shape(used=0.3)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "not enough history yet")

    def test_spare_advice_appends_long_window_cost(self):
        shape = forecast_shape(verdict="SPARE", used=0.24, projected=0.24)
        shape["coupled_burn"] = 0.076
        shape["coupled_window_ms"] = 7 * DAY_MS
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "crank it up · ~76% spare by reset · ~8% of 7d",
        )

    def test_on_pace_advice_appends_long_window_cost(self):
        shape = forecast_shape(verdict="ON PACE", used=0.5, projected=0.69)
        shape["coupled_burn"] = 0.076
        shape["coupled_window_ms"] = 7 * DAY_MS
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "keep going · ~69% by reset · ~8% of 7d",
        )

    def test_gated_advice_reports_burn_and_room(self):
        shape = forecast_shape(verdict="GATED", used=0.24)
        shape["coupled_burn"] = 0.38
        shape["coupled_room"] = 0.2
        shape["coupled_window_ms"] = 7 * DAY_MS
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "7d gates it · full burn ~38%, room ~20%",
        )


if __name__ == "__main__":
    unittest.main()
