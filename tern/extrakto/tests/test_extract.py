import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import extract


def leaf(pane_id):
    return {"Leaf": pane_id}


def split(axis, a, b):
    return {"Split": {"axis": axis, "ratio": 0.5, "a": a, "b": b}}


def block(block_id, program="zsh"):
    return {"id": block_id, "program": program}


def tab(tab_id, tree, blocks):
    return {"id": tab_id, "splits": tree, "blocks": blocks}


def ls_block(block_id, title, program, rows):
    return {"id": block_id, "title": title, "program": program, "rows": rows}


def touch_db(path):
    open(path, "wb").close()


class FindOriginTests(unittest.TestCase):
    def test_direct_column_split_returns_origin(self):
        tree = split("Column", leaf(1), leaf(2))
        self.assertEqual(extract.find_origin(tree, 2), 1)

    def test_nested_tree_returns_origin(self):
        tree = split("Row", leaf(3), split("Column", leaf(1), leaf(2)))
        self.assertEqual(extract.find_origin(tree, 2), 1)

    def test_me_as_a_side_raises(self):
        tree = split("Column", leaf(2), leaf(1))
        with self.assertRaises(LookupError):
            extract.find_origin(tree, 2)

    def test_row_axis_raises(self):
        tree = split("Row", leaf(1), leaf(2))
        with self.assertRaises(LookupError):
            extract.find_origin(tree, 2)

    def test_b_side_split_raises(self):
        tree = split("Column", leaf(1), split("Column", leaf(2), leaf(3)))
        with self.assertRaises(LookupError):
            extract.find_origin(tree, 2)


class FindTabTests(unittest.TestCase):
    def test_finds_tab_across_sessions(self):
        first = tab(10, split("Column", leaf(1), leaf(2)), [block(1), block(2)])
        second = tab(20, split("Column", leaf(3), leaf(4)), [block(3), block(4)])
        ls = {"sessions": [{"tabs": [first]}, {"tabs": [second]}]}
        self.assertEqual(extract.find_tab(ls, 4), second)

    def test_unknown_id_raises(self):
        only = tab(10, split("Column", leaf(1), leaf(2)), [block(1), block(2)])
        ls = {"sessions": [{"tabs": [only]}]}
        with self.assertRaises(LookupError):
            extract.find_tab(ls, 9)


class TextBlocksTests(unittest.TestCase):
    def test_excludes_me_and_file_panes_and_keeps_pip_and_order(self):
        tree = split("Column", leaf(9), leaf(7))
        blocks = [
            block(7, "zsh"),
            block(5, ""),
            block(9, "zsh"),
            block(11, "zsh"),
            block(3, "nvim"),
        ]
        self.assertEqual(extract.text_blocks(tab(20, tree, blocks), 9), [7, 11, 3])


class PaneLinesTests(unittest.TestCase):
    def test_pane_lines_captures_and_caps_to_2000_lines(self):
        raw_text = "\n".join(f"line {i}" for i in range(2500)) + "\n"
        with mock.patch.object(extract, "run_tern", return_value=mock.Mock(stdout=raw_text)):
            lines = extract.pane_lines(5)
        self.assertEqual(len(lines), 2000)
        self.assertEqual(lines[0], "line 500")
        self.assertEqual(lines[-1], "line 2499")


class LineCandidatesTests(unittest.TestCase):
    def test_newest_line_first(self):
        results = extract.line_candidates(["older line here", "newer line here"])
        self.assertEqual(results[0][2], 1)
        self.assertEqual(results[-1][2], 0)

    def test_line_kinds_for_path_url_word_line(self):
        line = "open /usr/local/share/doc and https://example.com/page now"
        results = extract.line_candidates([line])
        self.assertEqual(results[0][0], "word")
        self.assertEqual(results[-1], ("line", line, 0))
        by_kind = {}
        for kind, text, _ in results:
            by_kind.setdefault(kind, []).append(text)
        self.assertEqual(by_kind["path"], ["/usr/local/share/doc"])
        self.assertEqual(by_kind["url"], ["example.com", "https://example.com/page"])
        self.assertEqual(by_kind["word"], ["/usr/local/share/doc", "https://example.com/page"])
        self.assertEqual(by_kind["line"], [line])

    def test_disabled_url_filter_omits_url_candidates(self):
        line = "open /usr/local/share/doc and https://example.com/page now"
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, ".config", "extrakto")
            os.makedirs(config_dir, exist_ok=True)
            with open(os.path.join(config_dir, "extrakto.conf"), "w") as f:
                f.write("[url]\nenabled = false\n")
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                results = extract.line_candidates([line])
        kinds = {kind for kind, _, _ in results}
        self.assertIn("word", kinds)
        self.assertIn("path", kinds)
        self.assertIn("line", kinds)
        self.assertNotIn("url", kinds)
        by_kind = {}
        for kind, text, _ in results:
            by_kind.setdefault(kind, []).append(text)
        self.assertEqual(by_kind["path"], ["/usr/local/share/doc"])
        self.assertEqual(by_kind["line"], [line])

    def test_disabled_word_filter_omits_word_candidates(self):
        line = "open /usr/local/share/doc and https://example.com/page now"
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = os.path.join(tmpdir, ".config", "extrakto")
            os.makedirs(config_dir, exist_ok=True)
            with open(os.path.join(config_dir, "extrakto.conf"), "w") as f:
                f.write("[word]\nenabled = false\n")
            with mock.patch.dict(os.environ, {"HOME": tmpdir}):
                results = extract.line_candidates([line])
        kinds = {kind for kind, _, _ in results}
        self.assertNotIn("word", kinds)
        self.assertIn("path", kinds)
        self.assertIn("url", kinds)
        self.assertIn("line", kinds)
        by_kind = {}
        for kind, text, _ in results:
            by_kind.setdefault(kind, []).append(text)
        self.assertEqual(by_kind["path"], ["/usr/local/share/doc"])
        self.assertEqual(by_kind["url"], ["example.com", "https://example.com/page"])
        self.assertEqual(by_kind["line"], [line])


class CaptureTests(unittest.TestCase):
    def fixture(self):
        tree = split("Column", leaf(5), leaf(9))
        blocks = [
            ls_block(5, "shell", "zsh", 2),
            ls_block(3, "logs", "tail", 2),
            ls_block(9, "Extract", "", 1),
        ]
        ls = {"sessions": [{"tabs": [tab(1, tree, blocks)]}]}
        lines_by_pane = {
            5: ["shared alpha start", "shared middle value", "gamma ending word"],
            3: ["shared three alpha", "delta other value", "plain text row"],
        }
        return ls, lines_by_pane

    def test_capture_metadata_structure_and_bounded_panes(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            result = extract.capture(ls, 9, lines_by_pane, db_path)
            self.assertEqual(result["origin"], 5)
            self.assertEqual(result["db"], db_path)
            self.assertEqual([pane["id"] for pane in result["panes"]], [5, 3])
            self.assertTrue(result["panes"][0]["origin"])
            self.assertFalse(result["panes"][1]["origin"])
            self.assertEqual(result["panes"][0]["lines"], lines_by_pane[5])
            self.assertIsInstance(result["candidates"], int)
            self.assertGreater(result["candidates"], 0)
            self.assertFalse(any(isinstance(v, list) and k == "candidates" for k, v in result.items()))

    def test_capture_preview_lines_caps_to_eight(self):
        ls, _ = self.fixture()
        ten_lines = [f"line {i}" for i in range(10)]
        lines_by_pane = {5: ten_lines, 3: ["short line"]}
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            result = extract.capture(ls, 9, lines_by_pane, db_path)
            self.assertEqual(len(result["panes"][0]["lines"]), 8)
            self.assertEqual(result["panes"][0]["lines"], ten_lines[-8:])

    def test_capture_panes_table_order_and_origin_flag(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            extract.capture(ls, 9, lines_by_pane, db_path)
            conn = sqlite3.connect(db_path)
            try:
                panes = conn.execute(
                    "SELECT id, ord, title, program, origin, rows FROM panes ORDER BY ord"
                ).fetchall()
                self.assertEqual(len(panes), 2)
                self.assertEqual(panes[0], (5, 0, "shell", "zsh", 1, 2))
                self.assertEqual(panes[1], (3, 1, "logs", "tail", 0, 2))
            finally:
                conn.close()

    def test_capture_lines_table_stores_all_lines_one_based(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            extract.capture(ls, 9, lines_by_pane, db_path)
            conn = sqlite3.connect(db_path)
            try:
                rows_5 = conn.execute("SELECT no, text FROM lines WHERE pane = 5 ORDER BY no").fetchall()
                self.assertEqual([r[0] for r in rows_5], [1, 2, 3])
                self.assertEqual([r[1] for r in rows_5], lines_by_pane[5])
                rows_3 = conn.execute("SELECT no, text FROM lines WHERE pane = 3 ORDER BY no").fetchall()
                self.assertEqual([r[0] for r in rows_3], [1, 2, 3])
                self.assertEqual([r[1] for r in rows_3], lines_by_pane[3])
            finally:
                conn.close()

    def test_capture_candidates_table_ordering_dedupe_and_ids(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            extract.capture(ls, 9, lines_by_pane, db_path)
            conn = sqlite3.connect(db_path)
            try:
                candidates = conn.execute(
                    "SELECT ord, id, text, kind, pane, screen, line FROM candidates ORDER BY ord"
                ).fetchall()
                self.assertEqual([c[0] for c in candidates], list(range(len(candidates))))
                pane_order = [c[4] for c in candidates]
                self.assertEqual(pane_order, [5] * pane_order.count(5) + [3] * pane_order.count(3))
                for pane in (5, 3):
                    pane_ids = [c[1] for c in candidates if c[4] == pane]
                    self.assertEqual(pane_ids, [f"{pane}:{n}" for n in range(len(pane_ids))])
                origin_shared = [c for c in candidates if c[4] == 5 and c[2] == "shared"]
                self.assertEqual(len(origin_shared), 1)
                self.assertEqual(origin_shared[0][6], 2)
                gamma = next(c for c in candidates if c[2] == "gamma")
                self.assertEqual(gamma[5], 1)
                self.assertEqual(gamma[6], 3)
                alpha = next(c for c in candidates if c[2] == "alpha" and c[4] == 5)
                self.assertEqual(alpha[5], 0)
                self.assertEqual(alpha[6], 1)
            finally:
                conn.close()

    def test_capture_eligible_table_dedupe_per_scope(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            extract.capture(ls, 9, lines_by_pane, db_path)
            conn = sqlite3.connect(db_path)
            try:
                tab_shared = conn.execute(
                    "SELECT c.pane, c.ord FROM eligible e JOIN candidates c ON e.ord = c.ord "
                    "WHERE e.scope = 'tab' AND c.text = 'shared' AND c.kind = 'word'"
                ).fetchall()
                self.assertEqual(len(tab_shared), 1)
                self.assertEqual(tab_shared[0][0], 5)

                pane_scopes = conn.execute(
                    "SELECT DISTINCT c.pane FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'pane'"
                ).fetchall()
                self.assertEqual(pane_scopes, [(5,)])

                screen_scopes = conn.execute(
                    "SELECT DISTINCT c.pane, c.screen FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'screen'"
                ).fetchall()
                self.assertEqual(screen_scopes, [(5, 1)])
            finally:
                conn.close()

    def test_capture_totals_table_nine_counts(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            extract.capture(ls, 9, lines_by_pane, db_path)
            conn = sqlite3.connect(db_path)
            try:
                totals = conn.execute("SELECT filter, scope, total FROM totals").fetchall()
                self.assertEqual(len(totals), 9)
                filters = {"word", "all", "line"}
                scopes = {"tab", "pane", "screen"}
                found_pairs = {(r[0], r[1]) for r in totals}
                self.assertEqual(found_pairs, {(f, s) for f in filters for s in scopes})
                totals_dict = {(r[0], r[1]): r[2] for r in totals}

                expected_word_tab = conn.execute(
                    "SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'tab' AND c.kind = 'word'"
                ).fetchone()[0]
                self.assertEqual(totals_dict[("word", "tab")], expected_word_tab)

                expected_line_screen = conn.execute(
                    "SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'screen' AND c.kind = 'line'"
                ).fetchone()[0]
                self.assertEqual(totals_dict[("line", "screen")], expected_line_screen)
            finally:
                conn.close()


    def test_capture_removed_placeholder_raises_without_recreating(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            touch_db(db_path)
            os.remove(db_path)
            with self.assertRaises(sqlite3.OperationalError):
                extract.capture(ls, 9, lines_by_pane, db_path)
            self.assertFalse(os.path.exists(db_path))

    def test_capture_missing_placeholder_cannot_create_file(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            with self.assertRaises(sqlite3.OperationalError):
                extract.capture(ls, 9, lines_by_pane, db_path)
            self.assertFalse(os.path.exists(db_path))

    def test_capture_writes_db_in_dir_with_special_characters(self):
        ls, lines_by_pane = self.fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = os.path.join(tmpdir, "plug in#s?dir")
            os.makedirs(plugin_dir)
            db_path = os.path.join(plugin_dir, "cat alog.db")
            touch_db(db_path)
            result = extract.capture(ls, 9, lines_by_pane, db_path)
            self.assertEqual(result["db"], db_path)
            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
            finally:
                conn.close()
            self.assertGreater(count, 0)


class MainTests(unittest.TestCase):
    def ls_fixture(self):
        tree = split("Column", leaf(5), leaf(9))
        blocks = [ls_block(5, "shell", "zsh", 2), ls_block(9, "Extract", "", 1)]
        return {"sessions": [{"tabs": [tab(1, tree, blocks)]}]}

    def test_wrong_form_returns_two_and_no_stdout(self):
        for argv in (
            [],
            ["capture"],
            ["capture", "5"],
            ["capture", "5", "db", "extra"],
            ["capture", "abc", "db"],
            ["candidates", "5"],
            ["unknown"],
        ):
            with self.subTest(argv=argv):
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = extract.main(argv)
                self.assertEqual(code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertNotEqual(stderr.getvalue(), "")

    def test_capture_success_prints_json_and_closes_db(self):
        ls = self.ls_fixture()

        def run_tern(*args):
            if args[0] == "ls":
                return mock.Mock(stdout=json.dumps(ls))
            return mock.Mock(stdout="shared alpha start\nshared middle value\n")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            touch_db(db_path)
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "9", db_path])
            self.assertEqual(code, 0)
            result = json.loads(stdout.getvalue().strip())
            self.assertEqual(result["origin"], 5)
            self.assertEqual(result["db"], db_path)
            self.assertEqual([pane["id"] for pane in result["panes"]], [5])
            self.assertTrue(result["panes"][0]["origin"])
            self.assertIsInstance(result["candidates"], int)

            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
                self.assertEqual(count, result["candidates"])
            finally:
                conn.close()

    def test_capture_failure_reports_and_returns_one(self):
        ls = self.ls_fixture()

        def run_tern(*args):
            if args[0] == "ls":
                return mock.Mock(stdout=json.dumps(ls))
            raise subprocess.CalledProcessError(
                3, ["tern", "capture", "5", "--surfaces", "--scrollback"], stderr="boom\n"
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
                stderr
            ), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "9", db_path])
            self.assertEqual(code, 1)
            self.assertEqual(stderr.getvalue(), "extrakto: tern exited 3: boom\n")
            self.assertEqual(stdout.getvalue(), "")

    def test_unknown_pane_reports_and_returns_one(self):
        def run_tern(*args):
            return mock.Mock(stdout=json.dumps(self.ls_fixture()))

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
                stderr
            ), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "99", db_path])
            self.assertEqual(code, 1)
            self.assertEqual(stderr.getvalue(), "extrakto: pane 99 is in no tab\n")
            self.assertEqual(stdout.getvalue(), "")

    def test_db_error_reports_and_returns_one(self):
        ls = self.ls_fixture()

        def run_tern(*args):
            if args[0] == "ls":
                return mock.Mock(stdout=json.dumps(ls))
            return mock.Mock(stdout="sample line\n")

        stderr = io.StringIO()
        stdout = io.StringIO()
        with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
            stderr
        ), contextlib.redirect_stdout(stdout):
            code = extract.main(["capture", "9", "/nonexistent_dir_cannot_create/test.db"])
        self.assertEqual(code, 1)
        self.assertTrue(stderr.getvalue().startswith("extrakto: "))
        self.assertEqual(stdout.getvalue(), "")

    def test_ls_timeout_reports_command_and_returns_one(self):
        def run_tern(*args):
            raise subprocess.TimeoutExpired(["tern", "ls", "--json"], 20)

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            touch_db(db_path)
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
                stderr
            ), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "9", db_path])
            self.assertEqual(code, 1)
            self.assertTrue(stderr.getvalue().startswith("extrakto: "))
            self.assertIn("tern ls --json", stderr.getvalue())
            self.assertIn("20", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")

    def test_capture_timeout_reports_command_and_returns_one(self):
        ls = self.ls_fixture()

        def run_tern(*args):
            if args[0] == "ls":
                return mock.Mock(stdout=json.dumps(ls))
            raise subprocess.TimeoutExpired(["tern", "capture", "5", "--surfaces", "--scrollback"], 20)

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            touch_db(db_path)
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
                stderr
            ), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "9", db_path])
            self.assertEqual(code, 1)
            self.assertTrue(stderr.getvalue().startswith("extrakto: "))
            self.assertIn("tern capture 5 --surfaces --scrollback", stderr.getvalue())
            self.assertIn("20", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")

    def test_removed_placeholder_reports_and_returns_one_without_recreating(self):
        ls = self.ls_fixture()

        def run_tern(*args):
            if args[0] == "ls":
                return mock.Mock(stdout=json.dumps(ls))
            return mock.Mock(stdout="shared alpha start\nshared middle value\n")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            touch_db(db_path)
            os.remove(db_path)
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
                stderr
            ), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "9", db_path])
            self.assertEqual(code, 1)
            self.assertTrue(stderr.getvalue().startswith("extrakto: "))
            self.assertEqual(stdout.getvalue(), "")
            self.assertFalse(os.path.exists(db_path))

    def test_malformed_ls_reports_and_returns_one(self):
        def run_tern(*args):
            return mock.Mock(stdout=json.dumps({"sessions": None}))

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "capture.db")
            touch_db(db_path)
            stderr = io.StringIO()
            stdout = io.StringIO()
            with mock.patch.object(extract, "run_tern", side_effect=run_tern), contextlib.redirect_stderr(
                stderr
            ), contextlib.redirect_stdout(stdout):
                code = extract.main(["capture", "9", db_path])
            self.assertEqual(code, 1)
            self.assertTrue(stderr.getvalue().startswith("extrakto: "))
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
