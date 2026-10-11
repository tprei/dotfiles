import heapq
import json
import os
import sqlite3
import sys
from urllib.parse import quote

sys.dont_write_bytecode = True

CAP = 300
DELIMITER_BYTES = {9, 10, 11, 12, 13, 32, 45, 46, 47, 58, 95}
ASCII_FOLD_TABLE = bytes.maketrans(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    b"abcdefghijklmnopqrstuvwxyz",
)


def fold_char(ch: str) -> str:
    if "A" <= ch <= "Z":
        return chr(ord(ch) + 32)
    return ch


def merge_hits(positions: list[int]) -> list[list[int]]:
    if not positions:
        return []
    hits = []
    from_pos = positions[0]
    to_pos = positions[0] + 1
    for p in positions[1:]:
        if p == to_pos:
            to_pos = p + 1
        else:
            hits.append([from_pos, to_pos])
            from_pos = p
            to_pos = p + 1
    hits.append([from_pos, to_pos])
    return hits


def match_text(
    text: str,
    raw_bytes: bytes,
    folded_bytes: bytes,
    needles: list[bytes],
) -> tuple[bool, int, list[int]]:
    qlen = len(needles)
    byte_positions = []
    at = 0
    for needle in needles:
        found = folded_bytes.find(needle, at)
        if found == -1:
            return False, 0, []
        byte_positions.append(found)
        at = found + len(needle)

    for i in range(qlen - 2, -1, -1):
        next_pos = byte_positions[i + 1]
        byte_positions[i] = folded_bytes.rfind(needles[i], 0, next_pos)

    first_byte = byte_positions[0]
    boundary_hits = 0
    if first_byte == 0:
        boundary_hits += 1
    else:
        prev_byte = raw_bytes[first_byte - 1]
        if prev_byte in DELIMITER_BYTES:
            boundary_hits += 1
        elif 97 <= prev_byte <= 122 and 65 <= raw_bytes[first_byte] <= 90:
            boundary_hits += 1

    adjacent = 0
    for i in range(1, qlen):
        pos = byte_positions[i]
        prev_pos = byte_positions[i - 1]
        if pos == prev_pos + len(needles[i - 1]):
            adjacent += 1

        prev_byte = raw_bytes[pos - 1]
        if prev_byte in DELIMITER_BYTES:
            boundary_hits += 1
        elif 97 <= prev_byte <= 122 and 65 <= raw_bytes[pos] <= 90:
            boundary_hits += 1

    if raw_bytes[:first_byte].isascii():
        first_pos = first_byte
    else:
        first_pos = len(raw_bytes[:first_byte].decode("utf-8"))

    gaps = qlen - 1 - adjacent
    score = 100 * qlen - 5 * gaps - first_pos + 15 * boundary_hits + 20 * adjacent
    if len(text) == qlen:
        score += 1000

    return True, score, byte_positions


def open_ro_connection(db_path: str) -> sqlite3.Connection:
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"database file not found: {db_path}")
    abs_path = os.path.abspath(db_path)
    quoted_path = quote(abs_path, safe="/")
    uri = f"file:{quoted_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def search(
    db_path: str,
    filter_name: str,
    scope: str,
    origin: int,
    query: str,
) -> tuple[int, list[dict]]:
    if filter_name not in ("word", "line", "all"):
        raise ValueError(f"invalid filter: {filter_name}")
    if scope not in ("tab", "pane", "screen"):
        raise ValueError(f"invalid scope: {scope}")

    conn = open_ro_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = 'origin'")
        row = cur.fetchone()
        if row is None:
            raise ValueError("missing origin in meta")
        try:
            meta_origin = int(row[0])
        except ValueError:
            raise ValueError("invalid origin in meta")
        if meta_origin != origin:
            raise ValueError(f"origin mismatch: expected {meta_origin}, got {origin}")

        cur.execute("SELECT total FROM totals WHERE filter = ? AND scope = ?", (filter_name, scope))
        total_row = cur.fetchone()
        if total_row is None:
            raise ValueError(f"missing total for filter={filter_name}, scope={scope}")
        total = int(total_row[0])

        if filter_name == "word":
            kind_sql = "c.kind = 'word'"
        elif filter_name == "line":
            kind_sql = "c.kind = 'line'"
        else:
            kind_sql = "c.kind NOT IN ('word', 'line')"

        if not query:
            cur.execute(f"""
                SELECT c.id, c.text, c.kind, c.pane, c.screen, c.line, l.text AS source, c.ord
                FROM eligible e
                JOIN candidates c ON c.ord = e.ord
                JOIN lines l ON l.pane = c.pane AND l.no = c.line
                WHERE e.scope = ? AND {kind_sql}
                ORDER BY e.ord ASC
                LIMIT {CAP}
            """, (scope,))
            rows = cur.fetchall()
            results = [
                {
                    "id": r["id"],
                    "text": r["text"],
                    "kind": r["kind"],
                    "pane": r["pane"],
                    "screen": bool(r["screen"]),
                    "line": r["line"],
                    "source": r["source"],
                    "ord": r["ord"],
                    "hits": [],
                }
                for r in rows
            ]
            return total, results

        needles = [fold_char(ch).encode("utf-8") for ch in query]
        escaped_cps = []
        for ch in query:
            f_ch = fold_char(ch)
            if f_ch == "\\":
                escaped_cps.append("\\\\")
            elif f_ch == "%":
                escaped_cps.append("\\%")
            elif f_ch == "_":
                escaped_cps.append("\\_")
            else:
                escaped_cps.append(f_ch)
        like_pattern = "%" + "%".join(escaped_cps) + "%"

        cur.execute(f"""
            SELECT c.id, c.text, c.kind, c.pane, c.screen, c.line, c.ord
            FROM eligible e
            JOIN candidates c ON c.ord = e.ord
            WHERE e.scope = ? AND {kind_sql} AND c.text LIKE ? ESCAPE '\\'
        """, (scope, like_pattern))
        matching_rows = cur.fetchall()

        heap = []
        for r in matching_rows:
            text = r["text"]
            raw_bytes = text.encode("utf-8")
            folded_bytes = raw_bytes.translate(ASCII_FOLD_TABLE)
            matched, score, byte_positions = match_text(text, raw_bytes, folded_bytes, needles)
            if not matched:
                continue

            ord_val = r["ord"]
            heap_key = (score, -ord_val)
            item = (heap_key, ord_val, r, byte_positions)
            if len(heap) < CAP:
                heapq.heappush(heap, item)
            elif heap_key > heap[0][0]:
                heapq.heapreplace(heap, item)

        if not heap:
            return total, []

        sorted_items = sorted(heap, key=lambda x: (-x[0][0], x[1]))
        winner_ords = [item[1] for item in sorted_items]
        placeholders = ",".join("?" * len(winner_ords))
        cur.execute(
            f"SELECT c.ord, l.text AS source FROM candidates c JOIN lines l ON l.pane = c.pane AND l.no = c.line WHERE c.ord IN ({placeholders})",
            winner_ords,
        )
        source_by_ord = {r["ord"]: r["source"] for r in cur.fetchall()}

        results = []
        for item in sorted_items:
            r = item[2]
            bps = item[3]
            text = r["text"]
            if text.isascii():
                cp_positions = bps
            else:
                raw_b = text.encode("utf-8")
                cp_positions = [len(raw_b[:bp].decode("utf-8")) for bp in bps]
            results.append({
                "id": r["id"],
                "text": r["text"],
                "kind": r["kind"],
                "pane": r["pane"],
                "screen": bool(r["screen"]),
                "line": r["line"],
                "source": source_by_ord.get(r["ord"], ""),
                "ord": r["ord"],
                "hits": merge_hits(cp_positions),
            })
        return total, results
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        sys.stderr.write("usage: extract.py search <db> <filter> <scope> <origin> <query>\n")
        return 2
    db_path = argv[0]
    filter_name = argv[1]
    scope = argv[2]
    try:
        origin = int(argv[3])
    except ValueError:
        sys.stderr.write("usage: extract.py search <db> <filter> <scope> <origin> <query>\n")
        return 2
    query = argv[4]

    try:
        total, results = search(db_path, filter_name, scope, origin, query)
    except Exception as e:
        sys.stderr.write(f"extrakto: {e}\n")
        return 1

    lines = [json.dumps({"total": total, "count": len(results)}, ensure_ascii=False)]
    for r in results:
        lines.append(json.dumps(r, ensure_ascii=False))
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
