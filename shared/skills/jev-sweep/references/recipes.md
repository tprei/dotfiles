# Jev sweep recipes

Python cells for omp's `eval` kernel. Run them in order and keep each cell's definitions in that cell, so an interrupt can't leave half of them behind. The kernel starts in the session cwd; set `ROOT` to the repo's absolute path anyway, since sweeps usually run in worktrees. Cells time out after 30 s by default: run the inventory cell with the eval `timeout` raised (600 or more on a first `npx` download), or run the scans in `bash` writing JSON and load that.

## Helpers

```python
import collections, hashlib, json, os, random, re, subprocess

ROOT = "/abs/path/to/repo"
EXCLUDE = ["!.git/**", "!node_modules/**", "!dist/**", "!build/**", "!*.generated.*", "!*.min.*"]
LINE_CAP, STATE_CAP = 240, 24_000

def run(args, timeout=120):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=timeout, check=False)

def rg_hits(pattern):
    args = ["rg", "--json", "-n", "--hidden", "--pcre2", "-e", pattern]
    for g in EXCLUDE:
        args += ["-g", g]
    hits = []
    for line in run(args + ["."]).stdout.splitlines():
        o = json.loads(line)
        if o["type"] == "match":
            d = o["data"]
            path, n = d["path"]["text"].removeprefix("./"), d["line_number"]
            hits.append((path, n, d["lines"].get("text", f"<non-utf8 {path}:{n}>").rstrip("\n")))
    return hits

def sg_hits(pattern, langs=("ts", "tsx")):
    globs = [a for g in EXCLUDE for a in ("--globs", g)]
    widest = {}
    for lang in langs:
        args = ["npx", "-y", "-p", "@ast-grep/cli", "ast-grep", "run", "-p", pattern, "-l", lang, "--json=stream", *globs, ROOT]
        for line in run(args, timeout=600).stdout.splitlines():
            m = json.loads(line)
            b = m["range"]["byteOffset"]
            key = (os.path.relpath(m["file"], ROOT), b["start"])
            if key not in widest or b["end"] > widest[key][0]:
                widest[key] = (b["end"], m["range"]["start"]["line"] + 1, m["text"])
    return [(path, line, text) for (path, _), (_, line, text) in widest.items()]

_files = {}
def lines_of(path):
    if path not in _files:
        with open(os.path.join(ROOT, path), errors="replace") as f:
            _files[path] = f.read().splitlines()
    return _files[path]

def clip(line):
    return line if len(line) <= LINE_CAP else line[:LINE_CAP] + " …[line clipped]"

def window(path, line, before=8, after=8):
    L = lines_of(path)
    lo, hi = max(0, line - 1 - before), min(len(L), line + after)
    return "\n".join(f"{i + 1:>5}{'>' if i + 1 == line else ' '} {clip(L[i])}" for i in range(lo, hi))

def norm(text):
    return re.sub(r"\s+", " ", text.strip())
```

`sg_hits` keeps the widest match per start offset, so a chained `x as unknown as T` counts once, while `f(a as X, b as Y)` and a cast nested inside a larger cast expression each count separately. `ast-grep` treats `ts` and `tsx` as separate languages; scan both. `$E as $T` skips `as const`. `npx -p` runs its command from the nearest `package.json` directory, not from `cwd`, so pass `ROOT` as the search path and relativize the results.

## Inventory and pre-filter, counts only

```python
raw = {
    "double-cast": rg_hits(r"\bas\s+unknown\s+as\b"),
    "empty-catch": rg_hits(r"\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*(\{\s*\}|undefined|null)\s*\)"),
    "assertion": [h for h in sg_hits("$E as $T") if not re.search(r"\bas\s+unknown\s+as\b", h[2].splitlines()[-1])],
}

def prefilter(category, path, line, text):
    if path.endswith((".md", ".mdx")):
        return "prose"
    return None

removed = collections.Counter()
for cat in raw:
    kept = []
    for hit in raw[cat]:
        reason = prefilter(cat, *hit)
        if reason:
            removed[(cat, reason)] += 1
        else:
            kept.append(hit)
    raw[cat] = kept
print({k: len(v) for k, v in raw.items()}, "removed:", dict(removed))
```

The `assertion` filter keeps a double cast out of two categories. Freeze `QUESTIONS` in its own cell before printing a single hit. The cells below expect a `choice` question with id `verdict`; add more questions under other ids.

## Evidence

Write one extractor per category whose deciding fact lives elsewhere, and check it by hand on 3 hits before trusting it. A bare-name `rg` for a callee picks up interfaces, same-named methods, and generated files. When the repo has a language server, ask it:

```python
r = await tool.write({"path": "xd://lsp", "i": "Resolving callee", "content": json.dumps(
    {"action": "definition", "file": "src/lib/sync/refresh.ts", "line": 152, "symbol": "refreshSettlement"})})
print(r["text"])
```

Run `{"action": "status"}` first. Without a server the call returns `No language server found for this action`; read that category instead of guessing.

Start with no evidence. Replace the default per category once its extractor passes the 3-hit check.

```python
def evidence(category, path, line, text):
    return None
```

## Clusters and states

Cluster ids hash the cluster's content, so rebuilding one category never renames another category's clusters or orphans an override.

```python
def fit(s):
    s = {**s, "match": clip(s["match"]), "count": len(s["locations"]), "locations": s["locations"][:50]}
    if len(json.dumps(s)) <= STATE_CAP:
        return s, "ok"
    s["context"] = s["context"][: STATE_CAP // 4] + "\n…[context clipped]"
    if len(json.dumps(s)) > STATE_CAP:
        s["evidence"] = "…[evidence dropped: over state cap]"
    return s, "clipped" if len(json.dumps(s)) <= STATE_CAP else "overflow"

def build_states(categories):
    clusters = {}
    for cat in categories:
        for path, line, text in raw[cat]:
            ev = evidence(cat, path, line, text)
            key = json.dumps([cat, norm(text), ev], sort_keys=True)
            c = clusters.setdefault(key, {"category": cat, "match": norm(text), "evidence": ev,
                                          "context": window(path, line), "locations": []})
            c["locations"].append(f"{path}:{line}")
    built, status = {}, collections.Counter()
    for key, c in clusters.items():
        cid = f"{c['category']}:{hashlib.sha1(key.encode()).hexdigest()[:10]}"
        s, st = fit({"id": cid, **c})
        status[st] += 1
        if st == "overflow":
            print("read instead of judging:", cid, s["locations"][0])
            continue
        built[cid] = s
    return built, status

states, status = build_states(list(raw))
print(len(states), "states from", sum(len(v) for v in raw.values()), "hits;", dict(status))
```

## Judge and tabulate

```python
batch = judge_batch(states, QUESTIONS, intent="Classifying sweep hits")
print(batch.id)
```

The batch runs on the host and outlives the cell. Its completion arrives as a background notice; tabulate after it lands. `max_tokens_exceeded` in an error means a state is too big: lower `STATE_CAP` or `LINE_CAP` and re-judge those keys.

```python
def tabulate(res, failed):
    rows = {}
    for k, s in states.items():
        r = res.get(k)
        if r is None:
            rows[k] = {"cat": s["category"], "label": "ERROR", "p": 0.0, "error": str(failed.get(k))[:200]}
            continue
        v = r["verdict"]
        rows[k] = {"cat": s["category"], "label": v["choice"], "p": max(v["probabilities"].values())}
    return rows

res, failed = dict(batch.results()), dict(batch.failed())
rows = tabulate(res, failed)
print(collections.Counter((r["cat"], r["label"]) for r in rows.values()))
```

## Audit

```python
def audit_set(rows, low=0.7, per_bucket=3, seed=0):
    rng = random.Random(seed)
    pick = {k for k, r in rows.items() if r["label"] == "ERROR" or r["p"] < low}
    buckets = collections.defaultdict(list)
    for k, r in rows.items():
        if k not in pick:
            buckets[(r["cat"], r["label"])].append(k)
    for keys in buckets.values():
        pick.update(rng.sample(sorted(keys), min(per_bucket, len(keys))))
    return sorted(pick)

for k in audit_set(rows):
    s, r = states[k], rows[k]
    print(f"## {k} {r['cat']} {r['label']} {r['p']:.2f} x{s['count']} {s['locations'][0]}")
    print(s["context"])
```

Record every verdict you read as `overrides[key] = (label, reason)`, for example `overrides["empty-catch:3f2a9c01de"] = ("legitimate", "trackedRead records the failure before rethrowing, src/lib/sync/refresh.ts:77")`. Final labels come from code, not memory:

```python
overrides = {}

def final_labels(rows, overrides):
    final = {k: overrides[k][0] if k in overrides else r["label"] for k, r in rows.items()}
    flipped = collections.Counter((rows[k]["label"], final[k]) for k in overrides if k in rows and rows[k]["label"] != final[k])
    return final, flipped
```

## Re-judge a category

When the audit overturns high-confidence verdicts in one category, fix that category's `evidence` extractor, then rebuild and judge the whole category:

```python
CATEGORY = "empty-catch"
fresh, status = build_states([CATEGORY])
for k in [k for k, s in states.items() if s["category"] == CATEGORY]:
    for table in (states, res, failed):
        table.pop(k, None)
    if k not in fresh:
        overrides.pop(k, None)
states.update(fresh)
batch2 = judge_batch(fresh, QUESTIONS, intent=f"Re-judging {CATEGORY}")
print(batch2.id, dict(status))
```

After its notice lands, merge and audit again:

```python
res.update(batch2.results())
failed.update(batch2.failed())
rows = tabulate(res, failed)
```

This loop is for evidence and state changes only. Any change to `QUESTIONS` invalidates every verdict it produced: rebuild and re-judge all states, and drop the overrides.
