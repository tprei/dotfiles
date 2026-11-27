import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
SHARE_DIR = TOOLS / ".local" / "share" / "codex-usage"

if str(SHARE_DIR) not in sys.path:
    sys.path.insert(0, str(SHARE_DIR))

activity_usage = importlib.import_module("activity_usage")

START_MS = 1_789_000_000_000
END_MS = START_MS + 7 * 86_400_000
HOUR_MS = 3_600_000
RECORD_KEYS = {
    "session_id",
    "provider",
    "model",
    "project",
    "title",
    "at_ms",
    "tokens",
}
COLLECTION_KEYS = {"start_ms", "end_ms", "records", "issues"}


def iso_z(ms: int) -> str:
    moment = datetime.fromtimestamp(ms // 1000, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


def title_entry(text="Unit fixture title", updated_ms=None):
    entry = {
        "type": "title",
        "v": 1,
        "title": text,
        "updatedAt": iso_z(updated_ms if updated_ms is not None else START_MS - 500),
    }
    return entry


def session_entry(session_id="session-1", cwd=None, title=None):
    entry = {
        "type": "session",
        "version": 3,
        "id": session_id,
        "timestamp": iso_z(START_MS - 1_000),
    }
    if cwd is not None:
        entry["cwd"] = cwd
    if title is not None:
        entry["title"] = title
    return entry


def bucket_usage(total_tokens=15, cost_total=0.03):
    usage = {"input": 10, "output": 5, "totalTokens": total_tokens}
    if cost_total is not None:
        usage["cost"] = {"total": cost_total}
    return usage


def assistant_entry(entry_id, timestamp_ms, provider="zai", model="glm-5.3", usage=None):
    return {
        "type": "message",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "message": {
            "role": "assistant",
            "provider": provider,
            "model": model,
            "api": "openai-completions",
            "timestamp": timestamp_ms,
            "usage": bucket_usage() if usage is None else usage,
        },
    }


def model_usage_entry(entry_id, timestamp_ms, provider="anthropic", model="claude-opus-5", usage=None):
    return {
        "type": "model_usage",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "provider": provider,
        "model": model,
        "api": "anthropic-messages",
        "usage": bucket_usage() if usage is None else usage,
    }


def user_entry(entry_id, timestamp_ms):
    return {
        "type": "message",
        "id": entry_id,
        "timestamp": iso_z(timestamp_ms),
        "message": {"role": "user", "content": [{"type": "text", "text": "unit fixture"}]},
    }


def activity_record(session_id="session-1", provider="zai", model="glm-5.3",
                    project=None, title=None, at_ms=None, tokens=100):
    return {
        "session_id": session_id,
        "provider": provider,
        "model": model,
        "project": project,
        "title": title,
        "at_ms": at_ms if at_ms is not None else START_MS + HOUR_MS,
        "tokens": tokens,
    }


def activity_collection(records, issues=None):
    return {
        "start_ms": START_MS,
        "end_ms": END_MS,
        "records": records,
        "issues": issues or [],
    }


class TempRootMixin(unittest.TestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="omp-activity-tests-")
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

    def collect(self, root=None):
        return activity_usage.collect_activity(
            self.root if root is None else root, START_MS, END_MS
        )

    def row(self, collection, **fields):
        for record in collection["records"]:
            if all(record[key] == value for key, value in fields.items()):
                return record
        return None


class CollectActivityGroupingTests(TempRootMixin):
    def test_groups_per_session_and_model_with_latest_at_and_summed_tokens(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                title_entry("Track relay lag"),
                session_entry(cwd="/home/prei/dotfiles"),
                assistant_entry("a1", START_MS + HOUR_MS, usage=bucket_usage(10)),
                assistant_entry("a2", START_MS + 2 * HOUR_MS, usage=bucket_usage(20)),
                assistant_entry("a3", START_MS + 3 * HOUR_MS, usage=bucket_usage(30)),
            ],
        )
        collection = self.collect()
        record = self.row(collection)
        self.assertEqual(record["at_ms"], START_MS + 3 * HOUR_MS)
        self.assertEqual(record["tokens"], 60)
        self.assertEqual(record["session_id"], "session-1")
        self.assertEqual(record["project"], "dotfiles")
        self.assertEqual(record["title"], "Track relay lag")
        self.assertEqual(collection["records"], [record])

    def test_distinct_models_providers_and_entry_kinds_yield_separate_rows(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                session_entry(cwd="/home/prei/dotfiles"),
                assistant_entry("a1", START_MS + HOUR_MS),
                assistant_entry("a2", START_MS + 2 * HOUR_MS, model="glm-5.4"),
                assistant_entry("a3", START_MS + 3 * HOUR_MS, provider="openai-codex", model="gpt-6.2"),
                model_usage_entry("m1", START_MS + 4 * HOUR_MS, provider="anthropic", model="claude-opus-5"),
            ],
        )
        collection = self.collect()
        self.assertEqual(
            {(record["provider"], record["model"]) for record in collection["records"]},
            {
                ("zai", "glm-5.3"),
                ("zai", "glm-5.4"),
                ("openai-codex", "gpt-6.2"),
                ("anthropic", "claude-opus-5"),
            },
        )
        self.assertTrue(all(record["session_id"] == "session-1" for record in collection["records"]))

    def test_title_entry_wins_and_session_title_is_fallback(self):
        self.write_session(
            "agent/sessions/proj/titled.jsonl",
            [
                title_entry("From title entry"),
                session_entry(session_id="s-titled", cwd="/repos/app", title="From session entry"),
                assistant_entry("a1", START_MS + HOUR_MS),
            ],
        )
        self.write_session(
            "agent/sessions/proj/empty-title.jsonl",
            [
                title_entry(""),
                session_entry(session_id="s-empty", cwd="/repos/app", title="From session entry"),
                assistant_entry("a2", START_MS + 2 * HOUR_MS, model="claude-opus-5"),
            ],
        )
        collection = self.collect()
        self.assertEqual(
            self.row(collection, session_id="s-titled")["title"], "From title entry"
        )
        self.assertEqual(
            self.row(collection, session_id="s-empty")["title"], "From session entry"
        )

    def test_missing_metadata_yields_nulls(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        record = self.collect()["records"][0]
        self.assertIsNone(record["title"])
        self.assertIsNone(record["project"])
        self.assertEqual(record["session_id"], "session-1")

    def test_project_slug_handles_trailing_slash_windows_and_root(self):
        cases = {
            "/home/prei/dotfiles/": "dotfiles",
            "C:\\Users\\srtp\\proj": "proj",
            "/": None,
        }
        for index, (cwd, expected) in enumerate(cases.items()):
            with self.subTest(cwd=cwd):
                self.write_session(
                    f"agent/sessions/proj/session-{index}.jsonl",
                    [session_entry(session_id=f"s-{index}", cwd=cwd), assistant_entry("a1", START_MS + HOUR_MS)],
                )
        collection = self.collect()
        slugs = sorted(
            (record["session_id"], record["project"]) for record in collection["records"]
        )
        self.assertEqual(slugs, [("s-0", "dotfiles"), ("s-1", "proj"), ("s-2", None)])

    def test_window_boundaries_apply_to_activity_rows(self):
        self.write_session(
            "agent/sessions/in-window.jsonl",
            [session_entry(session_id="in"), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        self.write_session(
            "agent/sessions/at-end.jsonl",
            [session_entry(session_id="at-end"), assistant_entry("b1", END_MS)],
        )
        self.write_session(
            "agent/sessions/early.jsonl",
            [session_entry(session_id="early"), assistant_entry("c1", START_MS - HOUR_MS)],
        )
        collection = self.collect()
        self.assertEqual([record["session_id"] for record in collection["records"]], ["in"])

    def test_title_whitespace_collapses_to_single_spaces(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                title_entry("  Fix\n\tthe   login\r\nbug  "),
                session_entry(cwd="/repos/app"),
                assistant_entry("a1", START_MS + HOUR_MS),
            ],
        )
        collection = self.collect()
        self.assertEqual([record["title"] for record in collection["records"]], ["Fix the login bug"])

    def test_home_directories_and_root_are_not_projects(self):
        home = Path.home().as_posix()
        self.assertIsNone(activity_usage._project_slug(home))
        self.assertIsNone(activity_usage._project_slug(f"{home}/"))
        self.assertIsNone(activity_usage._project_slug("/home/alice"))
        self.assertIsNone(activity_usage._project_slug("/Users/alice"))
        self.assertIsNone(activity_usage._project_slug("C:\\Users\\srtp"))
        self.assertIsNone(activity_usage._project_slug("/root"))
        self.assertEqual(activity_usage._project_slug("/home/prei/dotfiles"), "dotfiles")


class CollectActivityFidelityTests(TempRootMixin):
    def test_malformed_usage_keeps_row_with_null_tokens_and_issue(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                session_entry(cwd="/repos/app"),
                assistant_entry("a1", START_MS + HOUR_MS, usage={}),
            ],
        )
        collection = self.collect()
        record = collection["records"][0]
        self.assertIsNone(record["tokens"])
        self.assertTrue(any("malformed usage record" in issue for issue in collection["issues"]))

    def test_mixed_valid_and_malformed_usage_sums_valid_only(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                session_entry(cwd="/repos/app"),
                assistant_entry("a1", START_MS + HOUR_MS, usage=bucket_usage(10)),
                assistant_entry("a2", START_MS + 2 * HOUR_MS, usage={"totalTokens": "bad"}),
            ],
        )
        collection = self.collect()
        self.assertEqual(collection["records"][0]["tokens"], 10)
        self.assertEqual(len(collection["issues"]), 1)

    def test_user_and_tool_entries_produce_no_rows(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(cwd="/repos/app"), user_entry("u1", START_MS + HOUR_MS)],
        )
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertEqual(collection["issues"], [])

    def test_profiles_and_subagent_files_are_scanned_with_own_headers(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(session_id="main"), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        self.write_session(
            "agent/sessions/proj/session/__advisor.jsonl",
            [session_entry(session_id="advisor"), assistant_entry("a2", START_MS + 2 * HOUR_MS)],
        )
        self.write_session(
            "profiles/mix/agent/sessions/other/session.jsonl",
            [session_entry(session_id="mix"), assistant_entry("a3", START_MS + 3 * HOUR_MS)],
        )
        collection = self.collect()
        self.assertEqual(
            sorted(record["session_id"] for record in collection["records"]),
            ["advisor", "main", "mix"],
        )

    def test_non_session_and_non_jsonl_files_are_ignored(self):
        self.write_session("agent/sessions/proj/notes.txt", [session_entry()])
        self.write_session(
            "agent/sessions/proj/log.jsonl",
            [{"type": "log", "message": "not a session"}],
        )
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertEqual(collection["issues"], [])

    def test_unreadable_file_yields_issue_but_others_survive(self):
        blocked = self.write_session(
            "agent/sessions/proj/locked.jsonl",
            [session_entry(session_id="locked"), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        self.write_session(
            "agent/sessions/proj/open.jsonl",
            [session_entry(session_id="open"), assistant_entry("a2", START_MS + HOUR_MS)],
        )
        os.chmod(blocked, 0o000)
        self.addCleanup(os.chmod, blocked, 0o644)
        collection = self.collect()
        self.assertEqual([record["session_id"] for record in collection["records"]], ["open"])
        self.assertTrue(any("locked.jsonl" in issue for issue in collection["issues"]))

    def test_records_cap_keeps_most_recent_and_ascending(self):
        entries = [session_entry(cwd="/repos/app")]
        for index in range(activity_usage.ACTIVITY_MAX_RECORDS + 2):
            entries.append(
                model_usage_entry(
                    f"m{index}",
                    START_MS + (index + 1) * 60_000,
                    model=f"model-{index:03d}",
                )
            )
        self.write_session("agent/sessions/proj/session.jsonl", entries)
        collection = self.collect()
        records = collection["records"]
        self.assertEqual(len(records), activity_usage.ACTIVITY_MAX_RECORDS)
        self.assertNotIn("model-000", {record["model"] for record in records})
        self.assertNotIn("model-001", {record["model"] for record in records})
        ats = [record["at_ms"] for record in records]
        self.assertEqual(ats, sorted(ats))

    def test_long_title_and_project_are_truncated(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [
                title_entry("T" * 300),
                session_entry(cwd=f"/home/prei/{'p' * 300}"),
                assistant_entry("a1", START_MS + HOUR_MS),
            ],
        )
        record = self.collect()["records"][0]
        self.assertEqual(len(record["title"]), activity_usage._TEXT_MAX_CHARS)
        self.assertEqual(record["project"], "p" * activity_usage._TEXT_MAX_CHARS)

    def test_wire_schema_and_raw_provider_ids(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(cwd="/repos/app"), assistant_entry("a1", START_MS + HOUR_MS, provider="antigravity-cli")],
        )
        collection = self.collect()
        self.assertEqual(set(collection), COLLECTION_KEYS)
        self.assertEqual(set(collection["records"][0]), RECORD_KEYS)
        self.assertEqual(collection["records"][0]["provider"], "antigravity-cli")

    def test_missing_root_and_empty_dirs(self):
        collection = self.collect(self.root / "absent")
        self.assertEqual(collection["records"], [])
        self.assertEqual(collection["issues"], ["session root not found"])
        (self.root / "unrelated").mkdir()
        collection = self.collect()
        self.assertEqual(collection["records"], [])
        self.assertEqual(collection["issues"], ["no session directories found"])
        (self.root / "agent" / "sessions" / "proj").mkdir(parents=True)
        collection = self.collect()
        self.assertEqual(collection, {"start_ms": START_MS, "end_ms": END_MS, "records": [], "issues": []})

    def test_half_written_final_line_is_skipped_silently(self):
        path = self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(cwd="/repos/app"), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"type": "message", "id": "a2"')
        collection = self.collect()
        self.assertEqual(len(collection["records"]), 1)
        self.assertEqual(collection["issues"], [])

    def test_complete_malformed_line_is_reported(self):
        path = self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(cwd="/repos/app"), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"type": "message", "id": "a2"\n')
        collection = self.collect()
        self.assertEqual(len(collection["records"]), 1)
        self.assertEqual(collection["issues"], ["session.jsonl: 1 malformed line"])


class ActivityCliTests(TempRootMixin):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SHARE_DIR / "activity_usage.py"), *arguments],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def window_arguments(self):
        return ["--start-ms", str(START_MS), "--end-ms", str(END_MS)]

    def test_emits_json_for_positional_root(self):
        self.write_session(
            "agent/sessions/proj/session.jsonl",
            [session_entry(cwd="/repos/app"), assistant_entry("a1", START_MS + HOUR_MS)],
        )
        result = self.run_cli(*self.window_arguments(), str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), COLLECTION_KEYS)
        self.assertEqual(len(payload["records"]), 1)

    def test_missing_root_exits_two_with_usable_json(self):
        result = self.run_cli(*self.window_arguments(), str(self.root / "absent"))
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["records"], [])
        self.assertTrue(payload["issues"])

    def test_argument_errors_exit_two_without_json(self):
        cases = [
            [],
            ["--start-ms", str(START_MS)],
            self.window_arguments() + ["--bogus"],
            self.window_arguments() + [str(self.root), "--start-ms", "-5"],
            ["--start-ms", str(END_MS), "--end-ms", str(START_MS)],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout.strip(), "")


class MergeActivityTests(TempRootMixin):
    def merge(self, collections, issues=None):
        return activity_usage.merge_activity(collections, START_MS, END_MS, issues)

    def test_dedups_same_session_across_sources_keeping_max_tokens_and_latest(self):
        merged = self.merge(
            [
                ("WSL", activity_collection([activity_record(tokens=100, at_ms=START_MS + HOUR_MS)])),
                ("mini", activity_collection([activity_record(tokens=150, at_ms=START_MS + 2 * HOUR_MS)])),
            ]
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["tokens"], 150)
        self.assertEqual(merged[0]["at_ms"], START_MS + 2 * HOUR_MS)

    def test_metadata_conflicts_prefer_nonempty_then_deterministic(self):
        merged = self.merge(
            [
                ("WSL", activity_collection([activity_record(title=None, project=None)])),
                ("mini", activity_collection([activity_record(title="Real title", project="dotfiles")])),
            ]
        )
        self.assertEqual(merged[0]["title"], "Real title")
        self.assertEqual(merged[0]["project"], "dotfiles")

    def test_window_mismatch_drops_source_with_issue(self):
        sink: list[str] = []
        merged = self.merge(
            [
                ("WSL", activity_collection([activity_record()])),
                ("mini", {**activity_collection([activity_record(provider="anthropic", model="claude-opus-5")]), "start_ms": START_MS - 1}),
            ],
            issues=sink,
        )
        self.assertEqual([record["provider"] for record in merged], ["zai"])
        self.assertTrue(any("mini: activity window mismatch" in issue for issue in sink))

    def test_invalid_rows_are_skipped_without_dropping_source(self):
        sink: list[str] = []
        merged = self.merge(
            [
                ("WSL", activity_collection([activity_record(), {"provider": "zai"}])),
            ],
            issues=sink,
        )
        self.assertEqual(len(merged), 1)
        self.assertTrue(any("WSL: skipped 1 invalid activity record" in issue for issue in sink))

    def test_relayed_project_and_title_are_normalized(self):
        merged = self.merge(
            [
                (
                    "relay",
                    activity_collection(
                        [
                            activity_record(session_id="session-1", project="/home/prei/secret", title="x" * 5000),
                            activity_record(session_id="session-2", project="/home/prei"),
                        ]
                    ),
                ),
            ]
        )
        by_session = {record["session_id"]: record for record in merged}
        self.assertEqual(by_session["session-1"]["project"], "secret")
        self.assertEqual(len(by_session["session-1"]["title"]), activity_usage._TEXT_MAX_CHARS)
        self.assertIsNone(by_session["session-2"]["project"])

    def test_null_session_rows_differing_only_in_tokens_merge(self):
        merged = self.merge(
            [
                (
                    "WSL",
                    activity_collection(
                        [
                            activity_record(session_id=None, tokens=None),
                            activity_record(session_id=None, tokens=5),
                        ]
                    ),
                ),
            ]
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual({record["tokens"] for record in merged}, {None, 5})

    def test_out_of_window_rows_are_skipped_with_issue(self):
        sink: list[str] = []
        merged = self.merge(
            [
                ("WSL", activity_collection([
                    activity_record(),
                    activity_record(provider="anthropic", model="claude-opus-5", at_ms=END_MS),
                ])),
            ],
            issues=sink,
        )
        self.assertEqual([record["provider"] for record in merged], ["zai"])
        self.assertTrue(any("WSL: skipped 1 invalid activity record" in issue for issue in sink))

    def test_sorts_descending_and_caps_output(self):
        records = [
            activity_record(model=f"model-{index:03d}", at_ms=START_MS + (index + 1) * 60_000)
            for index in range(activity_usage.ACTIVITY_MAX_RECORDS + 5)
        ]
        merged = self.merge([("WSL", activity_collection(records))])
        self.assertEqual(len(merged), activity_usage.ACTIVITY_MAX_RECORDS)
        self.assertEqual(merged[0]["model"], f"model-{activity_usage.ACTIVITY_MAX_RECORDS + 4:03d}")
        ats = [record["at_ms"] for record in merged]
        self.assertEqual(ats, sorted(ats, reverse=True))

    def test_null_session_rows_dedup_on_exact_identity_only(self):
        merged = self.merge(
            [
                ("WSL", activity_collection([
                    activity_record(session_id=None, tokens=10, at_ms=START_MS + HOUR_MS),
                    activity_record(session_id=None, tokens=10, at_ms=START_MS + HOUR_MS),
                    activity_record(session_id=None, tokens=20, at_ms=START_MS + 2 * HOUR_MS),
                ])),
            ]
        )
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["tokens"], 20)
        self.assertEqual(merged[1]["tokens"], 10)

    def test_mixed_null_and_named_sessions_do_not_crash_and_cap_applies(self):
        records = [
            activity_record(model=f"model-{index:03d}", at_ms=START_MS + (index + 1) * 60_000)
            for index in range(activity_usage.ACTIVITY_MAX_RECORDS + 3)
        ]
        records.append(activity_record(session_id=None, provider="anthropic", model="claude-opus-5"))
        merged = self.merge([("WSL", activity_collection(records))])
        self.assertEqual(len(merged), activity_usage.ACTIVITY_MAX_RECORDS)

    def test_empty_string_metadata_normalizes_to_null(self):
        merged = self.merge(
            [("WSL", activity_collection([activity_record(title="", project="")]))]
        )
        self.assertIsNone(merged[0]["title"])
        self.assertIsNone(merged[0]["project"])

    def test_collection_issues_are_folded_into_sink_with_label(self):
        sink: list[str] = []
        self.merge(
            [("WSL", activity_collection([activity_record()], issues=["session.jsonl: 1 malformed line"]))],
            issues=sink,
        )
        self.assertIn("WSL: session.jsonl: 1 malformed line", sink)


if __name__ == "__main__":
    unittest.main()
