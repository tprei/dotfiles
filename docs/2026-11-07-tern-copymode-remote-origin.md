# Tern copy mode: resolve the origin on the pane's host

## Problem

Over a remote host, copy mode opens and then fails with:

```
Capture: copymode: tern capture exited 1: tern capture: no block is called `335544345`
```

`tern/copymode/window.luau` passes `origin % 17592186044416` (2^44) as the copy block's launch argument, assuming a remote pane's window id is `tag << 44 | host_local_id`. On the Oracle host (Tern 0.9.12) the origin's host-local id is `85899345945` (`0x14_0000_0019`, printed by `tern ls` and `$TERN_PANE`), but the window's id modulo 2^44 is `335544345` (`0x1400_0019`). The window's packing doesn't keep the host-local id in the low 44 bits. Tern's docs (`references/docs/concepts/runtime.md`, `references/docs/reference/api-window.md#pane-and-tab-ids`) say ids are opaque: no arithmetic, pass them back unchanged. The plugin broke that rule; 0.8.3 loopback ids happened to be small enough to hide it.

`tern capture 85899345945 --html --scrollback --surfaces` with `TERN_PANE`, `TERN_PANE_SOCKET`, `TERN_WINDOW_KEY` and `TERN_WINDOW_SOCKET` stripped works on that host (32 KB of HTML), so capture itself is fine once it has the right id.

## Fix

The host half finds the origin's host-local id itself from the daemon's layout, the way `tern/extrakto/extract.py` does: right after the window's `cx.layout:split(origin, "down", {block = "copymode.copy"})`, the tab tree in `tern ls --json` holds `{"Split": {"axis": "Column", "a": {"Leaf": ORIGIN}, "b": {"Leaf": COPY}, ...}}`. That only holds while the origin is still in the tree, so the window no longer parks at entry. The host resolves the origin, asks the window to park it with a private link, and captures the pane; it does not wait for a park acknowledgement.

```mermaid
sequenceDiagram
  participant W as window.luau (window machine)
  participant H as host.luau (pane's host)
  participant P as capture.py
  W->>W: split origin down, block copymode.copy, no args; record {origin, copy, tab}
  H->>P: capture.py --origin-of COPY
  P->>P: tern ls --json, Column split with b == Leaf(COPY), a is a Leaf
  P-->>H: stdout "ORIGIN\n"
  H->>W: cx:open("copymode://park")
  par
    W->>W: cx.layout:park(record.origin)
  and
    H->>P: capture.py --origin ORIGIN --output PATH
    P->>P: tern capture --html --scrollback --surfaces
  end
```

No window id ever crosses to the host, and no id is computed with.

## Files

Edit only these files. No new files besides this plan.

### `tern/copymode/capture.py`

Replace `main`'s argument parsing and add an origin lookup mode. The snapshot mode (`--origin ID --output PATH --copy COPY`) keeps its conversion behavior and gains the copy id for window scoping.

```python
def find_tab(ls: dict, copy: int) -> dict:
    for session in ls["sessions"]:
        for tab in session["tabs"]:
            if any(block["id"] == copy for block in tab["blocks"]):
                return tab
    raise LookupError("pane %d is in no tab" % copy)


def split_origin(tree: dict, copy: int) -> Optional[int]:
    if "Split" not in tree:
        return None
    node = tree["Split"]
    if node["axis"] == "Column" and node["b"] == {"Leaf": copy} and "Leaf" in node["a"]:
        return node["a"]["Leaf"]
    origin = split_origin(node["a"], copy)
    if origin is None:
        origin = split_origin(node["b"], copy)
    return origin


def print_origin(copy_arg: str) -> int:
    try:
        copy = int(copy_arg)
    except ValueError:
        return fail("--origin-of needs a pane id, not %r" % copy_arg)
    env = tern_env(copy)
    try:
        result = subprocess.run(["tern", "ls", "--json"], capture_output=True, text=True, env=env)
    except FileNotFoundError:
        return fail("tern is not on PATH; install Tern 0.8.3 and its CLI on this host")
    if result.returncode != 0:
        detail = result.stderr.strip()
        message = "tern ls exited %d" % result.returncode
        return fail(message + (": %s" % detail if detail else ""))
    try:
        ls = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return fail("tern ls printed invalid JSON: %s" % e)
    try:
        tab = find_tab(ls, copy)
    except LookupError as e:
        return fail(str(e))
    origin = split_origin(tab["splits"], copy)
    if origin is None:
        return fail("can't find the pane copy mode split from")
    print(origin)
    return 0
```

`main` becomes:

```python
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="capture.py")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--origin")
    mode.add_argument("--origin-of")
    parser.add_argument("--output")
    parser.add_argument("--copy")
    args = parser.parse_args(argv)
    if args.origin_of is not None:
        return print_origin(args.origin_of)
    if args.output is None or args.copy is None:
        parser.error("--origin needs --output and --copy")
    # parse int(args.copy) (fail "--copy needs a pane id, not %r" on ValueError), then the
    # existing snapshot body from `try: fd = os.open(...)` onward, with env=tern_env(copy)
```

Add `import json` and `from typing import Optional`. No timeout argument on `subprocess.run`: the host half already kills the process after `CAPTURE_TIMEOUT_MS`.

Window scoping: `tern ls` and `tern capture` act on "the window whose sessions hold `$TERN_PANE`, else `$TERN_WINDOW_KEY`'s, else the first window". Both calls set `TERN_PANE` to the copy block's host-local id, so they work on the copy's window, and strip `TERN_PANE_SOCKET`, `TERN_WINDOW_KEY` and `TERN_WINDOW_SOCKET`, so they reach the daemon running the host half:

```python
def tern_env(copy: int) -> dict:
    env = {name: value for name, value in os.environ.items() if name not in PANE_IDENTITY}
    env["TERN_PANE"] = str(copy)
    return env
```

`start_capture` in `host.luau` passes the copy id: `'PATH="$HOME/.local/bin:$PATH"; exec python3 "$1" --origin "$2" --output "$3" --copy "$4"'` with `tostring(cx.pane)` after `path`. `CaptureTests.run_capture` appends `--copy 9`; the environment test sets `TERN_PANE=1234` and the three stripped variables, and asserts the fake `tern` sees `TERN_PANE == "9"` and none of the others, in both modes.

### `tern/copymode/host.luau`

1. Add `local PARK_URL = "copymode://park"` beside `CLOSE_URL`.
2. Add `find_origin(state: State, cx: BlockCx)` above `local copy: BlockDef<State>`:
   - argv: `{ shell(), "-lc", 'PATH="$HOME/.local/bin:$PATH"; exec python3 "$1" --origin-of "$2"', "_", tern.plugin.dir .. "/capture.py", tostring(cx.pane) }`, run with `tern.process.run(argv, { timeout_ms = CAPTURE_TIMEOUT_MS }, callback)` inside the same `pcall` shape as `start_capture`.
   - Callback: `if gone(state, cx.pane) then return end`. On `result.status ~= 0`: `state.model.status = "error"`, `state.model.message = failure_message(result, "Finding the pane to capture")`, `cx:render()`, return.
   - Parse `local origin = tonumber(string.match(result.stdout, "(%d+)%s*$") or "")`. If `origin == nil or origin <= 0`: error status with message `"Copy mode couldn't tell which pane to capture"`, `cx:render()`, return.
   - Otherwise: `state.origin = origin`, `cx:save()`, `cx:open(PARK_URL)`, `start_capture(state, cx, origin)`.
3. In `init`, drop the launch-argument path entirely: rename the parameter to `_args`, delete the `if origin_id == nil and type(args[1]) == "string"` block, and delete the `else` branch that sets "Copy mode couldn't tell which pane to capture" (that message now lives in `find_origin`). Keep the saved restore (`saved.origin`, `saved.path`) as is: it stores the host-local id the host resolved. When a restart restores an origin without a usable path, the timer recaptures using `state.origin` without resolving the layout again.
4. In the zero-delay timer in `init`: `if state.snapshot ~= nil then load_snapshot(...) elseif state.origin ~= nil then start_capture(...) else find_origin(state, cx) end`.
5. Everything else (`start_capture`, `request_close`, keys) stays. Change `save` so it returns nil when `state.origin == nil`, returns `{ origin = state.origin, path = state.snapshot }` when `state.model.status == "ready"` and `state.snapshot ~= nil`, and otherwise returns `{ origin = state.origin }`.

### `tern/copymode/window.luau`

1. Delete `ORIGIN_MODULO`. Add `local PARK_URL = "copymode://park"`.
2. In `open`, split with `cx.layout:split(origin, "down", { block = COPY_BLOCK })` (no `args`), and delete the `cx.layout:park(origin)` block (lines `local ok, why = cx.layout:park(origin)` through its `end`). Keep the `tab == nil` check, the record, `dirty`, and `persist()`.
3. Add a `park(cx: WindowCx, record: Record)` local function above `tern.command`:
   ```lua
   local function park(cx: WindowCx, record: Record)
   	local info = pane_of(cx, record.origin)
   	if info == nil or info.parked == true then
   		return
   	end
   	local ok, why = cx.layout:park(record.origin)
   	if not ok then
   		cx:toast("error", "Copy mode couldn't freeze the pane", tostring(why))
   		finish(cx, record, true)
   	end
   end
   ```
   A missing origin leaves the copy open; its capture fails and shows that, and `q` closes it through `restore`'s existing "origin pane exited" path.
4. In `tern.route.link`, handle both private URLs from the copy pane:
   ```lua
   tern.route.link(function(link, cx)
   	if link.pane == nil or (link.url ~= CLOSE_URL and link.url ~= PARK_URL) then
   		return nil
   	end
   	local record = record_for_copy(link.pane)
   	if link.url == PARK_URL then
   		if record ~= nil then
   			park(cx, record)
   		end
   		return { handled = true }
   	end
   	-- existing CLOSE_URL body unchanged from `if record ~= nil then restore(...)`
   end)
   ```
5. Leave `restore`'s swap behavior unchanged: after the missing-origin check, always swap the origin into the copy's slot before closing the copy, whether or not it was parked.

### `tern/copymode/tests/test_capture.py`

Add a `FindOriginTests(unittest.TestCase)` class next to `CaptureTests`, reusing its fake-`tern`-on-`PATH` setup style (`write_tern`), that runs `capture.py --origin-of 9` and asserts:

- a `tern ls --json` fake printing one tab with `{"Split": {"axis": "Column", "a": {"Leaf": 5}, "b": {"Leaf": 9}}}` and blocks 5 and 9 makes stdout exactly `"5\n"` and exit 0;
- the same with the copy nested under a `Row` split still prints the Column's `a` leaf;
- a tree where 9 is a Column's `a` side (copy above its origin) exits 1 with `can't find the pane copy mode split from` on stderr;
- an id that's in no tab exits 1 with `is in no tab`;
- a fake `tern ls` exiting 2 with stderr `boom` exits 1 and reports `tern ls exited 2: boom`;
- with `TERN_PANE=1234`, `TERN_PANE_SOCKET`, `TERN_WINDOW_KEY` and `TERN_WINDOW_SOCKET` set in the test, the fake sees `TERN_PANE == "9"` and none of the other three (the fake writes its environment to a file the test reads), for both `--origin-of 9` and snapshot mode. The fake also records `sys.argv[1:]`; assert `["ls", "--json"]` for origin lookup and `["capture", "17", "--html", "--scrollback", "--surfaces"]` for snapshot mode.

Existing tests change only by `run_capture` appending `--copy 9`.

### `README.md`

In the `tern/copymode` bullet (line 35), describe entry accurately: the window splits the origin down with the copy block, the host half finds the origin from `tern ls --json` on the pane's host, asks the window to park it with `copymode://park`, then captures. Remove any claim about passing the origin id.

### `shared/skills/tern/SKILL.md`

- Line 49: replace "(launch arg: the origin id modulo 2^44, its host-local id), then parks the origin" with the new flow: no launch argument; the host half runs `capture.py --origin-of COPY`, which finds the origin as the `a` leaf of the copy's Column split in `tern ls --json`, then `cx:open("copymode://park")` makes the window's `tern.route.link` handler park the origin; capture runs on the host-local id. Keep the rest of the bullet.
- Append to the "Verified on 0.8.3" bullet (line 52) a sentence: on 0.9.12 a remote pane's window id modulo 2^44 isn't its host-local id (host-local `85899345945`, window id mod 2^44 `335544345`), so never derive host ids from window ids; resolve them on the host.

## Constraints

- No id arithmetic anywhere. No fallback to the old launch argument, no compatibility branch for old records, no suppressions.
- No comments in code.
- Snapshot mode's HTML-to-ANSI conversion, file privacy and cleanup stay unchanged.
- `tern/extrakto` is out of scope.

## Verification

From the worktree root:

```sh
python3 -m unittest discover -s tern/copymode/tests -v
```

Expected: every existing `CaptureTests` case and the new `FindOriginTests` cases pass.

End to end, load the plugin in an isolated daemon and headless window attached to it as a remote host (built separately under `/tmp/tern-copymode-repro/`) and confirm:

1. Entering copy mode on a remote pane shows the snapshot, not the `no block is called` error.
2. The origin parks after the copy block resolves it; `q` restores the origin into its slot.
3. Quitting while the copy block still shows an error closes the copy and leaves the origin in place.
