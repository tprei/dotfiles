import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
SHARE_DIR = TOOLS / ".local" / "share" / "codex-usage"
COLLECTOR_PATH = SHARE_DIR / "token_usage.py"
REPORTER_PATH = TOOLS / ".local" / "bin" / "codex-usage-check"

if str(SHARE_DIR) not in sys.path:
    sys.path.insert(0, str(SHARE_DIR))

import token_usage


def load_reporter():
    loader = importlib.machinery.SourceFileLoader(
        "codex_usage_check_under_test", str(REPORTER_PATH)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


reporter = load_reporter()

START_MS = 1_789_000_000_000
END_MS = START_MS + 43_200_000
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


class MergeUsageTests(unittest.TestCase):
    def test_snapshot_schema_and_baseline_providers_on_empty_sources(self):
        snapshot = merge_collections(
            [("WSL", merge_collection([])), ("mini-1", merge_collection([]))]
        )
        self.assertEqual(set(snapshot), {"start_ms", "end_ms", "providers", "sources_ok", "issues"})
        self.assertEqual(snapshot["start_ms"], START_MS)
        self.assertEqual(snapshot["end_ms"], END_MS)
        self.assertEqual([total["provider"] for total in snapshot["providers"]], BASELINE_PROVIDERS)
        for total in snapshot["providers"]:
            self.assertEqual(set(total), {"provider", "tokens", "estimated_usd", "unpriced_records"})
            self.assertEqual(total["tokens"], 0)
            self.assertEqual(total["estimated_usd"], 0.0)
            self.assertEqual(total["unpriced_records"], 0)
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
                mock.patch.object(reporter, "tg_pin") as pin:
            self.assertTrue(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        send.assert_called_once()
        edit.assert_called_once()
        pin.assert_called_once()
        self.assertEqual(call_arg(pin.call_args, 1, "message_id"), 555)
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
                ):
            self.assertFalse(reporter.update_pinned(self.config, self.token_image, "tokens_message_id"))
        edit.assert_not_called()
        send.assert_called_once()
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
        update_patcher = mock.patch.object(reporter, "update_pinned", return_value=True)
        failure_patcher = mock.patch.object(
            reporter, "fail", side_effect=lambda error: getattr(error, "exit_code", 2)
        )
        self.build_limits = limits_patcher.start()
        self.build_tokens = token_patcher.start()
        self.update = update_patcher.start()
        self.failure = failure_patcher.start()
        self.addCleanup(limits_patcher.stop)
        self.addCleanup(token_patcher.stop)
        self.addCleanup(update_patcher.stop)
        self.addCleanup(failure_patcher.stop)

    def published(self):
        return sorted(
            (call_arg(call, 1, "image"), call_arg(call, 2, "state_key"))
            for call in self.update.call_args_list
        )

    def test_publishes_both_images_with_independent_state_keys(self):
        self.assertEqual(reporter.publish_images(self.config), 0)
        self.assertEqual(
            self.published(),
            [(b"limits-image", "message_id"), (b"token-image", "tokens_message_id")],
        )
        self.failure.assert_not_called()

    def test_quota_failure_still_publishes_token_chart(self):
        self.build_limits.side_effect = reporter.UsageError("omp usage unavailable", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(self.published(), [(b"token-image", "tokens_message_id")])
        self.failure.assert_called_once()

    def test_token_collection_failure_still_publishes_limits(self):
        self.build_tokens.side_effect = reporter.UsageError("mini-1 unavailable", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(self.published(), [(b"limits-image", "message_id")])
        self.failure.assert_called_once()

    def test_incomplete_token_snapshot_publishes_with_warning_exit(self):
        self.build_tokens.return_value = (b"token-image", 2)
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(
            self.published(),
            [(b"limits-image", "message_id"), (b"token-image", "tokens_message_id")],
        )

    def test_unrecovered_tool_error_exits_one(self):
        self.build_limits.side_effect = reporter.UsageError("no provider reports", 1)
        self.assertEqual(reporter.publish_images(self.config), 1)
        self.assertEqual(self.published(), [(b"token-image", "tokens_message_id")])

    def test_failed_publication_exits_two_and_attempts_both_images(self):
        self.update.side_effect = lambda config, image, state_key: state_key == "message_id"
        self.assertEqual(reporter.publish_images(self.config), 2)
        self.assertEqual(len(self.update.call_args_list), 2)
        self.assertEqual(
            self.published(),
            [(b"limits-image", "message_id"), (b"token-image", "tokens_message_id")],
        )

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


if __name__ == "__main__":
    unittest.main()
