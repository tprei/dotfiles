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
- `tern/nav` is the window plugin behind `ctrl+h/j/k/l`, session cycling and agent focus (`plugin.nav.*`, bound in `keys.json`); `just tern-keys` links it before merging (`just tern-plugin` alone links it). nvim's split-edge handoff lives in `nvim/.config/nvim/lua/plugins/vim-tmux-navigator.lua`.
- Verified on 0.4.5, not stated in the docs: a `keybinds` array never consults a command's `available` (palette only); the window's `PaneInfo.program` is the shell-reported foreground command; `tern focus BLOCK` from a pane moves the window's focus; `tern open` in a remote host's pane is handled by that host's daemon and never reaches the window's `tern.route.open`; `cx.layout:focus` on a pane in another session switches to it.
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

## Refresh

Run `python3 scripts/sync_docs.py` from this skill's directory. It reads the site's table of contents, re-downloads every page and `tern-sdk.tar.gz`, and rewrites `references/docs/`, `references/sdk/`, and `references/toc.md`. `references/cookbook.md` is hand-written; re-check its citations after a refresh.
