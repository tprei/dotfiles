# Personal dotfiles

WSL/Linux and MacBook config for shell, tmux, nvim, terminals, keyboard, and agents. Each top-level directory is a GNU Stow package.

## Tasks

`justfile` holds repeatable procedures. Run recipes from the repo root; `OMP_SRC` overrides the runtime source path. Install `just` with `cargo binstall just`, `brew install just`, or a [release binary](https://github.com/casey/just/releases).

```sh
just                      # list recipes
just stow-check omp       # dry-run one package (omit the name for all)
just stow omp             # link it
just omp-verify           # prove the omp package is live in $HOME
just omp-config-check     # parse configs, compile extensions, check GLM thinking levels
just omp-rebuild          # bootstrap the pinned source, apply patches, rebuild, relink
just omp-runtime-export   # regenerate omp-runtime/*.patch from the source checkout
just omp-runtime-check    # fail on patch drift against the source checkout and PIN
just raycast-import       # load raycast/settings.json into Raycast (confirm in its dialog)
just raycast-capture FILE # rebuild raycast/settings.json from a Raycast export
just usage                # provider usage report
just ci                   # lean CI gate: tests, ruff, shellcheck, config check, secret scan
```

## Shell and terminals

- `zsh/.zshrc`: Oh My Zsh (`git`, `z`, autosuggestions, `fzf`), nvim as editor, nvm, brew, bun, pnpm, local secrets, Claude wrappers, clipboard helpers.
- `tmux/.tmux.conf`: `C-a` prefix, `tmux-256color`, mouse, clipboard passthrough, vi copy mode, `C-h/j/k/l` pane navigation, Meta bindings for windows, panes, resizing, and WSL helpers. Shifted forwarding accepts both legacy shifted glyphs and Alacritty's explicit CSI-u Shift chords. `tmux/scripts/tmux-paste-image.sh` pastes a WSL clipboard image path.
- `herdr/.config/herdr/config.toml`: herdr on a `ctrl+a` prefix, same as tmux. `alt+n/p`, `alt+j/k`, and `alt+1..9` switch tabs; `alt+c` creates a tab, `alt+x` closes it, and `alt+r` or `prefix+,` renames it. `alt+w` or `alt+g` opens Goto, which lists terminals with their workspace and tab names; Herdr has no tab-only picker. `alt+shift` targets workspaces: `alt+shift+n/p`, `alt+shift+j/k`, and `alt+shift+1..9` switch, `alt+shift+c` creates, `alt+shift+r` renames, `alt+shift+x` closes (asks first), and `alt+shift+w` opens workspace navigation across connected machines. `ctrl+alt+1..9` focuses agents. Other direct keys remain `alt+z` zoom, `alt+f` sidebar, `alt+-`/`alt+=` split, `alt+h/l` resize, `alt+e` scrollback in `$EDITOR`, `alt+o` notification target, and `alt+?` help. `alt+shift+e` opens the pane's directory in Finder, and `alt+shift+.` toggles reviewr. `ctrl+h/j/k/l` move pane focus through `scripts/navigate.py`, which forwards the key to vim, fzf, ssh, mosh, tmux, or nested herdr; nvim hands focus back at a split edge. `ctrl+alt+h/j/k/l` and `prefix h/j/k/l` always move focus. Copy mode is `prefix+[`, `alt+]`, or either shifted bracket. An outer tmux still owns its Alt keys and forwards shifted variants one level inward; that is separate from Herdr's workspace bindings. Saved SSH machines use the local client's keys by default, while custom commands execute on the selected server. Reload the client with `prefix+r`; reload server config with `herdr server reload-config`. See [Herdr's machine settings](https://herdr.dev/docs/connecting-machines/#settings-and-automation).
- `herdr/.config/herdr/scripts/`: `checkpoint.sh` backs `prefix+ctrl+s`. Herdr has no save command and autosaves `session.json`, so the key copies it to `~/.config/herdr/checkpoints/` (last 20 kept, layout only, no processes). `checkpoint-status.sh` feeds the tab bar: a three-second progress animation after a checkpoint, then how long ago `session.json` was saved. `open-pane-dir.sh` backs `alt+shift+e`. The tab bar is hidden in single-tab workspaces (`hide_tab_bar_when_single_tab`), so the status only shows with two or more tabs.
- `herdr/.config/herdr/extrakto/`: `prefix+tab` opens `extract.py` in a popup, a Herdr port of [extrakto](https://github.com/laktak/extrakto) that vendors its `extrakto.py`, `extrakto.conf`, and `LICENSE` from `d1af779` (with `extrakto.py` patched only for lint findings), so `~/.config/extrakto/extrakto.conf` overrides apply. In fzf, `tab` types the selection into the focused pane, `enter` copies it (`pbcopy` on macOS, OSC 52 elsewhere), `ctrl-o` opens it, `ctrl-e` runs `$EDITOR` on it in the pane, `ctrl-f` cycles the word, all, and line filters, `ctrl-g` cycles the grab area between the focused pane and every pane in the tab, and `ctrl-l` shows `HELP.md`. It replaces Herdr's default next-pane cycling (`cycle_pane_next = ""`); `prefix+shift+tab` still cycles backward. Each server needs Python, `fzf`, and the installed `~/.config/herdr/extrakto` directory. After pulling new package directories, run `just stow herdr` on each host; a live config symlink does not install new sibling directories. A missing `extract.py` makes the popup close immediately. Resolve Stow conflicts without overwriting local plugin configuration.
- `nvim/.config/nvim`: `lazy.nvim` with gruvbox, LSP, formatting, linting, Telescope, Treesitter, Blink, `nvim-tree`, render-markdown, lualine, persistence, and `vim-tmux-navigator`, whose `ctrl+h/j/k/l` move between splits and, at the edge, to the neighboring herdr pane whenever `HERDR_ENV=1`, even if the pane inherited a `TMUX` variable, to the neighboring tmux pane in tmux outside herdr, or to the neighboring Tern pane when `TERN_PANE` is set: it reads the tab's layout from `tern ls --json` and runs `tern focus`, against the daemon of the machine nvim runs on, so it works on remote hosts too. Tern CLI processes have a 1-second timeout; nonzero exits, signal termination, and timeouts raise an error in nvim.
- `ghostty/.config/ghostty/config`: Gruvbox Dark, zsh integration, Option-as-Alt, copy on keypress only, top quick terminal, `Ctrl-Shift-V` paste, command palette unbound. `alacritty/.config/alacritty`: Gruvbox Dark and explicit CSI-u sequences for Herdr's Alt and Alt+Shift chords, including shifted digits and brackets on a US layout. These mappings apply outside Herdr too. On Windows, install the same keyboard bindings into `%APPDATA%\alacritty\alacritty.toml`; a regular file there does not follow this checkout.
- `tern/keys.json`: Tern's keys, laid over the `tmux` preset on a `ctrl+a` prefix with herdr's direct keys: `alt+c/x/r` create, close, and rename tabs, `alt+n/p` and `alt+1..9` switch them, `alt+-`/`alt+=` split right and down, `alt+z` zooms, `alt+h/l` resize, `ctrl+alt+h/j/k/l` focus panes, `alt+[` and `ctrl+a>[` open native copy mode (`plugin.copymode.open`), `alt+g`/`alt+w` open Mission Control, `alt+o` the inbox, and `alt+shift+c/r/x/w` create, rename, close, and switch sessions. `cmd+d` sends `ctrl+d` and `cmd+a` sends `ctrl+a`, as in Ghostty. `global_hotkey` `alt+space` (physical ⌘Space under the Mac Karabiner rule, which leaves Raycast's ⌘Space on physical Ctrl+Space) brings the running Tern to the front from any app and hides it when it's already in front; it's macOS and Windows only, so the WSL window ignores it. Tern rewrites `settings.json` whole on every preference change, so it can't be stowed: `just tern-keys` merges this file into it (`~/Library/Application Support/Tern` on macOS, `$TERN_CONFIG_DIR` when set), replacing `keybinds`, then run **Reload settings**. Settings are per machine; run it where the Tern window runs, not on a remote host.
- Tern review keys: `alt+d` opens a Git pane of working tree changes, `alt+shift+d` toggles the inline/split diff setting, `alt+f` toggles the files sidebar, `alt+shift+f` shows the focused pane's cwd in it, `alt+t` opens Processes, `alt+u` toggles a picture-in-picture of the focused pane, and `alt+/` searches scrollback; `ctrl+shift+up/down` jump to the previous/next prompt where the shell integration marks prompts, and `ctrl+shift+h/l` move previous/next file and `ctrl+shift+j/k` next/previous hunk while a Git diff is open. Tern handles these keys on the window machine; logical Alt is physical Cmd under the current Mac Karabiner rule and ordinary Alt on the WSL window.
- Tern parked panes: `alt+shift+j` (or `ctrl+a shift+j`) parks the focused pane in the pile at the window's bottom edge with its program still running, and `alt+shift+k` (or `ctrl+a shift+k`) fans the pile out. The fanned pile opens on the oldest card and takes only Tern's own keys: `left/right` pick a card, `up` or `enter` deals it back beside the focused pane, and `down` or `esc` puts the pile away; it ignores `h/j/k/l`, and no action or plugin API moves its selection. Tern's default `ctrl+shift+down/up` for the same commands stay shadowed by the prompt jumps above.
- `tern/nav`: a Tern window plugin for herdr's navigation keys. `just tern-keys` links the plugins before merging the keys that call them (`just tern-plugin` links them alone); remote hosts need only `tern` on `PATH` for nvim. `ctrl+h/j/k/l` pass the key through when the focused pane runs a vi-family editor (`vi`, `vim`, `nvim`, `view`, `lvim`), fzf, ssh, mosh, tmux, or herdr, and move Tern focus otherwise, including from shells and agents, as under herdr. The only other interception: when the focused block is the extrakto picker, nav routes `ctrl+h/j/k/l` to the picker — `h/l` move its query caret, `j/k` its result selection — instead of pane focus; `ctrl+a ctrl+l` clears the screen. `alt+j/k` and `alt+shift+n/p` cycle sessions, `alt+shift+1..9` jump to one, and `ctrl+alt+1..9` focus the Nth agent in Tern's agent list, switching sessions as needed. Tern only knows the command the shell reported, so nvim started by another program (`git commit`), behind a `VAR=value` prefix, or fzf in a zsh widget (`ctrl+r`) don't count.
- `tern/extrakto`: `ctrl+a tab` opens a compact native themed picker (`extrakto.picker`) in a zoomed split under the focused terminal pane, with matched characters highlighted; the vendored laktak/extrakto core and `extrakto.conf` stay unchanged, so `~/.config/extrakto/extrakto.conf` overrides apply. The picker builds a private SQLite catalog from the last 2000 lines of every terminal and agent pane in the tab, picture-in-picture panes included; the catalog keeps every eligible candidate and the UI renders the best 300. `ctrl-f` cycles the words, paths/URLs/quotes, and lines filters, `ctrl-g` cycles the whole tab, origin pane, and visible screen scopes, `ctrl-j/k`, `ctrl-n/p`, and the arrows move through results, `ctrl-h/l` move the query caret, `shift-tab` marks multiple results, `tab` pastes into the origin pane, `enter` copies through Tern's clipboard, `ctrl-e` opens the selection in `$EDITOR` on the pane's machine, and `escape` cancels. Install is `just tern-plugin` on the window and pane machines, then **Reload plugins**; a pane machine needs `python3` 3.9+ and `tern` on the login shell's `PATH`, and the bundled `extract.py` helper runs directly — no `fzf` and no `tern-extrakto` executable link. File panes aren't read, and the picker won't start from a file pane or a floating picture in picture.
- `tern/copymode`: `ctrl+a [` or `alt+[` enters native copy mode (`copymode.copy` block via `plugin.copymode.open`) in the focused pane's own slot. At entry, the window half splits the origin pane down with host block `copymode.copy`, with no launch argument. The host half finds the origin from `tern ls --json` on the pane's host, asks the window to park it with `copymode://park`, and captures one snapshot of the pane's full retained scrollback with `tern capture --html --scrollback --surfaces` streamed to a private file, so it includes native block surface text (omp transcripts and other TSP blocks) alongside the colored terminal grid. The process keeps running behind the snapshot, shown as a card in Tern's park pile. The cursor starts on the last line. Motions follow herdr and vi: `h/j/k/l` and arrows (one character, with its combining marks, per step), words `w/b/e` and `W/B/E`, line boundaries `0/^/$`, paragraphs `{/}`, page and half-page jumps, `g`/`gg` to the top and `G` to the bottom, and numeric counts. Search with `/` (forward) and `?` (backward) wraps, uses smart case, and steps with `n/N`. Selection supports characterwise (`v`/`space`) and linewise (`V`) with `o` to swap endpoints. `y` or `enter` copies the selection (or the current line when nothing is selected) to the window machine's clipboard and exits, `escape` clears the selection or exits when nothing is selected, and `q` exits immediately; every exit, including `ctrl+a x` on the copy pane, puts the pane back in its exact slot with the split ratios unchanged. If something else closes the copy pane (`tern close`), the pane comes back on the next focus change. Requires Tern 0.8.3, `python3`, and `tern` on the pane host's login `PATH`. Install on the window machine and every remote pane host (including WSL) via `just tern-plugin` (or `tern plugin link`) and **Reload plugins**; the window and host halves must come from the same checkout, so update and reload both machines together. Run `just tern-keys` and **Reload settings** on the window machine for bindings.

## MacBook keyboard

`karabiner/.config/karabiner/karabiner.json` is the active config, stowed as `~/.config/karabiner`. Stow must link the whole `karabiner` directory. Karabiner doesn't reload a symlinked `karabiner.json`, so never link the file alone.

- Control sends Command outside terminals and stays Control inside them; Tern counts as a terminal.
- `Control-Space` sends `Command-Space` in terminals, for Raycast.
- Option sends right Command; Command sends Option.
- Physical Option or physical right Command plus an AeroSpace key sends Ctrl+Option+Command plus that key, so Control+K reaches apps as Command+K instead of AeroSpace.
- Holding Caps Lock sends Hyper (Command+Control+Option+Shift) in every app; tapping it alone sends Escape on release in terminals.

One-time setup: back up the live config to a unique sibling, stow, and restart Karabiner's user server once. After that, edits to the repo file reload automatically and Karabiner Settings write through the link into this repo. No import or remove-and-re-add of Complex Modifications is needed because the `Default profile` ships with the rules enabled. GUI saves also drop timestamped copies in `karabiner/.config/karabiner/automatic_backups/` (git-ignored). Rules imported through the GUI land in the repo's `assets/` directory; review those files before committing.

```sh
mv ~/.config/karabiner ~/.config/karabiner.backup-$(date +%Y%m%d-%H%M%S)
just stow-check karabiner   # must report no conflicts
just stow karabiner
test -L ~/.config/karabiner && test ! -L ~/.config/karabiner/karabiner.json
launchctl kickstart -k gui/$(id -u)/org.pqrs.service.agent.karabiner_console_user_server
```

The link check must succeed before continuing. If Karabiner recreates a real directory before Stow runs, stop Karabiner, move that directory aside, and repeat the setup. The service label above is installed with Karabiner-Elements 16.0.0; `launchctl list | grep karabiner` prints the label for other versions. If an earlier Stow install left `~/assets` pointing to this repo's old `karabiner/assets`, remove that obsolete symlink.

Disable macOS **Input sources** shortcuts on `Control-Space`. Re-record Raycast with physical `Control-Space` (it should show `Command-Space`) and AltTab with physical `Command-Tab` (it should see `Option-Tab`).

## Raycast

`raycast/` isn't a Stow package; like `tern/`, Raycast reads it from this checkout. `raycast/settings.json` versions Raycast's preferences and every command hotkey, including `Hyper+F` (`Shift-Control-Option-Command-3`, key code 3 being F) for **Fork focused omp session**.

One-time setup per Mac: in Raycast **Settings > Extensions > Script Commands**, add the script directory `~/repos/dotfiles/raycast/scripts`. Raycast keeps script directories only in its encrypted database, and its export leaves them out, so this step can't be versioned. Then run `just raycast-import` and click **Import**. The recipe gzips `settings.json` into an unencrypted `.rayconfig` and opens it in Raycast's **Import Settings & Data**. On Raycast 1.104 that import overwrites existing settings and hotkeys rather than merging them, so `settings.json` must list every hotkey you want to keep.

After changing settings or hotkeys in Raycast, run **Export Settings & Data** with only **Settings** checked, then `just raycast-capture <file>.rayconfig` and enter the export passphrase. It decrypts the export, keeps only preferences and hotkeyed commands, and rewrites `settings.json`; delete the export afterward. Run the script tests with `python3 -m unittest discover -s raycast/tests`.

The command uses Tern's native fork operation to open the focused omp session in a new right-hand pane without changing the source session or its unsent draft. It selects only the shown session's shown tab and refuses a non-omp pane or multiple Tern windows rather than guessing. Tern must be installed at `/Applications/Tern.app`; `TERN_DAEMON_SOCKET` overrides its default daemon socket. Physical Option+Shift+F still fullscreens through a separate AeroSpace chord, leaving Hyper+F free.

## AeroSpace

`aerospace/.aerospace.toml` binds only Ctrl+Option+Command chords, which the Karabiner rule sends for physical Option or physical right Command, so Herdr keeps its Alt chords and Control keeps app shortcuts. AeroSpace can't tell left from right Command, so the rule does it. Without a config file, AeroSpace's default Alt bindings shadow Herdr's.

- Option+h/j/k/l focuses, Option+Shift+h/j/k/l moves, Option+-/=/0 shrinks, grows, and balances, Option+Shift+F fullscreens, and Option+Shift+Space toggles floating.
- Option+/ and Option+, switch to tiles and accordion; pressing again toggles horizontal and vertical.
- Option+1–7 switch workspaces and return to the previous one when already there; Option+Tab jumps back, and Option+Shift+1–7 move the window.
- Workspaces 1–4 stay on the main monitor and 5–7 on the other one, or on the main monitor when only one is connected. Option+M focuses the other monitor, and Option+Shift+M moves the window there and follows it.
- Option+Z toggles workspace Z, where new Zoom windows open. Finder, System Settings, and Calculator open floating.
- Option+Shift+; enters service mode: `Esc` reloads the config and `r` flattens the workspace tree.
- AeroSpace starts at login with 6-pixel inner and 3-pixel outer gaps. Turn on **Group windows by application** under **Desktop & Dock** > **Mission Control** so Mission Control doesn't shrink windows parked on hidden workspaces.

## Agents

`shared/` is the source of truth: `skills/` (canonical workflow library; tool skill dirs symlink into it), `agents/` (per-tool agent definitions), `context/agent-guidance.md` (shared instructions, symlinked as `AGENTS.md`, `CLAUDE.md`, and omp/pi `APPEND_SYSTEM.md`), and `prompts/` (legacy compatibility only).

`claude`, `codex`, `omp`, and `pi` are separate stow packages. A real file at a target path means the package isn't stowed and the tool runs on its defaults.

### OMP setup

If `omp` isn't stowed, OMP writes defaults to `~/.omp/agent/config.yml` and ignores this repo; the symptom is the default model falling back to OMP's built-in instead of `modelRoles.default`.

```sh
just stow-check omp   # must report no conflicts
just stow omp
```

`stow` won't link over real files. On `existing target is neither a link nor a directory`, back those files up, move them aside, and re-run. Expected on fresh machines, since OMP creates `config.yml` on first launch.

Layout:
- `omp/.omp/agent/config.yml`: root profile (model roles, thinking level, subagent overrides, retry fallback chains).
- `omp/.omp/agent/{rules,extensions}/`: global rules and TypeScript extensions.
- `omp/.omp/agent/extensions/model-balancer.ts`: rotates subagent spawns across pools (one model served by several providers). It assumes `task.perCallModel: off`, the default.
- `omp/.omp/agent/models.yml`: model definitions merged over the bundled catalog; each profile symlinks it. Caps GPT-6.2 Astra (OpenAI Codex, OpenRouter) thinking at `low`, `medium`, and `high` with a `medium` default.
- `omp/.omp/profiles/{mix,claude,codex,china}/agent/`: per-profile `config.yml`, `agents/`, and optional `rules/`, `APPEND_SYSTEM.md`, `WATCHDOG.md`. `codex` pins every role, agent override, and fallback chain to OpenAI Codex GPT-6.2 only.
- `omp/.gemini/config/agents/omp-provider/agent.md`: isolated AGY transport agent.

`just omp-verify` fails when `~/.omp/agent/config.yml` resolves outside the repo. `just omp-config-check` fails when a `zai/glm-5.3` or `zai/glm-5.3-flash` selector uses a level other than `max`, when a tracked file under `omp/` or `shared/` still pins `zai/glm-5.4`, or when a `shared/agents/*/*.md` pinned to a ZAI GLM model declares anything but `thinking: max`. Level-less keys under `retry.fallbackChains` name a failing route and stay level-less. Routing: `zai/glm-5.3:max` drives root, `anthropic/claude-opus-5-5` is the go-to for frontier work, `openai-codex/gpt-6.2-sol:xhigh` plans and reviews, `anthropic/claude-haiku-5-5:max` runs trivial implementation and tasking (`task`, `ui-implementer`, `triage`), and `openai-codex/gpt-6.2-astra` is reserved for tough work (`investigator`, last-resort fallbacks). `retry.fallbackChains` is keyed by model, and a model key outranks any per-spawn chain, so each model's entry is the whole fallback order: Opus falls back AGY Opus, then Gemini 4 Neon, then Sol, then Astra, and no Opus, Sol, or Astra route reaches GLM. `mainAgent.disabledProviders` keeps AGY out of the main driver, so a main session on Opus falls back Sol, then Astra. A subagent spawn on a pooled model alternates providers, and a model auto-retry just abandoned cools its quota bucket (provider plus model family) for 10 minutes. OpenCode Go routes stay inactive until `omp login opencode-go`; drop them when that plan lapses.

Edit configs here, never in `~/.omp`. A real file under `~/.omp` is drift: reconcile it into the repo and re-stow. `agent.db`, `history.db`, `models.db`, `sessions/`, `logs/`, and `cache/` are untracked runtime state.

A model id missing from the catalog, provider extensions, and `models.yml` resolves to nothing, and the `advisor` role only says `no model is assigned`. Check selectors with `omp models <provider>`.

### AGY CLI provider

`omp/.omp/agent/extensions/antigravity-cli.ts` registers `antigravity-cli`, an `agy` stream-json bridge. AGY isn't ACP; OMP stays the agent process and AGY supplies Gemini turns with its own auth. Run `agy` once to authenticate; there's no `omp login` step. Set `AGY_BIN` when `agy` isn't on `PATH`.

```sh
omp models antigravity-cli
```

The bridge defines `gemini-4-hydrogen`, `gemini-4-neon`, `claude-opus-5-5`, and `claude-sonnet-5-5`; role config uses the effort suffix (`antigravity-cli/gemini-4-hydrogen:high`). Root and `mix` use it for the advisor and commit roles, for the latency-tolerant `surveyor` and `git-commit-specialist` agents, and behind Anthropic and OpenAI Codex in `retry.fallbackChains`. `model-balancer.ts` rotates subagent spawns between `anthropic/claude-opus-5-5` and `antigravity-cli/claude-opus-5-5`, and likewise for Sonnet. Interactive and planner roles keep their primary providers. `china` only moved to GLM-5.3.

Upstream omp v19.2.1 ships its own `antigravity-cli` provider (ACP transport with host tools and image input, `/login antigravity-cli`). The bridge's rows shadow upstream's rows with the same id; upstream-only rows (`gemini-4-carbon`, `gemini-4-argon`, `gemini-3.8-flash`, `gpt-oss-120b-medium`) need that login. Without it, `omp --model antigravity-cli/<id>` fails with `Antigravity CLI credential data is not valid JSON` and walks `retry.fallbackChains`. `--model` never reaches the bridge rows; roles resolved at runtime (advisor, subagents) do.

Bridge behavior:
- The `omp-provider` agent strips AGY's default prompt components and MCP tools. AGY never gets native-tool permissions: the bridge renders OMP's tool catalog in OMP's XML dialect, parses Gemini's XML calls into OMP `toolCall` blocks, and OMP executes and approves.
- An AGY conversation is reused only while the full OMP transcript prefix matches. Each tool batch costs one local AGY round trip. Image input is rejected.
- OMP-specific headers are renamed only in OMP-authored system text, never in user messages, tool results, or quoted source.

Profiles inherit the extension through `~/.omp/profiles/*/agent/extensions`:

```sh
readlink -f ~/.omp/agent/extensions/antigravity-cli.ts
readlink -f ~/.omp/profiles/mix/agent/extensions/antigravity-cli.ts
```

### Patched OMP runtime

`omp-runtime/` holds the patches this machine's `omp` is built from; the checkout lives outside the repo with no fork. The pinned source is upstream v19.2.1, bootstrapped into `~/.worktrees/oh-my-pi-main-driver-no-agy-v19.2.1` (`OMP_SRC` overrides the path). Building it needs Bun >= 1.4.4 (upstream CI pins 1.4.5); older Bun fails the frozen lockfile install. Running sessions keep the executable they started with; restart them to load the new runtime.

- `PIN`: upstream release, baseline commit, tarball URL, ordered patch list.
- `NNNN-*.patch`: `git format-patch` output above the baseline.
- `0001` scopes provider bans to the main driver and stays required: upstream's only knob, the global `disabledProviders` setting, also restricts subagents. Root, `mix`, and `china` bar `antigravity-cli` for the main driver through the patch's `mainAgent.disabledProviders` key while advisor and commit side agents and the surveyor and git-commit-specialist subagents keep using it.

Upstream ships a native `/effort` command that owns the slash picker and explicit levels, so the thinking-picker extension no longer registers its own; Alt+J still opens its direct effort picker. `/m` keeps fuzzy ranking and latest-version preference, and `/use` keeps session-only role lineups, unlike the persistent native `/modelpreset`.

`just omp-rebuild` works on any machine: it bootstraps the pinned tarball into `~/.worktrees/oh-my-pi-main-driver-no-agy-v19.2.1` (or `OMP_SRC`), applies patches, installs dependencies, drops the pinned release's prebuilt natives from npm into `packages/natives/native/` (x64 platforms ship `-baseline` and `-modern` CPU variants, arm64 the plain name; the loader picks the fastest one the CPU supports), and relinks every launcher holding an `omp`. After committing in the checkout, run `just omp-runtime-export` then `just omp-rebuild`. `just omp-runtime-check` fails when a patch differs from its source commit (ignoring the sha line), is missing from `PIN`, or `PIN` names a missing file. Run it after upstream bumps.

## Private workspaces

`private/<name>/` holds Git-ignored private workspaces, each a local directory or symlink that may carry its own private version control; `just private <name>` execs the workspace's `bin/launch`. The local source stays readable to agents, but this repo's Git never tracks anything under `private/`. The ignore isn't encryption or provider privacy.

## Tools

`tools/.local/bin/claude-usage-check` reports Claude Code OAuth usage (5-hour and 7-day windows) and can post to Telegram. It refreshes tokens through `~/.claude/.credentials.json`; a dead refresh token sends a Telegram warning to run `claude auth login`. `tools/.config/systemd/user/claude-usage-report.{service,timer}` runs it with `--telegram` every 5 minutes (first run 1 minute after boot), editing one pinned message in place; the `message_id` lives in `~/.config/claude-usage/state.json` (0600, untracked) and a deleted message is re-sent and re-pinned. Needs `loginctl enable-linger $USER`.

One-time Telegram setup (token and chat id stay out of the repo; writes `~/.config/claude-usage/config`, 0600):

```sh
TELEGRAM_BOT_TOKEN=<token from @BotFather> claude-usage-check --setup-telegram
```

`tools/.local/bin/codex-usage-check` wraps `omp usage --json --redact` for every provider authenticated in the default OMP profile (OpenAI Codex, Anthropic, OpenCode Go, ZAI). OMP pauses its Google Antigravity sign-in (Google suspended accounts that used third-party sign-in), so Gemini quotas aren't fetched and Antigravity appears only in the token section. It needs OMP auth, not a standalone `codex`. It keeps two pinned photos in the chat, **Usage** and **Predictions**, and runs on the always-on Oracle box `openclaw` via `tools/.config/systemd/user/codex-usage-report.{service,timer}`: the timer starts a run 1 minute after boot and again 1 minute after the previous run finishes, with 1s accuracy and no random delay, and the oneshot service uses `%h` paths so it works under any user, with a 300s startup timeout while the timer owns retries (the script flocks against manual overlap). Each run quietly edits both pinned messages in place, re-sending and re-pinning one when it's deleted, reading the Telegram bot token and chat from `~/.config/claude-usage/config` and keeping `message_id`, `pinned_message_id`, `forecast_message_id`, and `forecast_pinned_message_id` in `~/.config/codex-usage/state.json` (0600, untracked):

- Usage: one card per provider and account with its logo, a bar per window, used percent, reset countdown, and a pace pill, plus the 30-day token card. An alert strip on top shows the worst risk and the next reset. Flames mark heavy use (75% or more used, hot or running-out pace, top token providers); rainbow borders mark untapped quota that will reset unused.
- Predictions: each window's 48-hour usage sparkline, now to projected percent at reset, burn rate, verdict (`EXHAUSTED`, `RUN OUT`, `HOT`, `ON PACE`, `SPARE`, `GATED`, or `NO DATA`), and advice. `tools/.local/share/codex-usage/usage_history.py` reads `usage_history` from every OMP `agent.db` on both machines, measures burn over 24 hours (3 hours for windows of 6 hours or less), and projects usage to reset. Short windows (6 hours or less) are bound to the co-moving long window (24 hours or more) with the least slack; a pooled gain ratio (excluding intervals longer than the short window or containing a dip) prices a full short burn in long-window percent, shown on `SPARE` and `ON PACE` (`~8% of 7d`), and the verdict is `GATED` when that burn exceeds the long window's remaining room. A window that reset inside the lookback counts only post-drop samples; under an hour of history reports `NO DATA`.
- Tokens: 30 days per provider across all OMP session records. openclaw reads its own `~/.omp` and every bundle in `~/.local/state/codex-usage/relay/`. WSL runs `codex-usage-relay.{service,timer}` every 5 minutes: `codex-usage-check --relay openclaw` collects WSL's sessions and history plus mini-1's over strict batch-mode SSH, then pushes one gzipped JSON bundle (`WSL.json.gz`) to openclaw, which checks it parses before replacing the previous one, because openclaw can't reach either machine. Relayed collections are re-windowed to the reporter's window. The reporter unit names the sources it expects (`OMP_USAGE_RELAY_SOURCES=WSL`), so a missing bundle reads `WSL relay missing` and a bundle older than 15 minutes still counts but reads `WSL relay 20m old`; both mark the data partial. Known models are priced even without provider cost. Unreachable machines show as partial, not zero. Shared accounts mean it isn't a billing report.

The headers show quota data age and a `Partial pace history` flag when history comes from fewer machines; tokens show as partial when an SSH source is unreachable, so gaps never read as fresh. Captions hold a short checked-at UTC stamp. Steady runs stay quiet: the same pinned photos are edited and nothing new appears.

When a weekly or monthly window closes at 5% or more used, the run sends one new, notifying reset photo for that run's qualifying resets (fresh capacity, closing usage, next reset) with a text caption, and only advances the watch after delivery; 5-hour windows never alert. Tracking lives under `reset_watch` in the state file.

The first refresh after upgrading migrates in place: the old quota photo becomes the Usage photo, the old forecast photo becomes the Predictions photo, and the saved tokens pin is deleted. Telegram can't delete media older than 48 hours, so that one retires as unpin only and its photo may stay in the chat; all other state, credentials, and file locations are unchanged.

Rendering pipes the SVG through FFmpeg's `svg_pipe` input, which needs FFmpeg built with librsvg (the current setup has it). The renderer runs FFmpeg with `FONTCONFIG_FILE` pointing at `tools/.local/share/codex-usage/fonts.conf`, so the bundled OFL fonts in `fonts/` resolve without a system install. Provider logos live in `logos/`.

On openclaw (`host-admin`, dotfiles in `~/dotfiles/dotfiles`):

```sh
systemctl --user daemon-reload
systemctl --user enable --now codex-usage-report.timer
```

On WSL, the reporter timer stays disabled and only the relay runs:

```sh
systemctl --user daemon-reload
systemctl --user disable --now codex-usage-report.timer
systemctl --user enable --now codex-usage-relay.timer
```

Each run also writes iPhone widget files to `~/.local/state/codex-usage/widget/`: `small.png`, `medium.png`, and `large.png` for the home screen (same look as the photos, clock times in `OMP_USAGE_TZ`), plus `widget.json` with the lock screen summary, written last so it never points at a missing image. A widget failure exits 2 without skipping Telegram, and a Telegram failure doesn't skip the widget. openclaw serves them to the tailnet only, next to the app already on `/`:

```sh
sudo tailscale serve --bg --set-path /usage ~/.local/state/codex-usage/widget
sudo tailscale serve --bg --set-path /omp-usage.js ~/dotfiles/dotfiles/scriptable/omp-usage.js
```

`scriptable/omp-usage.js` is the thin client for the free Scriptable app: open `https://openclaw.tail2fec5e.ts.net/omp-usage.js` in Safari on the phone, copy it into a new Scriptable script, then add a Scriptable widget (home screen small, medium, or large; lock screen circular, rectangular, or inline) and pick the script. Home sizes show the PNGs; lock screen sizes draw natively from `widget.json` with live countdowns. It asks iOS for a refresh every 15 minutes, caches the last good data for offline use, and opens the Telegram bot on tap. Layout changes ship from openclaw without touching the phone; only changes to the script itself need a re-paste.

### Sprite offload

`tools/.local/bin/off` runs the tasks a repo declares in `offload.toml` on [Fly.io Sprites](https://fly.io/sprites) instead of this machine. Each machine gets its own workers per repo (`off-<host><hash>-<repo><hash>-<n>`; the hashes keep look-alike hostnames and same-named repos from different owners apart). A worker is built once from `[setup]`, locked down, and checkpointed. Setup sees only the `inputs` files, so nothing else from the tree ends up in the checkpoint. Every run restores that checkpoint, syncs the files `git ls-files -co --exclude-standard` lists (uncommitted edits and new files included, anything git ignores left out), runs the task, and lets the Sprite sleep. A change to `[setup]`, its `inputs`, or the worker policy rebuilds the worker.

One-time setup per machine: `just stow tools`, then `just sprites-setup org=<fly-org>`. It installs the `sprite` CLI, signs in, and pins the org in `~/.config/off/org`.

```toml
version = 1

[worker]
memory_mb = 6144
max = 2                                  # parallel workers for this repo on this machine
egress = ["fonts.googleapis.com"]        # everything else is blocked during runs

[setup]
inputs = ["package.json", "package-lock.json"]  # the only files setup sees; a change rebuilds the workers
run = ["npm ci --ignore-scripts"]

[tasks.test]
run = "npx vitest run --shard=$OFF_SHARD/$OFF_SHARDS"
timeout = "20m"
shards = 2
```

- Commands: `off plan` (local only), `off run TASK [-- ARGS]`, `off status`, `off down [--all]`, `off watch RUN_ID [--shard N]`, `off usage [--days N]`.
- Exit codes: the task's own code, `124` on timeout, `125` when off itself fails (including a dropped `sprite exec` connection), `130` when interrupted. Interrupting or losing a run restores the worker's checkpoint, which stops the remote task. Logs and artifacts live under `~/.local/state/off/`.
- Lockdown: during runs egress is denied except `worker.egress`, sudo is blocked, memory is capped, and the Sprite URL stays private. Env from `[env] pass` and task `env` goes in per run through a file deleted before the task starts. No credentials live on a worker.
- Tern: each shard opens a tab in a Tern session named `off` that follows the local log; it closes on success and stays open on failure. `OFF_TERN=off` disables it.
- Docker tasks aren't supported: the Docker daemon needs root, which the lockdown removes.
