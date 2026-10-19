---
name: tern
description: Tern terminal (Stencil) reference. Use when configuring Tern or writing for it: settings.json, keybinds, keymaps, plugins, Luau window/host plugins, CSS styling, layout, routing, lenses, blocks, remote hosts, or the Surface Protocol.
---

# Tern

Answer Tern configuration and plugin questions from the local mirror of https://docs.stencil.so/tern/ instead of guessing or browsing.

## Which machine applies what

Both setups happen, so first settle which machine shows the window and which runs the panes:

- Local: the window and its panes on one machine (the Mac, or `tern` inside WSL).
- Remote: the Mac window attached to WSL as a remote host (`tern remote`). WSL panes run in WSL's daemon, and one window can mix local and remote panes.

Each machine reads its own `settings.json` and plugins folder; nothing syncs between hosts.

| Config | Applied by |
|--------|------------|
| `keybinds`, `keymap`, `keymap_prefix`, window halves (`tern.bind`, `tern.command`, overrides, routes, chrome, layout, `tern.css`) | The machine showing the window, for every pane in it, remote ones included |
| Host halves (blocks, lenses, hooks, the `spawn` filter) | The machine whose panes they serve: WSL's daemon for WSL panes |
| Manifest `styles` | Either: a remote host's Ready plugins install theirs in your window; its `tern.css` sheets don't travel |
| `plugins`, `plugins_disabled` | Each machine, for its own plugins folder |

| Machine | `<config>` (`settings.json`, `plugins/`) | `<state>` (`plugin-data/<id>/`) |
|---------|------------------------------------------|-------------------------------|
| macOS | `~/Library/Application Support/Tern` | same |
| Linux, WSL | `~/.config/tern` | `~/.local/state/tern` |

`TERN_CONFIG_DIR` overrides both. Remote pitfalls:

- A plugin whose host half should serve WSL panes goes on WSL too: run `tern plugin install` in a pane on that host. Plugins with both halves go on both machines.
- Window-half `tern.fs` and `tern.process` act on the window's machine, so checking a remote pane's `pane.cwd` reads the wrong disk. Do file checks in a host half installed on that host.
- Disabling a plugin on the Mac leaves it on in WSL, and the other way round. **Reload plugins** reloads every attached host.
- Host halves log to `tern-daemon.log` on their own machine, window halves to the window's `tern.log`. Log folders: `~/Library/Logs/Tern` on macOS, `~/.local/state/tern/logs` on Linux and WSL, or `$STENCIL_LOG_DIR`. **Open logs and app state** opens the window machine's folder, so read a WSL host half's errors inside WSL. `STENCIL_LOG` works only in the environment of the process running the half: the window for window halves, that machine's daemon for host halves (`references/docs/guides/debugging.md#logs`).

Sources: `references/docs/guides/distribution.md#remote-hosts`, `references/docs/concepts/security.md#remote-hosts`, `references/docs/concepts/architecture.md#where-each-half-runs`, `references/docs/concepts/packages.md#directories`.

## Dotfiles and tools

- Keys live in `tern/keys.json` (`keymap`, `keymap_prefix`, `option_as_alt`, `keybinds`; the SDK docs never name `option_as_alt`). `just tern-keys` merges it into the current machine's `settings.json` with `jq '.[0] + .[1]'`, a shallow merge: each top-level key in `keys.json` replaces the one in `settings.json`, so the whole `keybinds` map is overwritten and chords added in Preferences are dropped. Add chords to `keys.json` instead. Stow can't own `settings.json` because Tern rewrites it on every preference change. Run it on the machine that shows the window (the Mac for the remote setup), then **Reload settings** (`reload_config`).
- On the Mac, `karabiner/assets/complex_modifications/macbook-left-modifiers.json` remaps the left modifiers, and its `frontmost_application_if`/`unless` conditions decide whether Tern (bundle id `so.stencil.tern`) gets the terminal or the GUI mapping. `keybinds` chords name the modifier Tern receives after the remap, so read the rule's current manipulators and conditions before choosing `ctrl`, `alt`, or `cmd`, and confirm a chord in Tern itself. A window running in WSL sees no Karabiner, and there `cmd`/`super` is the Windows key (`references/docs/reference/actions.md#chords`).
- Binary: `~/.local/bin/tern` in WSL. Run `tern --version` on each machine; the mirror tracks the published docs, which may lead or lag a build.
- Plugins: `tern plugin dir|list|link DIR|unlink ID|install SRC|remove ID|reload|types DIR` act on the machine you run them on.
- `tern/nav` is the window plugin behind `ctrl+h/j/k/l`, session cycling and agent focus (`plugin.nav.*`, bound in `keys.json`); `just tern-keys` links it before merging (`just tern-plugin` alone links it). Its only other interception is the dotfiles' own picker: when the focused block is `extrakto.picker`, nav forwards `ctrl+h/j/k/l` to the picker's query caret and result navigation instead of moving pane focus. nvim's split-edge handoff lives in `nvim/.config/nvim/lua/plugins/vim-tmux-navigator.lua`.
- `tern/extrakto` is the native picker behind `ctrl+a>tab` (`plugin.extrakto.open`), a window half plus a host half: the window opens the `extrakto.picker` block in a split under the focused pane and zooms it; the host half (`host.luau`) calls the bundled `tern/extrakto/extract.py` with `python3` directly on the pane's host, capturing each text pane's last 2000 lines with `tern capture --scrollback --surfaces` into a private SQLite catalog and searching it asynchronously (the 300 cap applies to rendered rows only, never the catalog); the origin is the `a` side of its Column split in `tern ls --json`. `tab` pastes with `tern send ID paste`, `enter` copies with `cx:copy`, and `ctrl-e` opens `$EDITOR` with `tern run` on the pane's machine; marking, filters, scopes, picker navigation keys, and dependency/install instructions are as the README's `tern/extrakto` entry (`just tern-plugin` on the window and pane machines, then **Reload plugins**; a pane machine needs `python3` 3.9+ and `tern` on the login shell's `PATH`; neither `fzf` nor a `tern-extrakto` link is required).
- Extrakto opens its split and zooms it in separate window callbacks, each under Tern's 50 ms budget. The zero-delay zoom callback checks that the picker is still the window's focused pane and skips an already-zoomed tab; keep the zoom out of the open handler.
- `tern/copymode` is the native copy mode plugin bound to `ctrl+a>[` and `alt+[` (`plugin.copymode.open`). At entry, the window half splits the origin pane down with host block `copymode.copy` (launch arg: the origin id modulo 2^44, its host-local id), then parks the origin, so the copy block takes the origin's exact slot while the process keeps running. The host half captures once with `capture.py`: `tern capture ID --html --scrollback --surfaces` streamed through `HTMLParser` into a private ANSI file (never through `tern.process.run` stdout, capped at 16 MiB), with `TERN_PANE`, `TERN_PANE_SOCKET` and `TERN_WINDOW_*` stripped from the CLI's environment so it reaches the daemon running the host half rather than whatever pane started that daemon. Keys go to the pure `engine.luau` (vi/herdr motions, `h/l` over a character and its combining marks, smart-case wrapping search, charwise and linewise selection); `view.luau` renders only the visible rows as `ui.ansi` with SGR overlays. `y`/`enter` run `cx:copy`; every exit then runs `cx:open("copymode://close")`, and the window's `tern.route.link` handler unparks the origin with `{focus = false}`, swaps it into the copy's slot with `cx.layout:move(origin, copy, "swap")`, then closes the copy, which restores the split ratios exactly. The `close_pane` override takes the same path. Records persist in `tern.kv`, shared by every window on the machine; an orphaned record (copy closed some other way) is recovered on `window_start`, `pane_closed` and every `focus` event.
- Verified on 0.4.5, not stated in the docs: a `keybinds` array never consults a command's `available` (palette only); the window's `PaneInfo.program` is the shell-reported foreground command; `tern focus BLOCK` from a pane moves the window's focus; `tern open` in a remote host's pane is handled by that host's daemon and never reaches the window's `tern.route.open`; `cx.layout:focus` on a pane in another session switches to it. Observed SDK gap: window navigation has no way to hand a native `Key` table to the focused block, so both plugins re-dispatch the key as a `text:` action whose payload is the key's escape sequence, and a text-bearing key event can carry a non-text key name (a paste arrives as name `paste` with `key.text` set), so `keys.luau` checks `key.text` before accepting it as query input. For isolated CLI commands, set `TERN_DAEMON_SOCKET` explicitly; this build's client can ignore `TERN_CONFIG_DIR` when choosing a socket while the daemon honors it.
- The refreshed mirror adds doc-only material (parked panes, `cx.agents`, whiteboard blocks, and the `references/docs/scripts/` harness); the published docs still name no copy mode.
- Verified on 0.8.3 (`e2b8656`), not stated in the docs: `tern capture --html --scrollback --surfaces` prints one `<pre>` of styled `<span>`s holding the whole retained grid plus flattened TSP surface text, while `--ansi` leaves surface text out. `cx.layout:unpark` dealt the pane beside the tab's largest pane every time it was observed, never beside the focused one as documented. A daemon-side close (`tern close`, for shells and blocks alike) sends the window no `pane_closed`, only a `focus` event when focus moves. Parked panes are missing from `tern ls` and, presumably, the host's `tern.pane.list()`. In a `--control` window, the daemon keeps every pane at 80×24 until the window is key (`window-focus on` in a script). A `remote loopback` host runs in the window process and inherits its environment, so its host-half children see the window's `TERN_DAEMON_SOCKET`; test host-local CLI calls against a second daemon behind `tern remote serve --user --listen 127.0.0.1:PORT --no-iroh --relay none --pkarr none` with temp `--access` and `--authorized-keys` files instead. `session:read` caps at 2000 lines and 64000 chars, and host-half `tern.pane` has only `write` and `list`. Copy-mode keys come from the dotfiles' `tern/copymode` plugin, not built-in Tern commands, so cite nothing upstream for them.
- Apply edits: **Reload settings** (`reload_config`), **Reload plugins** (`reload_plugins`), or `tern plugin reload`.

## Instructions

1. Start with `references/cookbook.md` for "how do I configure X": settings keys, keybind syntax, a personal config plugin, and window/host recipes with citations.
2. For anything else, find the page in `references/toc.md` (every page with its section headings), then read the page under `references/docs/`. Search across pages with `rg -n 'term' references/docs`.
3. When a guide and `references/docs/reference/*` disagree, the reference wins. Check API signatures in `references/sdk/tern.d.luau`.
4. Prefer adapting a complete plugin from `references/sdk/examples/` (each has a README) over writing one from scratch.
5. Use only command ids from `references/docs/reference/actions.md` and only CSS variables and selectors from `references/docs/styles/`. Don't invent `settings.json` keys: the docs publish no full schema, and `cx.settings` exposes the live tree to a window plugin.
6. For a new plugin, run `tern plugin types DIR` so luau-lsp sees the declarations this build ships, then `tern plugin link DIR`. `tern plugin list` reports the host half and folder problems but never shows a failing window entry as failed; check Preferences › Plugins or the "Plugin *name* failed to load" toast for that (`references/docs/reference/cli.md`).

## Where to look

| Task | Pages |
|------|-------|
| Which machine runs what (local vs remote host) | `references/docs/guides/distribution.md#remote-hosts`, `references/docs/concepts/architecture.md#where-each-half-runs`, `references/docs/guides/io.md` |
| Keys, commands, overrides | `references/docs/guides/commands.md`, `references/docs/reference/actions.md` |
| Tab, title, status line, global CSS | `references/docs/guides/chrome.md`, `references/docs/styles/` |
| Window layout, workspaces | `references/docs/guides/layout.md`, `references/sdk/examples/workspaces/` |
| File and link routing | `references/docs/guides/routing.md` |
| Shell hooks, spawn filter | `references/docs/guides/hooks.md`, `references/docs/reference/api-host.md` |
| Command lenses, blocks, views | `references/docs/guides/lenses.md`, `references/docs/guides/blocks.md`, `references/docs/guides/views.md`, `references/docs/elements/` |
| Manifest, directories, ids | `references/docs/concepts/packages.md`, `references/docs/reference/manifest.md` |
| CLI, errors, limits | `references/docs/reference/cli.md`, `references/docs/reference/errors.md`, `references/docs/reference/limits.md` |
| Native UI from any program | `references/docs/protocol/` |
| Scripted windows, screenshots and harness commands | `references/docs/scripts/` |

## Refresh

Run `python3 scripts/sync_docs.py` from this skill's directory. It reads the site's table of contents, re-downloads every page, resolves `stencil-hq/tern-sdk`'s default-branch head commit through the GitHub API, and unpacks only that commit archive's `plugins/` contents (`tern.d.luau`, `examples/`) into `references/sdk/`. It rewrites `references/docs/`, `references/sdk/`, and `references/toc.md`. `references/cookbook.md` is hand-written; re-check its citations after a refresh.
