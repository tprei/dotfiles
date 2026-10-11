import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import search


def create_test_db(
    db_path: str,
    origin: int = 1,
    panes: list[tuple[int, int, str, str, int, int]] = None,
    lines: list[tuple[int, int, str]] = None,
    candidates: list[tuple[int, str, str, str, int, int, int]] = None,
) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = OFF")
    cur.execute("PRAGMA synchronous = OFF")
    cur.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    cur.execute("CREATE TABLE panes (id INTEGER PRIMARY KEY, ord INTEGER NOT NULL, title TEXT NOT NULL, program TEXT NOT NULL, origin INTEGER NOT NULL, rows INTEGER NOT NULL)")
    cur.execute("CREATE TABLE lines (pane INTEGER NOT NULL REFERENCES panes(id), no INTEGER NOT NULL, text TEXT NOT NULL, PRIMARY KEY(pane,no)) WITHOUT ROWID")
    cur.execute("CREATE TABLE candidates (ord INTEGER PRIMARY KEY, id TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL, pane INTEGER NOT NULL REFERENCES panes(id), screen INTEGER NOT NULL, line INTEGER NOT NULL)")
    cur.execute("CREATE UNIQUE INDEX candidates_dedupe ON candidates(pane,kind,text)")
    cur.execute("CREATE INDEX candidates_kind_text_ord ON candidates(kind,text,ord)")
    cur.execute("CREATE TABLE eligible (scope TEXT NOT NULL, ord INTEGER NOT NULL REFERENCES candidates(ord), PRIMARY KEY(scope,ord)) WITHOUT ROWID")
    cur.execute("CREATE TABLE totals (filter TEXT NOT NULL, scope TEXT NOT NULL, total INTEGER NOT NULL, PRIMARY KEY(filter,scope)) WITHOUT ROWID")

    if panes is None:
        panes = [(origin, 0, "main", "/bin/zsh", 1, 24)]
    if lines is None:
        lines = [(origin, 1, "test line 1")]
    if candidates is None:
        candidates = []

    cur.execute("INSERT INTO meta (key, value) VALUES ('origin', ?)", (str(origin),))
    cur.execute("INSERT INTO meta (key, value) VALUES ('pane_count', ?)", (str(len(panes)),))
    cur.execute("INSERT INTO meta (key, value) VALUES ('candidate_count', ?)", (str(len(candidates)),))
    cur.execute("INSERT INTO meta (key, value) VALUES ('created_ms', '0')")

    cur.executemany("INSERT INTO panes (id, ord, title, program, origin, rows) VALUES (?, ?, ?, ?, ?, ?)", panes)
    cur.executemany("INSERT INTO lines (pane, no, text) VALUES (?, ?, ?)", lines)
    cur.executemany("INSERT INTO candidates (ord, id, text, kind, pane, screen, line) VALUES (?, ?, ?, ?, ?, ?, ?)", candidates)

    for scope in ("tab", "pane", "screen"):
        if scope == "tab":
            scope_where = "1=1"
        elif scope == "pane":
            scope_where = f"pane = {origin}"
        else:
            scope_where = f"pane = {origin} AND screen = 1"
        cur.execute(f"""
            INSERT INTO eligible (scope, ord)
            SELECT '{scope}', MIN(ord)
            FROM candidates
            WHERE {scope_where}
            GROUP BY kind, text
        """)

    for filter_name in ("word", "line", "all"):
        if filter_name == "word":
            kind_cond = "c.kind = 'word'"
        elif filter_name == "line":
            kind_cond = "c.kind = 'line'"
        else:
            kind_cond = "c.kind NOT IN ('word', 'line')"
        for scope in ("tab", "pane", "screen"):
            cur.execute(f"""
                INSERT INTO totals (filter, scope, total)
                SELECT '{filter_name}', '{scope}', COUNT(*)
                FROM eligible e
                JOIN candidates c ON c.ord = e.ord
                WHERE e.scope = '{scope}' AND {kind_cond}
            """)

    conn.commit()
    conn.close()


class ExactRankingAndScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_exact_scoring_components(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [
            (1, 1, "exact abc"),
            (1, 2, "separated a_b_c"),
            (1, 3, "prefix xabc"),
        ]
        candidates = [
            (0, "1:0", "abc", "word", 1, 1, 1),
            (1, "1:1", "a_b_c", "word", 1, 1, 2),
            (2, "1:2", "xabc", "word", 1, 1, 3),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "abc")
        self.assertEqual(total, 3)
        self.assertEqual(len(results), 3)

        self.assertEqual(results[0]["text"], "abc")
        self.assertEqual(results[0]["hits"], [[0, 3]])

        self.assertEqual(results[1]["text"], "xabc")
        self.assertEqual(results[1]["hits"], [[1, 4]])

        self.assertEqual(results[2]["text"], "a_b_c")
        self.assertEqual(results[2]["hits"], [[0, 1], [2, 3], [4, 5]])

    def test_tie_break_by_ord_ascending(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "line 1"), (1, 2, "line 2")]
        candidates = [
            (5, "1:5", "test_item", "word", 1, 1, 1),
            (2, "1:2", "test_item2", "word", 1, 1, 2),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "test")
        self.assertEqual(total, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["ord"], 2)
        self.assertEqual(results[1]["ord"], 5)


class UnicodeAndAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_adversarial_ea_query_in_multibyte_text(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "source line with Ã©aéa")]
        candidates = [
            (0, "1:0", "Ã©aéa", "word", 1, 1, 1),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "éa")
        self.assertEqual(total, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Ã©aéa")
        self.assertEqual(results[0]["hits"], [[3, 5]])

    def test_astral_codepoints_hit_offsets(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "source with astral a😀b")]
        candidates = [
            (0, "1:0", "a😀b", "word", 1, 1, 1),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "ab")
        self.assertEqual(total, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["hits"], [[0, 1], [2, 3]])

    def test_non_ascii_folding_is_exact(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "accented line")]
        candidates = [
            (0, "1:0", "café", "word", 1, 1, 1),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "CAFÉ")
        self.assertEqual(total, 1)
        self.assertEqual(len(results), 0)

        total, results = search.search(self.db_path, "word", "pane", 1, "café")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["hits"], [[0, 4]])

    def test_ascii_folding_case_insensitive(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "ascii cases")]
        candidates = [
            (0, "1:0", "FOOBAR", "word", 1, 1, 1),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "foobar")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["hits"], [[0, 6]])


class LiteralLikeEscapingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_like_escaping_percent(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "line 1"), (1, 2, "line 2")]
        candidates = [
            (0, "1:0", "foo%bar", "word", 1, 1, 1),
            (1, "1:1", "fooxbar", "word", 1, 1, 2),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "o%b")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "foo%bar")
        self.assertEqual(results[0]["hits"], [[2, 5]])

    def test_like_escaping_underscore(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "line 1"), (1, 2, "line 2")]
        candidates = [
            (0, "1:0", "foo_bar", "word", 1, 1, 1),
            (1, "1:1", "fooxbar", "word", 1, 1, 2),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "o_b")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "foo_bar")
        self.assertEqual(results[0]["hits"], [[2, 5]])

    def test_like_escaping_backslash(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "line 1"), (1, 2, "line 2")]
        candidates = [
            (0, "1:0", "foo\\bar", "word", 1, 1, 1),
            (1, "1:1", "fooxbar", "word", 1, 1, 2),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "o\\b")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "foo\\bar")
        self.assertEqual(results[0]["hits"], [[2, 5]])


class KindScopeAndDedupeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_filter_and_scope_filtering(self):
        panes = [
            (1, 0, "main", "/bin/zsh", 1, 24),
            (2, 1, "other", "/bin/zsh", 0, 24),
        ]
        lines = [
            (1, 1, "origin line 1"),
            (1, 2, "origin line 2"),
            (2, 1, "other line 1"),
        ]
        candidates = [
            (0, "1:0", "token1", "word", 1, 1, 1),
            (1, "1:1", "line_text", "line", 1, 1, 2),
            (2, "1:2", "https://example.com", "url", 1, 0, 1),
            (3, "2:0", "token2", "word", 2, 0, 1),
            (4, "2:1", "git@github.com", "path", 2, 0, 1),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total_word, res_word = search.search(self.db_path, "word", "tab", 1, "token")
        self.assertEqual(total_word, 2)
        self.assertEqual(len(res_word), 2)

        total_word_pane, res_word_pane = search.search(self.db_path, "word", "pane", 1, "token")
        self.assertEqual(total_word_pane, 1)
        self.assertEqual(len(res_word_pane), 1)
        self.assertEqual(res_word_pane[0]["text"], "token1")

        total_line, res_line = search.search(self.db_path, "line", "tab", 1, "line")
        self.assertEqual(total_line, 1)
        self.assertEqual(len(res_line), 1)
        self.assertEqual(res_line[0]["kind"], "line")

        total_all, res_all = search.search(self.db_path, "all", "tab", 1, "git")
        self.assertEqual(total_all, 2)
        self.assertEqual(len(res_all), 1)
        self.assertEqual(res_all[0]["kind"], "path")

        total_screen, res_screen = search.search(self.db_path, "all", "screen", 1, "https")
        self.assertEqual(total_screen, 0)
        self.assertEqual(len(res_screen), 0)

    def test_dedupe_precedence_after_scope(self):
        panes = [
            (1, 0, "main", "/bin/zsh", 1, 24),
            (2, 1, "other", "/bin/zsh", 0, 24),
        ]
        lines = [
            (1, 1, "origin line"),
            (2, 1, "other line"),
        ]
        candidates = [
            (0, "2:0", "shared_word", "word", 2, 0, 1),
            (1, "1:0", "shared_word", "word", 1, 1, 1),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total_tab, res_tab = search.search(self.db_path, "word", "tab", 1, "shared")
        self.assertEqual(total_tab, 1)
        self.assertEqual(res_tab[0]["pane"], 2)

        total_pane, res_pane = search.search(self.db_path, "word", "pane", 1, "shared")
        self.assertEqual(total_pane, 1)
        self.assertEqual(res_pane[0]["pane"], 1)


class CapBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_cap_300_limit(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, i + 1, f"source line {i}") for i in range(350)]
        candidates = [
            (i, f"1:{i}", f"matching_word_{i:04d}", "word", 1, 1, i + 1)
            for i in range(350)
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "matching")
        self.assertEqual(total, 350)
        self.assertEqual(len(results), 300)

        for i in range(len(results) - 1):
            a = results[i]
            b = results[i + 1]
            score_a = a["ord"]
            score_b = b["ord"]
            self.assertLess(score_a, score_b)


class EmptyQueryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_empty_query_returns_top_300_ordered_by_ord(self):
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "line 1 text"), (1, 2, "line 2 text")]
        candidates = [
            (0, "1:0", "item0", "word", 1, 1, 1),
            (1, "1:1", "item1", "word", 1, 1, 2),
        ]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

        total, results = search.search(self.db_path, "word", "pane", 1, "")
        self.assertEqual(total, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["ord"], 0)
        self.assertEqual(results[0]["hits"], [])
        self.assertEqual(results[0]["source"], "line 1 text")
        self.assertEqual(results[1]["ord"], 1)
        self.assertEqual(results[1]["hits"], [])
        self.assertEqual(results[1]["source"], "line 2 text")


class MissingAndCorruptDbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.corrupt_path = self.tmp.name
        self.tmp.write(b"NOT A SQLITE DATABASE FILE\n")
        self.tmp.close()

    def tearDown(self):
        if os.path.exists(self.corrupt_path):
            os.remove(self.corrupt_path)

    def test_missing_db(self):
        missing_path = "/tmp/extrakto_nonexistent_test_db_12345.db"
        with self.assertRaises(FileNotFoundError):
            search.search(missing_path, "word", "pane", 1, "query")

        stderr = io.StringIO()
        stdout = io.StringIO()
        old_err, old_out = sys.stderr, sys.stdout
        try:
            sys.stderr, sys.stdout = stderr, stdout
            ret = search.main([missing_path, "word", "pane", "1", "query"])
        finally:
            sys.stderr, sys.stdout = old_err, old_out

        self.assertEqual(ret, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertTrue(stderr.getvalue().startswith("extrakto: "))

    def test_corrupt_db(self):
        with self.assertRaises(sqlite3.DatabaseError):
            search.search(self.corrupt_path, "word", "pane", 1, "query")

        stderr = io.StringIO()
        stdout = io.StringIO()
        old_err, old_out = sys.stderr, sys.stdout
        try:
            sys.stderr, sys.stdout = stderr, stdout
            ret = search.main([self.corrupt_path, "word", "pane", "1", "query"])
        finally:
            sys.stderr, sys.stdout = old_err, old_out

        self.assertEqual(ret, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertTrue(stderr.getvalue().startswith("extrakto: "))

    def test_origin_mismatch(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = tmp.name
        tmp.close()
        try:
            create_test_db(db_path, origin=1)
            with self.assertRaises(ValueError):
                search.search(db_path, "word", "pane", 2, "query")

            stderr = io.StringIO()
            stdout = io.StringIO()
            old_err, old_out = sys.stderr, sys.stdout
            try:
                sys.stderr, sys.stdout = stderr, stdout
                ret = search.main([db_path, "word", "pane", "2", "query"])
            finally:
                sys.stderr, sys.stdout = old_err, old_out

            self.assertEqual(ret, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertTrue(stderr.getvalue().startswith("extrakto: "))
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class CliProtocolAndUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        panes = [(1, 0, "main", "/bin/zsh", 1, 24)]
        lines = [(1, 1, "echo hello world")]
        candidates = [(0, "1:0", "hello", "word", 1, 1, 1)]
        create_test_db(self.db_path, origin=1, panes=panes, lines=lines, candidates=candidates)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_usage_wrong_argc(self):
        for args in (
            [self.db_path, "word", "pane", "1"],
            [self.db_path, "word", "pane", "1", "q", "extra"],
        ):
            stderr = io.StringIO()
            stdout = io.StringIO()
            old_err, old_out = sys.stderr, sys.stdout
            try:
                sys.stderr, sys.stdout = stderr, stdout
                ret = search.main(args)
            finally:
                sys.stderr, sys.stdout = old_err, old_out
            self.assertEqual(ret, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertTrue(stderr.getvalue().startswith("usage: "))

    def test_usage_non_integer_origin(self):
        stderr = io.StringIO()
        stdout = io.StringIO()
        old_err, old_out = sys.stderr, sys.stdout
        try:
            sys.stderr, sys.stdout = stderr, stdout
            ret = search.main([self.db_path, "word", "pane", "invalid_origin", "hello"])
        finally:
            sys.stderr, sys.stdout = old_err, old_out
        self.assertEqual(ret, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertTrue(stderr.getvalue().startswith("usage: "))

    def test_successful_ndjson_protocol(self):
        stderr = io.StringIO()
        stdout = io.StringIO()
        old_err, old_out = sys.stderr, sys.stdout
        try:
            sys.stderr, sys.stdout = stderr, stdout
            ret = search.main([self.db_path, "word", "pane", "1", "hello"])
        finally:
            sys.stderr, sys.stdout = old_err, old_out

        self.assertEqual(ret, 0)
        self.assertEqual(stderr.getvalue(), "")
        output = stdout.getvalue().splitlines()
        self.assertEqual(len(output), 2)

        header = json.loads(output[0])
        self.assertEqual(header, {"total": 1, "count": 1})

        row = json.loads(output[1])
        self.assertEqual(row["id"], "1:0")
        self.assertEqual(row["text"], "hello")
        self.assertEqual(row["kind"], "word")
        self.assertEqual(row["pane"], 1)
        self.assertIs(row["screen"], True)
        self.assertEqual(row["line"], 1)
        self.assertEqual(row["source"], "echo hello world")
        self.assertEqual(row["ord"], 0)
        self.assertEqual(row["hits"], [[0, 5]])


if __name__ == "__main__":
    unittest.main()
