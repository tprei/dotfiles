import contextlib
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

class CollectTokenSnapshotWindowTests(unittest.TestCase):
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

        self.assertEqual(requested_windows, [("WSL", start_ms, now_ms), ("mini-1", start_ms, now_ms)])
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

class CollectHistorySnapshotTests(unittest.TestCase):
    def test_history_window_covers_seven_days_ending_now(self):
        now_ms = 1_789_000_000_000
        start_ms = now_ms - 7 * 86_400_000
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

        self.assertEqual(requested_windows, [("WSL", start_ms, now_ms), ("mini-1", start_ms, now_ms)])
        self.assertEqual(snapshot["start_ms"], start_ms)
        self.assertEqual(snapshot["end_ms"], now_ms)
        self.assertEqual(snapshot["sources_ok"], ["WSL", "mini-1"])
        self.assertEqual(snapshot["samples"], [wsl_sample, mini_sample])
        self.assertEqual(snapshot["issues"], [])

    def test_unconfigured_ssh_host_yields_issue_and_keeps_local_samples(self):
        now_ms = 1_789_000_000_000
        start_ms = now_ms - 7 * 86_400_000
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
        self.assertEqual(snapshot["issues"], ["mini-1 unconfigured"])
        self.assertEqual(snapshot["sources_ok"], ["WSL"])
        self.assertEqual(snapshot["samples"], [wsl_sample])

    def test_remote_failure_issue_precedes_merge_issues(self):
        now_ms = 1_789_000_000_000
        start_ms = now_ms - 7 * 86_400_000
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

        with mock.patch.object(reporter, "check_ssh_host", return_value="mini-1"), mock.patch.object(
            reporter, "collector_source", side_effect=reporter.UsageError("collector unreadable: x", 1)
        ), mock.patch.object(reporter, "remote_collection") as remote:
            collections, issues = reporter.gather_collections(
                HISTORY_PATH, local_history, HISTORY_START_MS, HISTORY_END_MS
            )

        remote.assert_not_called()
        self.assertEqual(collections, [("WSL", local)])
        self.assertEqual(issues, ["mini-1 unavailable: collector unreadable"])


class ReporterTelegramStateTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="omp-token-state-")
        self.addCleanup(temporary.cleanup)
        self.state_path = Path(temporary.name) / "state.json"
        state_patcher = mock.patch.object(reporter, "CODEX_STATE_PATH", self.state_path)
        state_patcher.start()
        self.addCleanup(state_patcher.stop)
        self.config = {"bot_token": "unit-test-token", "chat_id": "42"}
        self.limits_image = b"unit-limits-image"
        self.token_image = b"unit-token-image"

    def write_state(self, state):
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self):
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def telegram_http_error(self, description, code=400):
        body = json.dumps({"ok": False, "error_code": code, "description": description})
        return urllib.error.HTTPError(
            "https://api.telegram.org/bot-unit-test/method",
            code,
            description,
            {"Content-Type": "application/json"},
            io.BytesIO(body.encode("utf-8")),
        )

    def test_edit_success_pins_existing_message_without_resend(self):
        self.write_state({"message_id": 111, "tokens_message_id": 42})
        with mock.patch.object(reporter, "tg_send_photo") as send, \
                mock.patch.object(reporter, "tg_edit_photo") as edit, \
                mock.patch.object(reporter, "tg_pin") as pin:
            self.assertTrue(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_not_called()
        edit.assert_called_once()
        pin.assert_called_once()
        self.assertEqual(call_arg(pin.call_args, 1, "message_id"), 42)
        self.assertEqual(self.read_state(), {"message_id": 111, "tokens_message_id": 42})

    def test_message_not_modified_counts_as_success(self):
        self.write_state({"tokens_message_id": 42})
        with mock.patch.object(reporter, "tg_send_photo") as send, \
                mock.patch.object(
                    reporter,
                    "tg_edit_photo",
                    side_effect=[self.telegram_http_error("Bad Request: message is not modified")],
                ), \
                mock.patch.object(reporter, "tg_pin"):
            self.assertTrue(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_not_called()
        self.assertEqual(self.read_state(), {"tokens_message_id": 42})

    def test_missing_message_replaces_only_that_state_key(self):
        self.write_state({"message_id": 111, "tokens_message_id": 42, "note": "keep"})
        with mock.patch.object(reporter, "tg_send_photo", return_value=555) as send, \
                mock.patch.object(
                    reporter,
                    "tg_edit_photo",
                    side_effect=[self.telegram_http_error("Bad Request: message to edit not found")],
                ) as edit, \
                mock.patch.object(reporter, "tg_pin") as pin, \
                mock.patch.object(reporter, "tg_delete") as delete:
            self.assertTrue(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_called_once()
        edit.assert_called_once()
        pin.assert_called_once()
        self.assertEqual(call_arg(pin.call_args, 1, "message_id"), 555)
        delete.assert_called_once()
        self.assertEqual(call_arg(delete.call_args, 1, "message_id"), 42)
        self.assertEqual(
            self.read_state(),
            {"message_id": 111, "note": "keep", "tokens_message_id": 555},
        )

    def test_generic_400_keeps_saved_id_without_duplicate_photo(self):
        self.write_state({"tokens_message_id": 42})
        with mock.patch.object(reporter, "tg_send_photo") as send, \
                mock.patch.object(
                    reporter,
                    "tg_edit_photo",
                    side_effect=[self.telegram_http_error("Bad Request: chat not found")],
                ), \
                mock.patch.object(reporter, "tg_pin") as pin:
            self.assertFalse(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_not_called()
        pin.assert_not_called()
        self.assertEqual(self.read_state(), {"tokens_message_id": 42})

    def test_other_telegram_failure_keeps_saved_id(self):
        self.write_state({"tokens_message_id": 42})
        with mock.patch.object(reporter, "tg_send_photo") as send, \
                mock.patch.object(
                    reporter,
                    "tg_edit_photo",
                    side_effect=[reporter.TelegramError("Telegram editMessageMedia failed: busy")],
                ), \
                mock.patch.object(reporter, "tg_pin"):
            self.assertFalse(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_not_called()
        self.assertEqual(self.read_state(), {"tokens_message_id": 42})

    def test_pin_failure_on_edit_retains_saved_id(self):
        self.write_state({"tokens_message_id": 42})
        with mock.patch.object(reporter, "tg_send_photo") as send, \
                mock.patch.object(reporter, "tg_edit_photo"), \
                mock.patch.object(
                    reporter,
                    "tg_pin",
                    side_effect=[reporter.TelegramError("Telegram pinChatMessage failed: no rights")],
                ):
            self.assertFalse(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_not_called()
        self.assertEqual(self.read_state(), {"tokens_message_id": 42})

    def test_pin_failure_after_replacement_still_saves_new_id(self):
        self.write_state({"message_id": 111})
        with mock.patch.object(reporter, "tg_send_photo", return_value=555) as send, \
                mock.patch.object(reporter, "tg_edit_photo") as edit, \
                mock.patch.object(
                    reporter,
                    "tg_pin",
                    side_effect=[reporter.TelegramError("Telegram pinChatMessage failed: no rights")],
                ), \
                mock.patch.object(reporter, "tg_delete") as delete:
            self.assertFalse(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        edit.assert_not_called()
        send.assert_called_once()
        delete.assert_not_called()
        self.assertEqual(self.read_state(), {"message_id": 111, "tokens_message_id": 555})

    def test_state_keys_stay_independent_per_image(self):
        self.write_state({"tokens_message_id": 42})
        with mock.patch.object(reporter, "tg_send_photo", return_value=900) as send, \
                mock.patch.object(reporter, "tg_edit_photo") as edit, \
                mock.patch.object(reporter, "tg_pin"):
            self.assertTrue(reporter.update_pinned(self.config, self.limits_image, "message_id"))
            self.assertTrue(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_called_once()
        edit.assert_called_once()
        self.assertEqual(call_arg(edit.call_args, 1, "message_id"), 42)
        self.assertEqual(self.read_state(), {"message_id": 900, "tokens_message_id": 42})


class PublishImagesTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.config = {"bot_token": "unit-test-token", "chat_id": "42"}
        limits_patcher = mock.patch.object(reporter, "build_image", return_value=(b"limits-image", 0))
        token_patcher = mock.patch.object(reporter, "build_token_image", return_value=(b"token-image", 0))
        forecast_patcher = mock.patch.object(
            reporter, "build_forecast_image", return_value=(b"forecast-image", 0)
        )
        usage_patcher = mock.patch.object(
            reporter, "run_omp_usage", return_value={"reports": [{"provider": "zai", "limits": []}]}
        )
        update_patcher = mock.patch.object(reporter, "update_pinned", return_value=True)
        announce_patcher = mock.patch.object(reporter, "announce_window_resets", return_value=0)
        failure_patcher = mock.patch.object(
            reporter, "fail", side_effect=lambda error: getattr(error, "exit_code", 2)
        )
        self.build_limits = limits_patcher.start()
        self.build_tokens = token_patcher.start()
        self.build_forecast = forecast_patcher.start()
        self.run_usage = usage_patcher.start()
        self.update = update_patcher.start()
        self.announce = announce_patcher.start()
        self.failure = failure_patcher.start()
        self.addCleanup(limits_patcher.stop)
        self.addCleanup(token_patcher.stop)
        self.addCleanup(forecast_patcher.stop)
        self.addCleanup(usage_patcher.stop)
        self.addCleanup(update_patcher.stop)
        self.addCleanup(announce_patcher.stop)
        self.addCleanup(failure_patcher.stop)

    def published(self):
        return sorted(
            (call_arg(call, 1, "image"), call_arg(call, 2, "state_key"))
            for call in self.update.call_args_list
        )

    def published_in_order(self):
        return [
            (call_arg(call, 1, "image"), call_arg(call, 2, "state_key"))
            for call in self.update.call_args_list
        ]

    def test_publishes_every_image_in_order_with_independent_state_keys(self):
        self.assertEqual(reporter.publish_images(self.config), 0)
        self.assertEqual(
            self.published_in_order(),
            [
                (b"limits-image", "message_id"),
                (b"token-image", "tokens_message_id"),
                (b"forecast-image", "forecast_message_id"),
            ],
        )
        self.failure.assert_not_called()
        self.announce.assert_called_once_with(
            self.config, {"reports": [{"provider": "zai", "limits": []}]}
        )

    def test_reset_announcement_failure_exits_two(self):
        self.announce.return_value = 2
        self.assertEqual(reporter.publish_images(self.config), 2)

    def test_quota_failure_still_publishes_token_chart(self):
        self.run_usage.side_effect = reporter.UsageError("omp usage unavailable", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(self.published(), [(b"token-image", "tokens_message_id")])
        self.failure.assert_called_once()

    def test_token_collection_failure_still_publishes_limits(self):
        self.build_tokens.side_effect = reporter.UsageError("mini-1 unavailable", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(
            self.published(),
            [(b"forecast-image", "forecast_message_id"), (b"limits-image", "message_id")],
        )
        self.failure.assert_called_once()

    def test_incomplete_token_snapshot_publishes_with_warning_exit(self):
        self.build_tokens.return_value = (b"token-image", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(
            self.published(),
            [
                (b"forecast-image", "forecast_message_id"),
                (b"limits-image", "message_id"),
                (b"token-image", "tokens_message_id"),
            ],
        )

    def test_unrecovered_tool_error_exits_one(self):
        self.build_limits.side_effect = reporter.UsageError("no provider reports", 1)
        self.assertEqual(reporter.publish_images(self.config), 1)
        self.assertEqual(
            self.published(),
            [(b"forecast-image", "forecast_message_id"), (b"token-image", "tokens_message_id")],
        )

    def test_failed_publication_exits_two_and_attempts_every_image(self):
        self.update.side_effect = lambda config, image, state_key: state_key == "message_id"
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(len(self.update.call_args_list), 3)
        self.assertEqual(
            self.published(),
            [
                (b"forecast-image", "forecast_message_id"),
                (b"limits-image", "message_id"),
                (b"token-image", "tokens_message_id"),
            ],
        )

    def test_forecast_failure_still_publishes_limits_and_tokens(self):
        self.build_forecast.side_effect = reporter.UsageError("history unavailable", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(
            self.published(),
            [(b"limits-image", "message_id"), (b"token-image", "tokens_message_id")],
        )
        self.failure.assert_called_once()

    def test_payload_failure_skips_limits_and_forecast(self):
        self.run_usage.side_effect = reporter.UsageError("omp usage unavailable", 2)
        reporter.publish_images(self.config)
        self.build_limits.assert_not_called()
        self.build_forecast.assert_not_called()

    def test_run_json_prints_quota_payload_unchanged(self):
        payload = {"reports": [{"provider": "zai", "limits": []}]}
        with mock.patch.object(reporter, "run_omp_usage", return_value=payload), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(reporter.run_json(), 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)

    def test_run_telegram_requires_configured_credentials(self):
        with mock.patch.object(reporter, "load_config", return_value=None), \
                mock.patch.object(reporter, "publish_images") as publish:
            self.assertEqual(reporter.run_telegram(), 1)
        publish.assert_not_called()

    def test_run_telegram_delegates_to_publication(self):
        with mock.patch.object(reporter, "load_config", return_value=self.config), \
                mock.patch.object(reporter, "publish_images", return_value=0) as publish:
            self.assertEqual(reporter.run_telegram(), 0)
        publish.assert_called_once_with(self.config)

    def test_setup_telegram_delegates_after_validating_bot(self):
        with mock.patch.object(reporter, "load_config", return_value=self.config), \
                mock.patch.object(
                    reporter, "tg_call", return_value={"ok": True, "result": {"username": "unitbot"}}
                ) as get_me, \
                mock.patch.object(reporter, "publish_images", return_value=0) as publish, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reporter.setup_telegram(), 0)
        self.assertEqual(call_arg(get_me.call_args, 1, "method"), "getMe")
        publish.assert_called_once_with(self.config)

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
    return {"id": limit_id, "label": label, "window": window, "amount": amount, "status": "ok"}


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
    NOW_MS = 1_789_000_000_000

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
        resets = self.NOW_MS + 7 * 86_400_000 if resets_at_ms is None else resets_at_ms
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
        same = self.NOW_MS + 7 * 86_400_000
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
            current[key] = dict(previous[key], resets_at_ms=self.NOW_MS + 86_400_000, used=0.0)
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
            "resets_at_ms": 1_789_000_000_000 + 7 * 86_400_000,
            "fresh_used": 0.0,
        }
        event.update(overrides)
        return event

    def test_caption_marks_weekly_reset_with_closed_usage(self):
        caption = reporter.reset_caption([self.event()])
        self.assertIn("🎉 <b>Weekly limit reset</b>", caption)
        self.assertIn("<b>OpenAI Codex</b>", caption)
        self.assertIn("closed at <b>100.0%</b> used", caption)
        self.assertIn("fresh window resets <b>", caption)

    def test_caption_titles_follow_the_announced_kinds(self):
        self.assertIn(
            "<b>Monthly limit reset</b>",
            reporter.reset_caption([self.event(kind="monthly")]),
        )
        self.assertIn(
            "<b>Limit resets</b>",
            reporter.reset_caption([self.event(), self.event(kind="monthly", provider="zai", label="Monthly")]),
        )

    def test_caption_appends_request_amounts_when_available(self):
        caption = reporter.reset_caption([self.event(amount_text="940/1,000 requests")])
        self.assertIn("(940/1,000 requests)", caption)

    def test_image_text_is_plain_and_shows_fresh_capacity(self):
        text = reporter.reset_image_text([self.event(fresh_used=0.01)])
        self.assertIn("OpenAI Codex", text)
        self.assertIn("7 days · fresh window", text)
        self.assertIn("99% free · resets", text)
        self.assertIn("closed at 100.0% used", text)
        self.assertNotIn("<b>", text)

    def test_caption_never_exceeds_the_telegram_limit(self):
        providers = ("anthropic", "google-antigravity", "openai-codex", "opencode-go", "zai")
        events = [
            self.event(provider=provider, label=f"Long limit name {index} of {provider}")
            for provider in providers
            for index in range(3)
        ]
        caption = reporter.reset_caption(events)
        self.assertLessEqual(len(caption), 1024)
        self.assertRegex(caption, r"\n\+\d+ more$")
        self.assertNotIn("2 of zai", caption)

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


class ResetAnnouncementTests(unittest.TestCase):
    KEY = "openai-codex:0:openai-codex:primary"

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="omp-reset-state-")
        self.addCleanup(temporary.cleanup)
        self.state_path = Path(temporary.name) / "state.json"
        state_patcher = mock.patch.object(reporter, "CODEX_STATE_PATH", self.state_path)
        state_patcher.start()
        self.addCleanup(state_patcher.stop)
        self.config = {"bot_token": "unit-test-token", "chat_id": "42"}

    def write_state(self, state):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def read_watch(self):
        return self.read_state().get("reset_watch")

    def payload(self, used_fraction=0.0, resets_offset_ms=7 * 86_400_000):
        return usage_payload(
            limits=[
                window_limit(
                    resets_at_ms=1_789_000_000_000 + resets_offset_ms,
                    used_fraction=used_fraction,
                )
            ]
        )

    def closed_watch(self):
        return {
            self.KEY: {
                "provider": "openai-codex",
                "kind": "weekly",
                "label": "7 days",
                "amount_text": "",
                "resets_at_ms": 1_789_000_000_000 - 3_600_000,
                "used": 1.0,
                "seen_at_ms": 1_789_000_000_000 - 300_000,
            }
        }

    def test_tracked_label_prefers_limit_label_over_window_label(self):
        limit = window_limit(
            limit_id="anthropic:7d:fable",
            label="Claude 7 Day (Fable)",
            window_label="7 Day",
            resets_at_ms=1_789_000_000_000 + 7 * 86_400_000,
        )
        tracked = reporter.tracked_window_limits(
            usage_payload(provider="anthropic", limits=[limit]), 1_789_000_000_000
        )
        self.assertEqual(tracked["anthropic:0:anthropic:7d:fable"]["label"], "Claude 7 Day (Fable)")

    def test_accounts_with_shared_limit_ids_are_not_tracked(self):
        spent = window_limit(
            limit_id="weekly",
            label="Weekly limit",
            window_label="Weekly",
            resets_at_ms=1_789_000_000_000 + 2 * 86_400_000,
            used_fraction=1.0,
        )
        fresh = window_limit(
            limit_id="weekly",
            label="Weekly limit",
            window_label="Weekly",
            resets_at_ms=1_789_000_000_000 + 7 * 86_400_000,
            used_fraction=0.0,
        )
        shared = {"reports": [{"provider": "opencode-go", "limits": [spent]}, {"provider": "opencode-go", "limits": [fresh]}]}
        self.assertEqual(reporter.tracked_window_limits(shared, 1_789_000_000_000), {})
        distinct = {
            "reports": [
                {"provider": "opencode-go", "limits": [spent]},
                {"provider": "opencode-go", "limits": [dict(fresh, id="monthly")]},
            ]
        }
        tracked = reporter.tracked_window_limits(distinct, 1_789_000_000_000)
        self.assertEqual(sorted(tracked), ["opencode-go:0:weekly", "opencode-go:1:monthly"])
        self.assertEqual(tracked["opencode-go:0:weekly"]["used"], 1.0)
        self.assertEqual(tracked["opencode-go:1:monthly"]["used"], 0.0)

    def test_first_run_records_baseline_without_sending(self):
        with mock.patch.object(reporter, "tg_send_photo") as send:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        send.assert_not_called()
        watch = self.read_watch()
        self.assertEqual(list(watch), [self.KEY])
        self.assertEqual(watch[self.KEY]["used"], 0.0)
        self.assertEqual(watch[self.KEY]["kind"], "weekly")

    def test_window_rollover_sends_reset_message_and_updates_watch(self):
        self.write_state({"message_id": 5, "reset_watch": self.closed_watch()})
        with mock.patch.object(reporter, "build_reset_image", return_value=b"reset-image") as build, \
                mock.patch.object(reporter, "tg_send_photo", return_value=123) as send:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        build.assert_called_once()
        send.assert_called_once()
        self.assertEqual(call_arg(send.call_args, 1, "image"), b"reset-image")
        caption = call_arg(send.call_args, 2, "caption")
        self.assertIn("Weekly limit reset", caption)
        self.assertIn("OpenAI Codex", caption)
        self.assertEqual(self.read_watch()[self.KEY]["resets_at_ms"], 1_789_000_000_000 + 7 * 86_400_000)
        self.assertEqual(self.read_state()["message_id"], 5)

    def test_failed_send_returns_two_and_retries_next_run(self):
        self.write_state({"reset_watch": self.closed_watch()})
        with mock.patch.object(reporter, "build_reset_image", return_value=b"reset-image"), \
                mock.patch.object(
                    reporter, "tg_send_photo", side_effect=reporter.TelegramError("sendPhoto failed")
                ) as send:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 2)
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 2)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(self.read_watch(), self.closed_watch())

    def test_below_floor_rollover_updates_watch_without_sending(self):
        watch = self.closed_watch()
        watch[self.KEY]["used"] = 0.03
        self.write_state({"reset_watch": watch})
        with mock.patch.object(reporter, "tg_send_photo") as send:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        send.assert_not_called()
        self.assertEqual(self.read_watch()[self.KEY]["used"], 0.0)

    def test_short_windows_are_not_tracked(self):
        limit = window_limit(
            limit_id="zai:tokens:5h",
            label="ZAI 5 Hours Token Quota",
            window_label="5 Hours",
            window_id="5h",
            duration_ms=18_000_000,
            resets_at_ms=1_789_000_000_000 + 3_600_000,
            used_fraction=0.5,
        )
        with mock.patch.object(reporter, "tg_send_photo") as send:
            self.assertEqual(
                reporter.announce_window_resets(self.config, usage_payload(provider="zai", limits=[limit])),
                0,
            )
        send.assert_not_called()
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
        with mock.patch.object(reporter, "tg_send_photo") as send:
            self.assertEqual(reporter.announce_window_resets(self.config, self.payload()), 0)
        send.assert_not_called()
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
    NOW_MS = 1_789_000_000_000

    def snapshot(self, samples):
        return {
            "start_ms": self.NOW_MS - 7 * 86_400_000,
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
                self.sample(self.NOW_MS - 3 * 3_600_000, 0.10, "oauth|account:a"),
                self.sample(self.NOW_MS - 2 * 3_600_000, 0.20, "oauth|account:a|email:x"),
                self.sample(self.NOW_MS - 1 * 3_600_000, 0.30, "oauth|account:a|email:x|org:y"),
            ]
        )
        series = reporter.history_series(snapshot, "openai-codex", "openai-codex:primary")
        self.assertEqual(
            series,
            [
                (self.NOW_MS - 3 * 3_600_000, 0.10),
                (self.NOW_MS - 2 * 3_600_000, 0.20),
                (self.NOW_MS - 1 * 3_600_000, 0.30),
            ],
        )

    def test_shared_quota_reported_twice_collapses_to_the_higher_fraction(self):
        snapshot = self.snapshot(
            [
                self.sample(self.NOW_MS - 3_600_000, 0.61, "api_key|secret:one"),
                self.sample(self.NOW_MS - 3_600_000, 0.64, "api_key|secret:two"),
            ]
        )
        series = reporter.history_series(snapshot, "openai-codex", "openai-codex:primary")
        self.assertEqual(series, [(self.NOW_MS - 3_600_000, 0.64)])

    def test_burn_rate_uses_the_full_cross_account_series(self):
        series = reporter.history_series(
            self.snapshot(
                [
                    self.sample(self.NOW_MS - 24 * 3_600_000, 0.0, "oauth|account:a"),
                    self.sample(self.NOW_MS - 12 * 3_600_000, 0.12, "oauth|account:a|email:x"),
                ]
            ),
            "openai-codex",
            "openai-codex:primary",
        )
        rate = reporter.burn_rate(series, self.NOW_MS, 0.24, 24 * 3_600_000)
        self.assertAlmostEqual(rate, 0.01, places=4)

    def test_other_providers_and_limits_are_excluded(self):
        snapshot = self.snapshot(
            [
                self.sample(self.NOW_MS - 3_600_000, 0.10),
                {
                    "recorded_at_ms": self.NOW_MS - 3_600_000,
                    "provider": "anthropic",
                    "account_key": "acct",
                    "limit_id": "openai-codex:primary",
                    "used_fraction": 0.99,
                },
                {
                    "recorded_at_ms": self.NOW_MS - 3_600_000,
                    "provider": "openai-codex",
                    "account_key": "acct",
                    "limit_id": "openai-codex:spark:primary",
                    "used_fraction": 0.88,
                },
            ]
        )
        series = reporter.history_series(snapshot, "openai-codex", "openai-codex:primary")
        self.assertEqual(series, [(self.NOW_MS - 3_600_000, 0.10)])


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
        "window_ms": 7 * 24 * 3_600_000,
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
        self.now_ms = 1_789_000_000_000

    def test_linear_usage_over_twenty_four_hours_projects_run_out(self):
        duration_ms = 7 * 24 * 3_600_000
        resets_at_ms = self.now_ms + 6 * 24 * 3_600_000
        series = [(self.now_ms - 24 * 3_600_000, 0.0)]
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
        self.assertAlmostEqual(f["exhaust_in_ms"], 76 * 3_600_000, delta=60_000)
        self.assertEqual(len(f["spark"]), 48)
        self.assertIsNone(f["spark"][0])
        self.assertTrue(any(v is not None for v in f["spark"]))

    def test_flat_history_verdict_is_spare(self):
        series = [(self.now_ms - 24 * 3_600_000, 0.15)]
        limit = forecast_limit(
            used_fraction=0.15,
            resets_at_ms=self.now_ms + 24 * 3_600_000,
            duration_ms=7 * 24 * 3_600_000,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertEqual(f["rate_per_hour"], 0.0)
        self.assertEqual(f["projected"], 0.15)
        self.assertIsNone(f["exhaust_in_ms"])
        self.assertEqual(f["verdict"], "SPARE")

    def test_reset_inside_lookback_uses_only_post_drop_samples(self):
        series = [
            (self.now_ms - 20 * 3_600_000, 0.90),
            (self.now_ms - 10 * 3_600_000, 0.05),
        ]
        limit = forecast_limit(
            used_fraction=0.15,
            resets_at_ms=self.now_ms + 48 * 3_600_000,
            duration_ms=7 * 24 * 3_600_000,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertAlmostEqual(f["rate_per_hour"], 0.01, places=4)

    def test_used_at_one_is_exhausted(self):
        limit = forecast_limit(
            used_fraction=1.0,
            resets_at_ms=self.now_ms + 10 * 3_600_000,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot([]), self.now_ms)
        self.assertEqual(f["verdict"], "EXHAUSTED")

    def test_history_span_under_one_hour_is_no_data(self):
        series = [(self.now_ms - 30 * 60 * 1_000, 0.10)]
        limit = forecast_limit(
            used_fraction=0.12,
            resets_at_ms=self.now_ms + 10 * 3_600_000,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot(series), self.now_ms)
        self.assertIsNone(f["rate_per_hour"])
        self.assertEqual(f["verdict"], "NO DATA")

    def test_missing_used_fraction_is_no_data(self):
        limit = forecast_limit(
            used_fraction=None,
            resets_at_ms=self.now_ms + 10 * 3_600_000,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot([]), self.now_ms)
        self.assertIsNone(f["used"])
        self.assertEqual(f["verdict"], "NO DATA")

    def test_short_window_duration_selects_short_lookback(self):
        duration_ms = 5 * 3_600_000
        series = [
            (self.now_ms - 10 * 3_600_000, 0.0),
            (self.now_ms - 2 * 3_600_000, 0.10),
        ]
        limit = forecast_limit(
            used_fraction=0.20,
            resets_at_ms=self.now_ms + 3 * 3_600_000,
            duration_ms=duration_ms,
        )
        snapshot = forecast_snapshot(series)
        f = reporter.build_forecast(limit, "openai-codex", snapshot, self.now_ms)
        self.assertAlmostEqual(f["rate_per_hour"], 0.05, places=4)
        rate_text = reporter.fmt_rate(f)
        self.assertEqual(rate_text, "+5.0%/h")
        self.assertTrue(rate_text.endswith("%/h"))

    def test_projected_between_eighty_five_and_one_hundred_is_hot(self):
        series = [(self.now_ms - 24 * 3_600_000, 0.0)]
        limit = forecast_limit(
            used_fraction=0.30,
            resets_at_ms=self.now_ms + 48 * 3_600_000,
            duration_ms=7 * 24 * 3_600_000,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot(series), self.now_ms)
        self.assertEqual(f["verdict"], "HOT")
        self.assertAlmostEqual(f["projected"], 0.9, places=3)

    def test_projected_between_fifty_and_eighty_five_is_on_pace(self):
        series = [(self.now_ms - 24 * 3_600_000, 0.0)]
        limit = forecast_limit(
            used_fraction=0.20,
            resets_at_ms=self.now_ms + 48 * 3_600_000,
            duration_ms=7 * 24 * 3_600_000,
        )
        f = reporter.build_forecast(limit, "openai-codex", forecast_snapshot(series), self.now_ms)
        self.assertEqual(f["verdict"], "ON PACE")
        self.assertAlmostEqual(f["projected"], 0.6, places=3)


class ForecastRowsTests(unittest.TestCase):
    def test_forecast_rows_filters_orders_and_sorts_limits(self):
        now_ms = 1_789_000_000_000
        payload = {
            "reports": [
                {
                    "provider": "google-antigravity",
                    "limits": [
                        forecast_limit(limit_id="ga:daily", label="Daily", resets_at_ms=now_ms + 1_000),
                    ],
                },
                {
                    "provider": "anthropic",
                    "limits": [],
                },
                {
                    "provider": "zai",
                    "limits": [
                        forecast_limit(limit_id="zai:late", label="Late", resets_at_ms=now_ms + 10_000_000),
                        forecast_limit(limit_id="zai:early", label="Early", resets_at_ms=now_ms + 1_000_000),
                    ],
                },
                {
                    "provider": "openai-codex",
                    "limits": [
                        forecast_limit(limit_id="codex:primary", label="Primary", resets_at_ms=now_ms + 5_000_000),
                    ],
                },
            ]
        }
        snapshot = forecast_snapshot([])
        rows = reporter.forecast_rows(payload, snapshot, now_ms)
        self.assertEqual([provider for provider, _ in rows], ["openai-codex", "zai"])
        zai_limits = [f["limit_id"] for f in rows[1][1]]
        self.assertEqual(zai_limits, ["zai:early", "zai:late"])


class WindowCouplingTests(unittest.TestCase):
    NOW_MS = 1_789_000_000_000
    HOUR_MS = 3_600_000

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
            "start_ms": self.NOW_MS - 7 * 86_400_000,
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
                "start_ms": self.NOW_MS - 7 * 86_400_000,
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
            "start_ms": self.NOW_MS - 7 * 86_400_000,
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

    def test_forecast_rows_couples_short_window_to_long_window(self):
        now_ms = self.NOW_MS
        payload = {
            "reports": [
                {
                    "provider": "anthropic",
                    "limits": [
                        forecast_limit(
                            limit_id="anthropic:5h",
                            label="Claude 5 Hour",
                            used_fraction=0.46,
                            resets_at_ms=now_ms + 2 * self.HOUR_MS,
                            duration_ms=5 * self.HOUR_MS,
                        ),
                        forecast_limit(
                            limit_id="anthropic:7d",
                            label="Claude 7 Day",
                            used_fraction=0.51,
                            resets_at_ms=now_ms + 6 * 24 * self.HOUR_MS,
                            duration_ms=7 * 24 * self.HOUR_MS,
                        ),
                    ],
                }
            ]
        }
        snapshot = self.coupled_snapshot(
            [(now_ms - self.HOUR_MS, 0.00), (now_ms, 0.50)],
            [(now_ms - self.HOUR_MS, 0.10), (now_ms, 0.20)],
        )
        rows = reporter.forecast_rows(payload, snapshot, now_ms)
        forecasts = {f["limit_id"]: f for f in rows[0][1]}
        self.assertAlmostEqual(forecasts["anthropic:5h"]["coupled_ratio"], 0.2, places=3)
        self.assertEqual(forecasts["anthropic:5h"]["coupled_limit_id"], "anthropic:7d")
        self.assertIsNone(forecasts["anthropic:7d"]["coupled_limit_id"])

    def test_fmt_window_short_labels_hours_days_and_unknown(self):
        self.assertEqual(reporter.fmt_window_short(5 * self.HOUR_MS), "5h")
        self.assertEqual(reporter.fmt_window_short(7 * 24 * self.HOUR_MS), "7d")
        self.assertEqual(reporter.fmt_window_short(None), "long")
        self.assertEqual(reporter.fmt_window_short(0), "long")


class FmtDurationTests(unittest.TestCase):
    def test_zero_and_negative_durations_read_as_now(self):
        self.assertEqual(reporter.fmt_duration(0), "~now")
        self.assertEqual(reporter.fmt_duration(-1), "~now")
        self.assertEqual(reporter.fmt_duration(-3_600_000), "~now")

    def test_minute_boundaries_round_up_to_singular_and_plural(self):
        self.assertEqual(reporter.fmt_duration(60_000), "~in 1 minute")
        self.assertEqual(reporter.fmt_duration(120_000), "~in 2 minutes")
        self.assertEqual(reporter.fmt_duration(3_599_000), "~in 60 minutes")

    def test_hour_boundaries_round_up_to_singular_and_plural(self):
        self.assertEqual(reporter.fmt_duration(3_600_000), "~in 1 hour")
        self.assertEqual(reporter.fmt_duration(7_200_000), "~in 2 hours")

    def test_day_boundaries_round_up_to_singular_and_plural(self):
        self.assertEqual(reporter.fmt_duration(86_400_000), "~in 1 day")
        self.assertEqual(reporter.fmt_duration(172_800_000), "~in 2 days")

    def test_reset_estimate_three_hours_out_matches_duration_text(self):
        resets_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + 3 * 3_600_000
        self.assertEqual(reporter.fmt_reset_estimate(resets_at_ms), "~in 3 hours")
        self.assertEqual(reporter.fmt_reset_estimate(resets_at_ms), reporter.fmt_duration(3 * 3_600_000))


class ForecastAdviceTests(unittest.TestCase):
    NOW_MS = 1_789_000_000_000

    def test_run_out_advice_counts_exhaustion_and_gap_before_reset(self):
        shape = forecast_shape(
            verdict="RUN OUT",
            used=0.5,
            resets_at_ms=self.NOW_MS + 7 * 24 * 3_600_000,
            projected=1.0,
            exhaust_in_ms=5 * 24 * 3_600_000,
        )
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "tone it down \u00b7 hits 100% ~in 5 days, ~in 2 days before reset",
        )

    def test_run_out_advice_clamps_gap_before_reset_at_now(self):
        shape = forecast_shape(
            verdict="RUN OUT",
            used=0.5,
            resets_at_ms=self.NOW_MS + 2 * 24 * 3_600_000,
            projected=1.0,
            exhaust_in_ms=5 * 24 * 3_600_000,
        )
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "tone it down \u00b7 hits 100% ~in 5 days, ~now before reset",
        )

    def test_advice_uses_passed_now_not_wall_clock(self):
        now_ms = 1_600_000_000_000
        shape = forecast_shape(
            verdict="RUN OUT",
            used=0.5,
            resets_at_ms=now_ms + 7 * 24 * 3_600_000,
            projected=1.0,
            exhaust_in_ms=5 * 24 * 3_600_000,
        )
        self.assertEqual(
            reporter.forecast_advice(shape, now_ms),
            "tone it down \u00b7 hits 100% ~in 5 days, ~in 2 days before reset",
        )

    def test_exhausted_advice_names_reset_three_days_out(self):
        resets_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + 3 * 86_400_000
        shape = forecast_shape(verdict="EXHAUSTED", used=1.0, resets_at_ms=resets_at_ms)
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "exhausted \u00b7 wait, resets ~in 3 days",
        )

    def test_exhausted_advice_without_reset_time_is_bare_wait(self):
        shape = forecast_shape(verdict="EXHAUSTED", used=1.0, resets_at_ms=None)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "exhausted \u00b7 wait")

    def test_hot_advice_reports_projected_percent(self):
        shape = forecast_shape(verdict="HOT", used=0.7, projected=0.92)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "ease off \u00b7 ~92% by reset")

    def test_on_pace_advice_reports_projected_percent(self):
        shape = forecast_shape(verdict="ON PACE", used=0.5, projected=0.69)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "keep going \u00b7 ~69% by reset")

    def test_spare_advice_reports_spare_percent(self):
        shape = forecast_shape(verdict="SPARE", used=0.24, projected=0.24)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "crank it up \u00b7 ~76% spare by reset")

    def test_no_data_without_usage_reports_no_usage(self):
        self.assertEqual(reporter.forecast_advice(forecast_shape(), self.NOW_MS), "no usage reported")

    def test_no_data_with_usage_reports_insufficient_history(self):
        shape = forecast_shape(used=0.3)
        self.assertEqual(reporter.forecast_advice(shape, self.NOW_MS), "not enough history yet")

    def test_spare_advice_appends_long_window_cost(self):
        shape = forecast_shape(verdict="SPARE", used=0.24, projected=0.24)
        shape["coupled_burn"] = 0.076
        shape["coupled_window_ms"] = 7 * 24 * 3_600_000
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "crank it up \u00b7 ~76% spare by reset \u00b7 ~8% of 7d",
        )

    def test_on_pace_advice_appends_long_window_cost(self):
        shape = forecast_shape(verdict="ON PACE", used=0.5, projected=0.69)
        shape["coupled_burn"] = 0.076
        shape["coupled_window_ms"] = 7 * 24 * 3_600_000
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "keep going \u00b7 ~69% by reset \u00b7 ~8% of 7d",
        )

    def test_gated_advice_reports_burn_and_room(self):
        shape = forecast_shape(verdict="GATED", used=0.24)
        shape["coupled_burn"] = 0.38
        shape["coupled_room"] = 0.2
        shape["coupled_window_ms"] = 7 * 24 * 3_600_000
        self.assertEqual(
            reporter.forecast_advice(shape, self.NOW_MS),
            "7d gates it \u00b7 full burn ~38%, room ~20%",
        )


if __name__ == "__main__":
    unittest.main()
