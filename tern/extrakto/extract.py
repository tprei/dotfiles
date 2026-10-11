#!/usr/bin/env python3

import json
import os
import sqlite3
import subprocess
import sys
import time
from typing import Optional
from urllib.parse import quote

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, ROOT)

from extrakto import Extrakto, get_lines

FULL_LINES = 2000
PREVIEW_LINES = 8
USAGE = "usage: extract.py capture <pane> <db>\n       extract.py search <db> <filter> <scope> <origin> <query>"


def run_tern(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tern", *args], check=True, capture_output=True, text=True, timeout=20)


def find_tab(ls: dict, me: int) -> dict:
    for session in ls["sessions"]:
        for tab in session["tabs"]:
            if any(block["id"] == me for block in tab["blocks"]):
                return tab
    raise LookupError(f"pane {me} is in no tab")


def split_origin(tree: dict, me: int) -> Optional[int]:
    if "Split" not in tree:
        return None
    node = tree["Split"]
    if node["axis"] == "Column" and node["b"] == {"Leaf": me} and "Leaf" in node["a"]:
        return node["a"]["Leaf"]
    origin = split_origin(node["a"], me)
    if origin is None:
        origin = split_origin(node["b"], me)
    return origin


def find_origin(tree: dict, me: int) -> int:
    origin = split_origin(tree, me)
    if origin is None:
        raise LookupError("can't find the pane extrakto split from")
    return origin


def text_blocks(tab: dict, me: int) -> list[int]:
    return [block["id"] for block in tab["blocks"] if block["id"] != me and block["program"] != ""]


def pane_lines(pane: int) -> list[str]:
    text = run_tern("capture", str(pane), "--surfaces", "--scrollback").stdout
    lines = text.removesuffix("\n").split("\n")
    return lines[-FULL_LINES:]


def line_candidates(lines: list[str]) -> list[tuple[str, str, int]]:
    word = Extrakto(alt=False, prefix_name=False)
    alt = Extrakto(alt=True, prefix_name=False)
    word_enabled = "word" in set(word.keys())
    enabled_alt = set(alt.keys())
    alt_names = [name for name in alt.all() if name in enabled_alt]
    results: list[tuple[str, str, int]] = []
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index]
        if word_enabled:
            for text in word["word"].filter(line):
                results.append(("word", text, index))
        for name in alt_names:
            for text in alt[name].filter(line):
                results.append((name, text, index))
        for text in get_lines(line):
            results.append(("line", text, index))
    return results


def capture(ls: dict, me: int, lines_by_pane: dict[int, list[str]], db_path: str) -> dict:
    tab = find_tab(ls, me)
    origin = find_origin(tab["splits"], me)
    blocks = {block["id"]: block for block in tab["blocks"]}
    order = text_blocks(tab, me)
    pane_order = [origin] + [pane for pane in reversed(order) if pane != origin]

    candidates_rows = []
    seen = set()
    cand_ord = 0
    for pane in pane_order:
        block = blocks[pane]
        lines = lines_by_pane[pane]
        screen_start = len(lines) - block["rows"]
        count = 0
        for kind, text, index in line_candidates(lines):
            key = (pane, kind, text)
            if key in seen:
                continue
            seen.add(key)
            cand_id = f"{pane}:{count}"
            screen = 1 if index >= screen_start else 0
            candidates_rows.append((cand_ord, cand_id, text, kind, pane, screen, index + 1))
            count += 1
            cand_ord += 1

    panes_meta = [
        {
            "id": pane,
            "title": blocks[pane]["title"],
            "program": blocks[pane]["program"],
            "origin": pane == origin,
            "lines": lines_by_pane[pane][-PREVIEW_LINES:],
        }
        for pane in order
    ]

    panes_rows = [
        (
            pane,
            ord_idx,
            blocks[pane]["title"],
            blocks[pane]["program"],
            1 if pane == origin else 0,
            blocks[pane]["rows"],
        )
        for ord_idx, pane in enumerate(pane_order)
    ]

    lines_rows = []
    for pane in pane_order:
        for idx, text in enumerate(lines_by_pane[pane], 1):
            lines_rows.append((pane, idx, text))

    created_ms = int(time.time() * 1000)
    meta_rows = [
        ("origin", str(origin)),
        ("pane_count", str(len(panes_meta))),
        ("candidate_count", str(len(candidates_rows))),
        ("created_ms", str(created_ms)),
    ]

    uri = "file:%s?mode=rw" % quote(os.path.abspath(db_path), safe="/")
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("BEGIN TRANSACTION")
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute(
            "CREATE TABLE panes (id INTEGER PRIMARY KEY, ord INTEGER NOT NULL, title TEXT NOT NULL, "
            "program TEXT NOT NULL, origin INTEGER NOT NULL, rows INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE lines (pane INTEGER NOT NULL REFERENCES panes(id), no INTEGER NOT NULL, "
            "text TEXT NOT NULL, PRIMARY KEY(pane,no)) WITHOUT ROWID"
        )
        conn.execute(
            "CREATE TABLE candidates (ord INTEGER PRIMARY KEY, id TEXT NOT NULL, text TEXT NOT NULL, "
            "kind TEXT NOT NULL, pane INTEGER NOT NULL REFERENCES panes(id), screen INTEGER NOT NULL, "
            "line INTEGER NOT NULL)"
        )
        conn.execute("CREATE UNIQUE INDEX candidates_dedupe ON candidates(pane,kind,text)")
        conn.execute("CREATE INDEX candidates_kind_text_ord ON candidates(kind,text,ord)")
        conn.execute(
            "CREATE TABLE eligible (scope TEXT NOT NULL, ord INTEGER NOT NULL REFERENCES candidates(ord), "
            "PRIMARY KEY(scope,ord)) WITHOUT ROWID"
        )
        conn.execute(
            "CREATE TABLE totals (filter TEXT NOT NULL, scope TEXT NOT NULL, total INTEGER NOT NULL, "
            "PRIMARY KEY(filter,scope)) WITHOUT ROWID"
        )

        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta_rows)
        conn.executemany(
            "INSERT INTO panes (id, ord, title, program, origin, rows) VALUES (?, ?, ?, ?, ?, ?)",
            panes_rows,
        )
        conn.executemany("INSERT INTO lines (pane, no, text) VALUES (?, ?, ?)", lines_rows)
        conn.executemany(
            "INSERT INTO candidates (ord, id, text, kind, pane, screen, line) VALUES (?, ?, ?, ?, ?, ?, ?)",
            candidates_rows,
        )

        conn.execute(
            "INSERT INTO eligible (scope, ord) SELECT 'tab', MIN(ord) FROM candidates GROUP BY kind, text"
        )
        conn.execute(
            "INSERT INTO eligible (scope, ord) SELECT 'pane', MIN(ord) FROM candidates WHERE pane = ? GROUP BY kind, text",
            (origin,),
        )
        conn.execute(
            "INSERT INTO eligible (scope, ord) SELECT 'screen', MIN(ord) FROM candidates WHERE pane = ? AND screen = 1 GROUP BY kind, text",
            (origin,),
        )

        conn.execute(
            """INSERT INTO totals (filter, scope, total) VALUES
('word', 'tab', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'tab' AND c.kind = 'word')),
('word', 'pane', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'pane' AND c.kind = 'word')),
('word', 'screen', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'screen' AND c.kind = 'word')),
('all', 'tab', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'tab' AND c.kind NOT IN ('word', 'line'))),
('all', 'pane', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'pane' AND c.kind NOT IN ('word', 'line'))),
('all', 'screen', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'screen' AND c.kind NOT IN ('word', 'line'))),
('line', 'tab', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'tab' AND c.kind = 'line')),
('line', 'pane', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'pane' AND c.kind = 'line')),
('line', 'screen', (SELECT COUNT(*) FROM eligible e JOIN candidates c ON e.ord = c.ord WHERE e.scope = 'screen' AND c.kind = 'line'))"""
        )

        conn.execute("COMMIT")
    finally:
        conn.close()

    return {
        "origin": origin,
        "db": db_path,
        "panes": panes_meta,
        "candidates": len(candidates_rows),
    }


def fail(message: str) -> int:
    print("extrakto: %s" % message, file=sys.stderr)
    return 1


def process_failure(e: subprocess.CalledProcessError) -> int:
    stderr = e.stderr.strip() if e.stderr else ""
    return fail(f"{e.cmd[0]} exited {e.returncode}: {stderr}")


def timeout_failure(e: subprocess.TimeoutExpired) -> int:
    cmd = " ".join(e.cmd)
    return fail("%s timed out after %ds" % (cmd, e.timeout))


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "search":
        import search
        return search.main(argv[1:])
    if cmd != "capture" or len(argv) != 3:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        me = int(argv[1])
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2
    db_path = argv[2]
    try:
        ls = json.loads(run_tern("ls", "--json").stdout)
        tab = find_tab(ls, me)
        find_origin(tab["splits"], me)
        lines_by_pane = {pane: pane_lines(pane) for pane in text_blocks(tab, me)}
        result = capture(ls, me, lines_by_pane, db_path)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except LookupError as e:
        return fail(str(e))
    except subprocess.CalledProcessError as e:
        return process_failure(e)
    except subprocess.TimeoutExpired as e:
        return timeout_failure(e)
    except (json.JSONDecodeError, OSError, sqlite3.Error, TypeError) as e:
        return fail(str(e))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
