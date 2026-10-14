# Tern native copy mode

## Scope

Target Tern 0.8.3. Add a native host block with entry bindings `ctrl+a>[` and `alt+[`. Capture all retained scrollback once on the pane's host, including Tern remote sessions. Keep the process running behind the snapshot. Render only the viewport, preserving captured ANSI colors. `g`, `gg`, and `G` jump buffer ends. No Neovim pager, key-table emulation, capped window reads, compatibility shims, or silent truncation.

## Files and ownership

- Add `tern/copymode/plugin.toml`, `window.luau`, `host.luau`, `capture.py`, and capture regression tests for host capture and lifecycle.
- Add `tern/copymode/model.luau` and `engine.luau` for pure navigation, search, and selection.
- Add `tern/copymode/view.luau` and `copymode.css` for the native viewport and status/search dock.
- Edit `tern/keys.json`, `justfile`, `README.md`, and `shared/skills/tern/SKILL.md` for installation, bindings, and remote-host instructions.
- Edit `shared/skills/tern/scripts/sync_docs.py`; regenerate `references/docs/`, `references/sdk/`, and `references/toc.md`; correct stale cookbook citations and API claims. The SDK comes from the resolved immutable GitHub commit's `plugins/` subtree.
- No deletions outside generated mirror replacement.

## Domain contract

`model.luau` exports:

```luau
export type Line = { text: string, ansi: string }
export type Position = { line: number, column: number }
export type Model = {
    lines: { Line }, cursor: Position, anchor: Position?, linewise: boolean,
    top: number, left: number, cols: number, rows: number, preferred: number,
    query: string, searching: boolean, searchDirection: number,
    searchOrigin: Position?, searchDraft: string, count: string,
    status: "loading" | "ready" | "error", message: string,
}
export type Result = "changed" | "copy" | "quit" | "ignored"
```

Positions are one-based Unicode codepoint columns, never UTF-8 bytes. `left` is the first displayed codepoint. `top` is the first displayed line. Retain only original text and ANSI strings per line; compute codepoint mappings lazily for cursor/visible lines.

`engine.luau` exports `new(): Model`, `load(model: Model, lines: {Line}): ()`, `resize(model: Model, cols: number, rows: number): ()`, `key(model: Model, key: Key): Result`, `selection(model: Model): string?`, `selected(model: Model, line: number): (number?, number?)`, `length(text: string): number`, `byte(text: string, column: number): number`, and `width(codepoint: number): number`. `selected` returns inclusive codepoint selection bounds for a line. Empty lines have a cursor cell; clipping must retain combining codepoints next to their base. Renderer uses the same width function as visibility calculations.

Motions include h/j/k/l and arrows, w/b/e and W/B/E, 0/^/$, paragraph {/}, page/half-page keys, g/gg/G, counts, and home/end. Search `/` and `?` is literal, smart-case, wraps, and supports n/N; Escape while editing cancels back to the original position. v/Space selects characters, V selects lines, o swaps endpoints. Escape clears a selection before exiting; q exits immediately. y/Enter copies the selection, or the current line when no selection is active, then exits. Ignore unsupported keys. Clamp counts without huge repeat loops. UTF-8 selection must not split a codepoint.

## Capture and host contract

`capture.py` accepts `--origin HOST_LOCAL_ID --output PRIVATE_PATH` and calls `tern capture ID --html --scrollback --surfaces`. Stream the unified HTML through stdlib `HTMLParser` into a private ANSI file, preserving decoded text, newlines, terminal colors, and native surface text. Restore the inherited foreground/background and text style when colored spans end. ANSI-only capture excludes native surfaces and must not be used. Report only a small completion summary. Never pass scrollback through `tern.process.run` stdout (16 MiB cap). Propagate subprocess errors and remove failed capture files. No 2,000-line tail or character cap.

The host `copymode.copy` block's first launch argument is the host-local origin id. The window passes `origin % 17592186044416` (2^44), as verified against a loopback remote daemon. All CLI and filesystem work runs in the host half. Invoke the helper with python3 through the existing login-shell PATH convention. Load capture with `tern.fs.read`, parse ANSI into `{text, ansi}` lines in batches scheduled with zero-delay timers to stay within the host callback budget, and release the raw string after parsing. Strip only CSI/OSC controls for motion/copy text. Do not recapture while browsing. Trim the capture's terminal padding at the end, but do not trim meaningful line whitespace. Snapshot errors show an actionable error with an exit key, not an empty successful buffer.

`host.luau` imports engine/model/view, handles asynchronous capture, and rechecks that the block still exists before applying callbacks. Entry state is loading; `engine.load` puts the cursor on the last line with the last page in view. On copy, call `cx:copy(text)` followed by `cx:open("copymode://close")`. On quit, remove the snapshot and only request the close URL; the host never judges origin liveness, because parked panes are missing from the host's pane list, and the window handles a dead origin. Do not exit the host block before the window restores the origin. Sweep only this plugin's orphan snapshot files. `save` persists only the origin/snapshot data needed to reload the current block without changing the frozen snapshot. `capture.py` strips `TERN_PANE`, `TERN_PANE_SOCKET`, and `TERN_WINDOW_*` from the CLI's environment so it reaches the daemon that runs the host half.

## Window lifecycle

Register `plugin.copymode.open` and `plugin.copymode.close`. Reject non-terminal/non-agent or floating origins. Re-entering from an active copy block closes it rather than creating another block. Split origin down with `{block = "copymode.copy", args = {tostring(origin % 2^44)}}`, then park origin. Persist only owned `{origin, copy, tab}` associations with `tern.kv`, decoded at the storage boundary. If park fails, close the added copy leaf and report the real failure. Both operations stay within the 50 ms budget verified by the runtime probe.

Handle exact private `copymode://close` links only from an owned `copymode.copy` pane, returning `{handled = true}`. Unpark the origin with `{focus = false}`, swap it into the copy's slot with `cx.layout:move(origin, copy, "swap", {focus = false})`, close the copy leaf, and focus origin; `unpark` alone deals beside the tab's largest pane, so the swap is what restores the exact slot. Override `close_pane` only for owned copy panes to run the same restore path. Recover a recorded origin whose copy disappeared on `window_start`, `pane_closed`, and every `focus` event, since daemon-side closes send no `pane_closed`; never unpark unrelated user-deck panes. Preserve stored ownership through plugin reload and initialize from it. Preserve unrelated focus when recovering a background copy. The existing unequal split ratios must remain unchanged. Do not use global snapshot restore to overwrite layout changes made while browsing.

## Native view

`view.luau` exports `render(model: Model): BlockView`. Draw only `model.rows` lines at `model.top`, horizontally clipped to `model.cols` with the cursor in view. Use `ui.ansi` with original SGR color runs, add distinct cursor/selection/search styling, and restore the original SGR state after an overlay. Do not feed the whole history to the renderer or use fallback rows with its debug marker. A wrapped root column contains the viewport. The dock shows copy/select/search mode, line position and total, selected range when present, active query/error/loading state, and concise key hints. CSS scopes to copymode surface/roles and existing theme variables. No invented theme variables or styling of other plugins.

## Integration

Add both keys to `tern/keys.json` with action `plugin.copymode.open`. Add `tern plugin link "{{ justfile_directory() }}/tern/copymode"` to `tern-plugin`; `tern-keys` inherits it. Update README and skill with exact key behavior, frozen snapshot semantics, no artificial history cap, requirements (Tern 0.8.3, python3, tern on the pane host's login PATH), and installation on both the window machine and every pane host. Reload settings on the window; reload plugins on all attached hosts. Remote IDs must not be guessed by host-side tree walks after park.

## Verification

After all edits, generate types from 0.8.3 into a temporary directory, run available Luau type checks with no suppressions, and execute permanent behavior tests once. Run the real 0.8.3 application under an isolated config, daemon, and control endpoint with the actual plugin. Capture screenshots outside the repo. Prove both entry chords, thousands of retained lines, g/G and search beyond 2,000 lines, Unicode selection, reversed and multiline selection, clipboard results, normal exit and external close, reload, unequal split restoration, ongoing origin output, and loopback remote capture/clipboard. Do not touch user's unrelated panes or settings. Rerun sync_docs.py once after integration and validate regenerated SDK/citations. Run an adversarial enemy review after implementation and fix demonstrated defects. Remove throwaway verification files from the repo; retain only consumer-visible regression tests and existing documentation updates.
