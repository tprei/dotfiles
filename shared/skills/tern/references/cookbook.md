# Tern configuration cookbook

Recipes for configuring Tern with `settings.json` and small personal plugins. Every recipe cites the doc page it comes from; when a guide and `docs/reference/*` disagree, the reference wins. Links are relative to `references/`. Plugin-authoring tutorials for blocks, lenses and the Surface Protocol live in `docs/`, not here.

## Files and applying changes

Tern uses two directories per machine. `<config>` holds `settings.json` and the plugins folder; `<state>` holds per-plugin data and, on Linux, the log folder. `TERN_CONFIG_DIR` set overrides both directories, not the log folder; `$STENCIL_LOG_DIR` moves that.

| What | macOS | Linux/WSL |
| --- | --- | --- |
| `<config>` | `~/Library/Application Support/Tern` | `$XDG_CONFIG_HOME/tern` (`~/.config/tern`) |
| `<state>` | `~/Library/Application Support/Tern` | `$XDG_STATE_HOME/tern` (`~/.local/state/tern`) |
| Settings | `<config>/settings.json` | `<config>/settings.json` |
| Plugins folder | `<config>/plugins/` (`tern plugin dir` prints it) | `<config>/plugins/` |
| Plugin data folder | `<state>/plugin-data/<id>/` | `<state>/plugin-data/<id>/` |
| Logs | `~/Library/Logs/Tern` | `~/.local/state/tern/logs` |

`$STENCIL_LOG_DIR` set replaces the log folder. Host halves log to `tern-daemon.log`, window halves to the window's `tern.log`; a file rotates at 16 MiB. `STENCIL_LOG=warn,stencil=info,tern::plugin=debug` keeps `print` and `tern.log.info/debug` lines, which the default filter drops, and must be in the environment of the process that runs the half: the window for window halves, the session daemon for host halves. A process reads `STENCIL_LOG` when it starts, and the daemon keeps the environment it started with, so setting it on the Mac does nothing for WSL host halves; restart that machine's daemon with it. **Open logs and app state** opens the window machine's log folder; a WSL host half's log is `~/.local/state/tern/logs/tern-daemon.log` inside WSL. [docs/concepts/packages.md#directories](docs/concepts/packages.md#directories), [docs/concepts/runtime.md#logs](docs/concepts/runtime.md#logs), [docs/guides/debugging.md#logs](docs/guides/debugging.md#logs)

A plugin is a directory under the plugins folder, or a `<id>.path` link to one (`tern plugin link DIR` writes it). An installed package is a copy at `<config>/plugins/<id>`; a linked package loads from where it is, which is what you want while editing. [docs/concepts/packages.md#the-plugins-folder](docs/concepts/packages.md#the-plugins-folder), [docs/guides/distribution.md#linking-for-development](docs/guides/distribution.md#linking-for-development)

How a hand edit takes effect:

- `settings.json`: the daemon re-reads it at every reload, but a window keeps the settings it holds until told to read them again. After editing by hand, run **Reload settings** (command `reload_config`) and then **Reload plugins** (`reload_plugins`) from the palette. `open_config` opens `settings.json`, `open_logs` opens the log folder. [docs/guides/distribution.md#turning-plugins-on-and-off](docs/guides/distribution.md#turning-plugins-on-and-off), [docs/reference/actions.md#commands](docs/reference/actions.md#commands)
- Plugin files: Tern watches the plugins folder and every linked folder; changes batch over 300 ms, so saving a file usually reloads within about 300 ms. `tern plugin reload` makes the daemon re-read `settings.json` and the plugins folder and reload every plugin; it prints the new catalog and exits 1 when a plugin failed or the folder has a problem. It needs a running daemon (`no daemon running` otherwise); `install`, `remove`, `link` and `unlink` work without one and apply at next start. [docs/concepts/lifecycle.md#watching](docs/concepts/lifecycle.md#watching), [docs/reference/cli.md#tern-plugin-reload](docs/reference/cli.md#tern-plugin-reload)
- What survives a reload: `tern.kv` and the data folder persist; running blocks restart from their last saved state; hooks, the spawn filter and window registrations are rebuilt from the new entry; `window_start` runs only for plugins that have not run it in that window; a hook disabled by a tripped budget is enabled again. [docs/concepts/lifecycle.md#what-survives-a-reload](docs/concepts/lifecycle.md#what-survives-a-reload)

### Local and remote machines

Each machine reads its own `settings.json` and plugins folder; nothing syncs. With your window on the Mac and this WSL machine attached as a remote host, both topologies apply:

| Piece | Window and panes on one machine | Mac window, WSL remote host |
| --- | --- | --- |
| Keybinds, `keymap`, `keymap_prefix`, `swap_ctrl_cmd` | That machine's `settings.json` | The Mac's: keys live in the window (inferred: the keymap is window state, and each machine reads its own `settings.json`; no page says so outright) [docs/concepts/architecture.md#why-the-split-exists](docs/concepts/architecture.md#why-the-split-exists) |
| Window-half plugins (commands, binds, overrides, routes, chrome, layout, CSS) | That machine's plugins folder | The Mac's plugins folder; they style and act on every pane in the window, remote ones included |
| Host-half plugins (hooks, spawn filter, lenses, blocks) | That machine's plugins folder | The WSL machine's plugins folder; your host half never hears about a remote host's panes, the remote one does |
| `plugins`, `plugins_disabled` | Each machine's own file gates its own halves | Disabling a plugin on the Mac does not disable it on the host, and the other way round |
| Manifest `styles` | Install as `plugin:local:<id>:styles` | Either machine; a remote host's Ready plugins install their manifest styles in your windows as `plugin:<slot>:<id>:styles`, `<slot>` being the window's number for that host (`docs/concepts/packages.md` and `docs/concepts/security.md` write it `<host>`) |
| `tern.css` sheets | Install in the local window | Only the Mac's window halves can add them; a remote host's `tern.css` never reaches your windows |
| `tern.fs`, `tern.process`, `pane.cwd` checks | The one machine's disk | The window half reads the Mac's disk, so a `pane.cwd` that names a host path is the wrong machine to check it on |

Installing runs on the machine whose folder it changes: run `tern plugin install` or `tern plugin link` in a pane on the remote host to install there, in a Mac terminal to install for the window. [docs/concepts/architecture.md#where-each-half-runs](docs/concepts/architecture.md#where-each-half-runs), [docs/concepts/security.md#remote-hosts](docs/concepts/security.md#remote-hosts), [docs/guides/hooks.md#where-hooks-run](docs/guides/hooks.md#where-hooks-run), [docs/guides/io.md#which-machine-which-thread](docs/guides/io.md#which-machine-which-thread), [docs/guides/chrome.md#global-css](docs/guides/chrome.md#global-css), [docs/guides/debugging.md#checking-the-wrong-machine](docs/guides/debugging.md#checking-the-wrong-machine)

## settings.json keys

The SDK docs publish no full settings schema; the keys below are those named in `references/docs/` and `sdk/tern.d.luau`, with only what those state. `cx.settings` exposes the whole preference tree to window plugins: `get(key)` reads a value or subtree, `list(prefix?)` maps dotted leaf keys to values, `describe(key)` returns `{type, enum, range, default, nullable, doc}`, `themes()` lists installed themes, `keybinds()` returns your overrides, and `set`, `set_many`, `bind` and `unbind` write. Unknown keys, invalid types and overlapping paths fail without changing preferences. [docs/reference/api-window.md#settings-cx](docs/reference/api-window.md#settings-cx)

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `plugins` | boolean | `true` | `false` loads no plugin at all on that machine. [docs/concepts/packages.md#settings](docs/concepts/packages.md#settings) |
| `plugins_disabled` | array of plugin ids | `[]` | Listed ids stay installed but unloaded (status Disabled). [docs/concepts/packages.md#settings](docs/concepts/packages.md#settings) |
| `keybinds` | map: chord to an action name, an array of action names (priority order), `"unbind"`, or `[]` | not documented | The user keybind layer, above every other layer. An entry replaces every binding of its keys; `"unbind"` or `[]` removes one without replacing it. [docs/guides/commands.md#plugin-actions-in-settingsjson](docs/guides/commands.md#plugin-actions-in-settingsjson), [docs/guides/commands.md#keymap-layering](docs/guides/commands.md#keymap-layering) |
| `keymap` | string, a keyboard preset name (`tmux` is the documented example) | not documented | The preset layer, between Tern's defaults and plugin binds. [docs/guides/commands.md#keymap-layering](docs/guides/commands.md#keymap-layering) |
| `keymap_prefix` | not documented beyond the name | not documented | Named beside `keymap` in the preset layer; the docs give no value format. [docs/guides/commands.md#keymap-layering](docs/guides/commands.md#keymap-layering) |
| `swap_ctrl_cmd` | not documented beyond the name | not documented | On macOS with it set, `cmd` names the Super/Windows key as on a PC keyboard; see [Keybinds](#keybinds). [docs/reference/actions.md#chords](docs/reference/actions.md#chords) |
| `command_lenses` | boolean | on | Settings › Terminal › **Native command output**; off gives no command any lens, built-in or plugin. [docs/guides/lenses.md#turning-lenses-off](docs/guides/lenses.md#turning-lenses-off) |
| `theme_dark`, `theme_light` | theme name or nothing | not documented (absent follows the default) | Named only in `sdk/tern.d.luau`: set one to pin the dark/light theme, nil follows the default; `cx.settings:themes()` lists installed names. |
| `new_tabs` | not documented beyond the name | not documented | Decides the directory a new tab starts in, which `cx.layout:new_tab` uses when its launch names none. [docs/guides/layout.md#arranging-panes](docs/guides/layout.md#arranging-panes) |
| `font_size` | number | not documented | The root name; `terminal.font_size` is the alias `cx.settings` accepts for it, shown as the canonical-alias example. [docs/reference/api-window.md#settings-cx](docs/reference/api-window.md#settings-cx) |
| `carly.model`, `notebook.start_on_open`, `sqlite.drop.quoted` | named only as `cx.settings` call examples | not documented | Illustrate dotted paths and nested patches. [docs/reference/api-window.md#settings-cx](docs/reference/api-window.md#settings-cx) |

The window's effective bindings (defaults, preset, plugins, your overrides) are visible at run time with `cx.actions:keys()`. [docs/reference/api-window.md#actions-cx](docs/reference/api-window.md#actions-cx)

## Keybinds

Chords are spelled the same in `settings.json` `keybinds` and `tern.bind`:

- `+`-joined modifiers `ctrl`, `alt` (or `opt`), `shift`, `cmd` (or `super`), then one key: `ctrl+alt+shift+s`, `cmd+shift+j`.
- The key is a character as the layout types it (`ctrl+shift+2`, `cmd+plus`), a named key, `f1` to `f20`, or a physical key (`cmd+digit_1`, `ctrl+key_a`, `alt+bracket_left`).
- `>` joins a sequence: `ctrl+a>c` is Ctrl+A then C. A modifier alone is its key tapped, and taps appear only in sequences of taps, each within half a second of the last (`shift>shift`, `cmd>cmd`); any other key or a click ends them.
- On Windows and Linux, and on macOS with `swap_ctrl_cmd` set, `ctrl` is the Ctrl key and `cmd`/`super` is the Windows or Super key; on macOS without it, `cmd` is the Command key. [docs/reference/actions.md#chords](docs/reference/actions.md#chords), [docs/guides/commands.md#binds](docs/guides/commands.md#binds)

An entry's value is one action name, an array of action names in priority order (a press runs the first that applies where focus is), `"unbind"`, or `[]`. `"unbind"` is special to `settings.json`: `tern.bind(chord, "unbind")` is left out. [docs/guides/commands.md#plugin-actions-in-settingsjson](docs/guides/commands.md#plugin-actions-in-settingsjson), [docs/reference/actions.md#keymap-actions](docs/reference/actions.md#keymap-actions)

The keymap is built in layers, each taking its keys from the layers under it: Tern's defaults, then the preset (`keymap` and `keymap_prefix`), then every plugin's `tern.bind` and command `keys` in plugin id order, then your `keybinds`. Plugins only add keys: a plugin bind whose keys the defaults or preset already bind, or that starts or extends one of their sequences, is left out with a `plugin bind left out` log warning and no toast. Your `keybinds` always win. [docs/guides/commands.md#keymap-layering](docs/guides/commands.md#keymap-layering)

Action names: the built-in commands (`new_tab`, `split_right`, `close_pane`, `layout:rail`, `move_pane:left`, and so on; `actions.md`'s prose counts 167 while its tables list 168 ids, so treat the section as the source of ids), all listed in [docs/reference/actions.md#commands](docs/reference/actions.md#commands), plus keymap-only actions (`palette`, `goto_tab:N`, `last_tab`, `focus_pane:DIR`, `resize_split:DIR`, `text:BYTES`), view chords (`edit.*`, `editor.*`, `markdown.*`, `git.*`, `sqlite.*`, `notebook.*`, `board.*`), and plugin actions `plugin.<plugin>.<id>`. Only command ids work with `tern.override` and `cx:command`; `text:BYTES` writes escaped bytes to the focused program (`\e`, `\r`, `\n`, `\t`, `\\`, `\xHH`). The `editor.*` family is rejected on a sequence in `settings.json` and acts on one chord only; `markdown.*` likewise. [docs/reference/actions.md#names-at-a-glance](docs/reference/actions.md#names-at-a-glance), [docs/reference/actions.md#keymap-actions](docs/reference/actions.md#keymap-actions)

```json
{
	"keymap": "tmux",
	"keybinds": {
		"ctrl+a>c": "new_tab",
		"ctrl+a>v": "split_right",
		"ctrl+a>z": "zoom",
		"ctrl+a>h": "focus_pane:left",
		"ctrl+a>shift+h": "move_pane:left",
		"alt+digit_1": "goto_tab:1",
		"ctrl+shift+v": "paste",
		"cmd+a": "text:\\x01",
		"cmd+shift+p": "unbind",
		"ctrl+alt+shift+s": "plugin.mine.scratch",
		"ctrl+alt+shift+h": ["focus_pane:left", "previous_tab"]
	}
}
```

Every id and chord above is documented syntax: `focus_pane:left` is a keymap action, `previous_tab` and `paste` are commands, and the array form runs the first action that applies where focus is. The docs don't say whether `focus_pane:left` counts as not applying when no pane sits to the left, so test the fallback before relying on it. [docs/reference/actions.md#commands](docs/reference/actions.md#commands), [docs/reference/actions.md#keymap-actions](docs/reference/actions.md#keymap-actions)

Your dotfiles keep these keys in `tern/keys.json` (`keymap` `tmux`, `keymap_prefix` `ctrl+a`, `option_as_alt` `both`, a key no SDK doc names, and the `keybinds` map). `just tern-keys` shallow-merges it into the current machine's `settings.json` with `jq '.[0] + .[1]'`: every top-level key in keys.json replaces the one in settings.json, so the whole `keybinds` map is replaced and chords added in Preferences are dropped on the next run; add chords to keys.json instead. Run `just tern-keys` on the machine that shows the window (the Mac in the remote setup), then **Reload settings**; run it inside WSL only when WSL shows its own windows. Tern rewrites `settings.json` on preference changes, which is why the workflow merges instead of symlinking.

## A personal config plugin

Keep personal commands, binds, overrides, chrome and CSS in a small plugin instead of growing `keybinds` forever. Anywhere outside the plugins folder is fine:

```text
~/src/mine/
  plugin.toml
  window.luau
  mine.css
```

```toml
schema = 1
id = "mine"
name = "Mine"
version = "0.1.0"
description = "Personal keys, a command and chrome."
window = "window.luau"
styles = ["mine.css"]
```

Create `mine.css` (empty is fine) before linking: a missing styles file fails `tern plugin link` with `DIR is not a plugin: cannot read style mine.css: …`. [docs/reference/manifest.md#styles](docs/reference/manifest.md#styles)

```lua
--!strict

tern.command({
	id = "scratch",
	title = "Open scratch file",
	icon = "file",
	keys = { "ctrl+alt+shift+s" },
	run = function(cx)
		cx:open(tern.plugin.data .. "/scratch.md", "beside")
	end,
})
```

Link, type-check, check status, reload:

```sh
tern plugin link ~/src/mine
tern plugin types ~/src/mine
tern plugin list
tern plugin reload
```

`link` writes `<plugins>/mine.path` and the daemon reloads; saving a file reloads within about 300 ms after that. `types` writes `tern.d.luau` beside your entries; point luau-lsp at it as a definitions file (`luau-lsp.platform.type: "standard"`, `luau-lsp.sourcemap.enabled: false`, `luau-lsp.types.definitionFiles: {"@tern": "tern.d.luau"}`) and regenerate it after upgrading Tern. `list` prints `mine 0.1.0 Mine — 0 blocks, 0 lenses, window  ready`; a window entry that fails shows Failed in Preferences but not in `list`, which reads the host catalog. [docs/guides/getting-started.md#link-it](docs/guides/getting-started.md#link-it), [docs/guides/getting-started.md#set-up-type-checking](docs/guides/getting-started.md#set-up-type-checking), [docs/reference/cli.md#tern-plugin-types](docs/reference/cli.md#tern-plugin-types), [docs/guides/debugging.md#the-catalog](docs/guides/debugging.md#the-catalog)

Add `host = "host.luau"` to the manifest only when you want the spawn filter, host events, blocks or lenses. The host half must be linked or installed on the machine whose panes it serves; the window half on the machine showing the windows (see [Local and remote machines](#local-and-remote-machines)). [docs/guides/distribution.md#remote-hosts](docs/guides/distribution.md#remote-hosts)

Both CSS doors work at once: manifest `styles` files are concatenated (256 KiB cap) and installed as the sheet `plugin:local:mine:styles` before the window entry runs, with or without one, and `tern.css(name, source)` adds or replaces a named sheet at run time. [docs/guides/chrome.md#global-css](docs/guides/chrome.md#global-css)

## Window-half recipes

### Bind a chord to a built-in action

```lua
tern.bind("ctrl+alt+shift+n", "new_tab")
tern.bind("ctrl+alt+shift+r", "split_right")
```

Chords that Tern's defaults or the preset already bind are left out at keymap build, logged as `plugin bind left out`. Under the `tmux` preset with prefix `ctrl+a`, `ctrl+a>…` chords the preset owns are left out too; the preset's contents are not documented, so check the effective bindings with `cx.actions:keys()` before choosing. [docs/guides/commands.md#binds](docs/guides/commands.md#binds), [docs/guides/commands.md#keymap-layering](docs/guides/commands.md#keymap-layering)

### Bind a chord to a function

```lua
tern.bind("ctrl+alt+shift+y", function(cx)
	local pane = cx.session:focused()
	if pane then
		cx:run(pane, "git status\r")
	end
end)
```

The function gets the action `plugin.<plugin>.bind.<n>`, counted from registration order, so prefer a `tern.command` when the user should be able to rebind it from `settings.json`. [docs/guides/commands.md#binds](docs/guides/commands.md#binds)

### Register a palette command with default keys

```lua
tern.command({
	id = "scratch",
	title = "Open scratch file",
	icon = "file",
	keys = { "ctrl+alt+shift+s" },
	run = function(cx)
		cx:open(tern.plugin.data .. "/scratch.md", "beside")
	end,
})
```

The action is `plugin.mine.scratch`, bindable from `settings.json` `keybinds` like any other name; `group` defaults to the manifest `name`, and an optional `available(cx) -> boolean` hides the row where it does not apply. [docs/guides/commands.md#commands](docs/guides/commands.md#commands), [docs/reference/api-window.md#terncommand](docs/reference/api-window.md#terncommand)

### Override a built-in command

```lua
tern.override("new_tab", function(cx)
	cx:toast("info", "Opening a tab")
	cx:command("new_tab")
	return true
end)
```

Returning truthy skips the built-in; the recursion guard makes `cx:command` inside a handler run Tern's own command with no overrides and no routes, so this cannot loop. Only command ids can be overridden, never `palette`, `goto_tab:N` or view chords. [docs/guides/commands.md#overrides](docs/guides/commands.md#overrides), [docs/guides/commands.md#the-recursion-guard](docs/guides/commands.md#the-recursion-guard)

### Retitle tabs, the window, and add status segments

```lua
tern.chrome.tab_title(function(tab)
	if tab.name then
		return nil
	end
	return string.match(tab.cwd or "", "([^/]+)/*$")
end)

tern.chrome.window_title(function(win)
	if win.tab == nil then
		return nil
	end
	return win.space .. " · " .. win.tab
end)

tern.chrome.status(function(pane)
	if pane.program == "kubectl" then
		return { { text = "k8s", icon = "box", tone = "accent", command = "plugin.mine.contexts" } }
	end
	return nil
end)
```

Formatters are pure, cached per input, and budgeted at 4 ms; returning `nil` keeps Tern's own. When a segment depends on data outside its input, keep it in an upvalue and call `tern.chrome.refresh()` from a timer, event or command after it changes. [docs/guides/chrome.md#formatters](docs/guides/chrome.md#formatters), [docs/guides/chrome.md#status-segments](docs/guides/chrome.md#status-segments), [docs/guides/chrome.md#refreshing](docs/guides/chrome.md#refreshing)

### Global CSS and theme variables

```lua
tern.css("status", [[
#statusline .sl-plugin[data-plugin="mine"] { color: var(--accent); }
]])
```

```css
.sf-card[data-role='mine.summary'] {
	background: light-dark(rgb(from var(--accent) r g b/6%), rgb(from var(--accent) r g b/12%));
}

.sf-row[data-role='mine.failed'] {
	background: rgb(from var(--bad) r g b/10%);
	box-shadow: inset 2px 0 0 var(--bad);
}
```

Color only through variables so light and dark follow the theme: text steps `--t1` to `--t4`, `--accent` for rings and tints, `--accent-fill` under white text, status colors `--ok`, `--warn`, `--bad`, surfaces `--page`, `--panel`, `--card`. Scope with your block's `[data-surface='plugin.<plugin>.<block>']` on `.sf-main`/`.sf-dock`/`.sf-layer`, lens blocks as `.sf-block[data-role='lens.plugin.<plugin>.<lens>']`, and your own nodes' `[data-role]`. The full variable and selector lists are in [docs/styles/variables.md](docs/styles/variables.md) and [docs/styles/css.md](docs/styles/css.md). [docs/guides/chrome.md#useful-selectors](docs/guides/chrome.md#useful-selectors), [docs/styles/variables.md#light-and-dark](docs/styles/variables.md#light-and-dark), [docs/styles/variables.md#kit-tokens-text-and-lines](docs/styles/variables.md#kit-tokens-text-and-lines)

### Layout at window open and workspaces

```lua
local ROOT = (tern.getenv("HOME") or "") .. "/work/stencil"

tern.on("window_start", function(cx)
	for _, tab in cx.session:tabs() do
		if tab.name == "stencil" then
			return
		end
	end
	if not tern.fs.exists(ROOT) then
		return
	end
	cx.layout:tab({
		name = "stencil",
		cwd = ROOT,
		split = "right",
		{ launch = { command = "nvim" } },
		{ launch = { command = "cargo watch -x check" } },
	})
end)
```

`window_start` runs once per plugin per window after the session settles, so the tab check matters: restored sessions bring their tabs back, and every new window would otherwise add another one. `cx.layout:new_tab(launch)`, `split(target, dir, launch)`, `focus`, `close`, `move` and `resize` arrange single panes; a `cwd` deeper in a workspace spec overrides one above it. [docs/guides/layout.md#a-workspace-at-launch](docs/guides/layout.md#a-workspace-at-launch), [docs/guides/layout.md#workspaces](docs/guides/layout.md#workspaces)

In a Mac window attached to WSL, `tern.getenv` and `tern.fs.exists` read the Mac, while `cx.layout:tab` opens on the current session's host: a `ROOT` checked on the Mac can name a pane opened on WSL, which then starts at home instead. Open the workspace only when the current session runs on the machine that has `ROOT`, for example when `cx.hosts:current().kind == "local"` (`cx.hosts:current()` returns the current session's host with a `kind` of `"local"` or `"remote"`). [docs/guides/layout.md#arranging-panes](docs/guides/layout.md#arranging-panes), [docs/reference/api-window.md#sessions-and-hosts-cx](docs/reference/api-window.md#sessions-and-hosts-cx), [docs/guides/debugging.md#checking-the-wrong-machine](docs/guides/debugging.md#checking-the-wrong-machine)

### Route file opens and links

```lua
tern.route.open(function(req, _cx)
	if string.match(req.path, "%.tfplan$") then
		return { block = "terraform.plan", args = { req.path } }
	end
	return nil
end)

tern.route.link(function(link, cx)
	local key = string.match(link.url, "^ticket://(%u+%-%d+)$")
	if key then
		return { url = "https://tracker.example.com/browse/" .. key }
	end
	return nil
end)
```

`route.open` handlers run before the built-in open until one returns a decision (`block`, `url`, `path`, `handled`); `nil` passes on. Gate on `req.origin` when some paths should stay text: `tern open` in a pane arrives as `cli` and is how `EDITOR='tern open --wait'` works, so leave those alone unless you open a block. [docs/guides/routing.md#two-routes](docs/guides/routing.md#two-routes), [docs/guides/routing.md#decisions](docs/guides/routing.md#decisions), [docs/guides/routing.md#tern-open-from-a-pane](docs/guides/routing.md#tern-open-from-a-pane)

## Host-half recipes

### The spawn filter

```lua
tern.on("spawn", function(spec: SpawnSpec): SpawnSpec?
	spec.env.EDITOR = "nvim"
	if string.match(spec.cwd or "", "^/srv/") then
		spec.program = "/usr/bin/bash"
		spec.args = { "-l" }
	end
	return spec
end)
```

The filter rewrites every shell pane before it starts on that host. `env` holds only what Tern adds on top of the inherited environment, so add and override but never rebuild the table: a returned `env` is the complete set and keys missing from it are dropped. Return the spec you received, modified. The pane waits at most 50 ms per plugin, `tern.process.run` and `tern.fetch` answers arrive too late, and plugins run in id order, each seeing the previous one's result. [docs/guides/hooks.md#the-spawn-filter](docs/guides/hooks.md#the-spawn-filter), [docs/reference/api-host.md#the-spawn-filter](docs/reference/api-host.md#the-spawn-filter), [docs/reference/events.md#the-spawn-filter](docs/reference/events.md#the-spawn-filter)

### Shell hooks

```lua
tern.on("command_finished", function(ev: CommandFinishedEvent, cx: EffectCx)
	if ev.took_ms >= 30000 then
		cx:toast("info", ev.line, string.format("exit %d after %ds", ev.status, ev.took_ms // 1000))
	end
end)

tern.on("cwd", function(ev, _cx)
	if ev.path:match("/node_modules$") then
		tern.pane.write(ev.pane, "cd ..\r")
	end
end)
```

Host events fire where the panes run, with no window open, and the effect `cx` (`toast`, `open`, `copy`) reaches every window showing that pane. `command_started` and `command_finished` need shell integration; `command_finished` fires only when the start was seen. Leave the `"\r"` off a `tern.pane.write` to put the text on the prompt for the person to confirm. [docs/guides/hooks.md#events](docs/guides/hooks.md#events), [docs/reference/events.md#host-events](docs/reference/events.md#host-events), [docs/reference/api-host.md#ternpanewrite](docs/reference/api-host.md#ternpanewrite)

## Troubleshooting

`tern plugin list` prints the running daemon's catalog, one line per plugin, then one per problem. Status is `ready`, `disabled`, or `failed: ` with the first error line; `problem DIR: ERROR` marks a folder entry that is not a usable plugin. With no daemon it reads the folder without running Lua, so `ready` only means the manifest parsed. A window entry that fails to load never shows as failed here: check Preferences for the worse of the two. [docs/reference/cli.md#tern-plugin-list](docs/reference/cli.md#tern-plugin-list), [docs/guides/debugging.md#the-catalog](docs/guides/debugging.md#the-catalog)

Where failures land: a broken folder is a problem line plus one "N plugins have problems" toast; a host entry that fails sets `failed` in `list`; a window entry that fails toasts "Plugin <name> failed to load" in that window; a handler that raises, returns the wrong shape, or trips its budget toasts "Plugin <name>: <hook> failed" with the error's first line and logs `plugin handler failed` with the traceback. CSS errors never raise; they log `plugin style sheet has errors` with the sheet name. [docs/guides/debugging.md#where-failures-show](docs/guides/debugging.md#where-failures-show), [docs/reference/errors.md#handler-failures](docs/reference/errors.md#handler-failures)

Messages worth memorizing:

| Message | Meaning and fix |
| --- | --- |
| `no plugin.toml` | A folder in the plugins directory has no manifest; not a plugin, listed as a problem. [docs/reference/errors.md#plugins-folder-problems](docs/reference/errors.md#plugins-folder-problems) |
| `invalid id "<id>" (lowercase letters, digits and -, 1-32 long)` | Manifest `id` breaks `^[a-z][a-z0-9-]{0,31}$`. Same page. |
| `needs a host or window entry` | The manifest names neither `host` nor `window`. Same page. |
| `missing entry <path>` | A named entry file does not exist. Same page. |
| `duplicate id <id>` | An earlier entry in name order already has this id; remove or rename one. Same page. |
| `block <id> is declared in plugin.toml but not defined with tern.block.define` | The manifest declares it; the host entry never defines it. Same for lenses with `tern.lens.define`. [docs/reference/errors.md#load-failures](docs/reference/errors.md#load-failures) |
| ``tern.on: unknown host event "<name>"`` / ``unknown window event `<name>` `` | The event exists in the other context or not at all. [docs/reference/errors.md#registration-errors](docs/reference/errors.md#registration-errors) |
| ``tern.override: unknown command `<id>` `` | Not a built-in command id; only the 167 commands are overridable. Same page. |
| ``tern.css: bad name `<name>` `` | Sheet names take letters, digits, `_`, `-` and cannot be `styles`. Same page. |
| `plugin bind left out: the preset binds these keys` | The defaults or preset own the chord or overlap its sequence; pick another chord or bind it in `keybinds`. [docs/reference/errors.md#registration-errors](docs/reference/errors.md#registration-errors) |
| `plugin spawn filter took over 50 ms; skipped` | The filter answered too late; the pane started with the spec as it was. [docs/reference/errors.md#log-only-messages](docs/reference/errors.md#log-only-messages) |
| `tern: <hook> exceeded <n> ms` | The call ran past its budget and the hook is disabled until the next reload. [docs/reference/errors.md#handler-failures](docs/reference/errors.md#handler-failures) |
| `no daemon running` | `tern plugin reload` needs the daemon; mutating verbs still change the folder. [docs/reference/errors.md#command-line](docs/reference/errors.md#command-line) |

Budgets that kill handlers: 2 s for every host call including the entry, 50 ms for every window call including the entry, 4 ms for chrome formatters and `available` checks. A trip raises once, toasts once, and disables that hook in that VM until reload; later calls are skipped silently, logged at debug on the host and as `tern: <hook> is disabled after exceeding its budget` on the window. The hook is the unit: one slow timer disables the plugin's timer callbacks, one slow `view` stops rendering every block of that type. A reload makes fresh VMs and re-enables everything. [docs/concepts/runtime.md#a-tripped-budget](docs/concepts/runtime.md#a-tripped-budget), [docs/reference/limits.md#vms-and-budgets](docs/reference/limits.md#vms-and-budgets), [docs/guides/debugging.md#budgets-as-a-signal](docs/guides/debugging.md#budgets-as-a-signal)

## Where to look next

| Question | Doc |
| --- | --- |
| Where plugins, settings and data live | [docs/concepts/packages.md#directories](docs/concepts/packages.md#directories) |
| Installing, linking, removing, `--json` output | [docs/reference/cli.md](docs/reference/cli.md) |
| Every action, command id and chord grammar | [docs/reference/actions.md](docs/reference/actions.md) |
| Commands, keys, overrides in depth | [docs/guides/commands.md](docs/guides/commands.md) |
| Tab titles, window title, status segments | [docs/guides/chrome.md](docs/guides/chrome.md) |
| Supported CSS and the variable catalog | [docs/styles/css.md](docs/styles/css.md), [docs/styles/variables.md](docs/styles/variables.md) |
| Window events, layout and workspaces | [docs/guides/layout.md](docs/guides/layout.md), [docs/reference/events.md](docs/reference/events.md) |
| Routing opens and links | [docs/guides/routing.md](docs/guides/routing.md) |
| Host hooks and the spawn filter | [docs/guides/hooks.md](docs/guides/hooks.md) |
| Every manifest key and rule | [docs/reference/manifest.md](docs/reference/manifest.md) |
| Reading settings from a plugin | [docs/reference/api-window.md#settings-cx](docs/reference/api-window.md#settings-cx) |
| Error messages with causes and fixes | [docs/reference/errors.md](docs/reference/errors.md) |
| Budgets and limits | [docs/reference/limits.md](docs/reference/limits.md), [docs/concepts/runtime.md#budgets](docs/concepts/runtime.md#budgets) |
| Reading logs and driving a window from a script | [docs/guides/debugging.md](docs/guides/debugging.md) |
| Blocks, lenses and views (beyond this cookbook) | [docs/guides/blocks.md](docs/guides/blocks.md), [docs/guides/lenses.md](docs/guides/lenses.md), [docs/guides/views.md](docs/guides/views.md) |
