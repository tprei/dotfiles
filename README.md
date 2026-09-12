# Personal dotfiles

Personal WSL/Linux and MacBook config for shell, tmux, nvim, terminals, keyboard, and agents.

## Shell

`zsh/.zshrc` uses Oh My Zsh with `git`, `z`, autosuggestions, and `fzf`. It sets nvim as the editor, loads nvm, brew, bun, pnpm, local secrets, Claude wrappers, and clipboard helpers.

## Tmux

`tmux/.tmux.conf` uses zsh, `tmux-256color`, mouse support, clipboard passthrough, extended keys, `C-a` as prefix, vi copy mode, and `C-h/j/k/l` pane navigation. Meta bindings handle windows, panes, resizing, and WSL helpers.

## Herdr

`herdr/.config/herdr/config.toml` runs herdr inside tmux panes and mirrors the tmux keymap on herdr's `ctrl+b` prefix: bare `C-b` enters herdr, `alt+n/p/w/x`, `alt+]`/`alt+}` copy mode, `alt+1..9` tabs, `alt+h/j/k/l` resize, and `ctrl+h/j/k/l` pane nav match the tmux root bindings, and `prefix -`/`prefix =` split side-by-side/stacked like tmux `-h`/`-v` (herdr's vertical/horizontal names are the reverse of tmux's). `herdr/.config/herdr/scripts/open-pane-dir.sh` backs `alt+e`. `@in_nested` and `@vim_navigator_check` include `herdr`, so Alt+Shift forwarding and the navigator keys pass one level into herdr panes.

## Neovim

`nvim/.config/nvim` is a `lazy.nvim` setup with gruvbox, LSP, formatting, linting, Telescope, Treesitter, Blink completion, `nvim-tree`, render-markdown, lualine, persistence, and tmux navigation.

## Terminals

`ghostty/.config/ghostty/config` uses Gruvbox Light, zsh integration, Option-as-Alt, clipboard integration, copy-on-select, top quick terminal, and `Ctrl-Shift-V` paste.

`alacritty/.config/alacritty` stores the Alacritty config and gruvbox dark theme.

## MacBook keyboard

Karabiner rule:

```text
karabiner/assets/complex_modifications/macbook-left-modifiers.json
```

Behavior:

- Physical Control sends Command/Super outside terminals.
- Physical Control stays Control in terminal apps.
- Physical `Control-Space` sends Command-Space in terminal apps for Raycast.
- Physical Option sends Command/Super.
- Physical Command sends Option/Alt.

Disable macOS **Input sources** shortcuts that use `Control-Space`. Re-record Raycast by pressing physical `Control-Space`; Karabiner emits logical `Command-Space`, so Raycast should show `Command-Space`. Re-record AltTab with physical `Command-Tab`; AltTab should see `Option-Tab`.

## Agents

Shared agent assets live under `shared/`: `shared/skills` is the canonical workflow library, `shared/prompts` is only a compatibility directory for any remaining prompt/command files, `shared/agents` holds tool-specific agent definitions, and `shared/context/agent-guidance.md` is the shared instruction file. The tool-specific skill directories are symlinks into that canonical library.

Each agent tool has its own stow package — `claude`, `codex`, `omp`, `pi` — that links its home path back into this repository. Confirm a package is actually linked before trusting it; a real file at the target means the package was never stowed and the tool is running on its own defaults.

### OMP setup

OMP config is stow-managed. The `omp` package must be symlinked into `$HOME`, otherwise OMP writes its own defaults into `~/.omp/agent/config.yml` and silently ignores everything in this repo — the visible symptom is the default model role falling back to OMP's built-in model instead of `modelRoles.default`.

```sh
cd ~/dotfiles
stow -n -v -t ~ omp   # dry run, must report no conflicts
stow -v -t ~ omp
```

`stow` refuses to link over real files. If the dry run reports `existing target is neither a link nor a directory`, move those files aside (back them up, don't delete) and re-run. OMP recreates `config.yml` as a plain file on first launch, so this conflict is expected on a fresh machine.

Layout:

- `omp/.omp/agent/config.yml` — root profile: model roles, thinking level, subagent model overrides, retry fallback chains.
- `omp/.omp/agent/rules/`, `omp/.omp/agent/extensions/` — global rules and TypeScript extensions.
- `omp/.omp/agent/models.yml` — custom model definitions merged over the bundled catalog. Each profile symlinks it.
- `omp/.omp/profiles/{mix,claude,china}/agent/` — per-profile overrides, each with its own `config.yml`, `agents/`, and optional `rules/`, `APPEND_SYSTEM.md`, `WATCHDOG.md`.

Verification, in order:

1. `stow -n -v -t ~ omp` prints nothing but the simulation warning.
2. `readlink -f ~/.omp/agent/config.yml` resolves into `~/dotfiles/omp/`.
3. `find ~/.omp -maxdepth 4 -type l` lists every managed path, including `agent/rules`, `agent/extensions`, and the profile directories.

Edit configs in this repository, never in `~/.omp`. Anything under `~/.omp` that is a real file is drift; reconcile it into the repo and re-stow. The rest of `~/.omp` (`agent.db`, `history.db`, `models.db`, `sessions/`, `logs/`, `cache/`) is runtime state and stays untracked.

`models.yml` exists because the bundled catalog trails Z.ai's releases. OMP already routes the `zai` provider through `https://api.z.ai/api/anthropic`, so the file only declares the missing GLM id `glm-5.3-flash`. A provider that declares `models` must also carry `apiKey`; `auth: oauth` alone makes OMP reject the entire file silently, and `auth: none` sends no credential at all. `apiKey: "!printenv MY_ZAI_AUTH_TOKEN"` runs the command and uses its stdout, falling through to the stored key when the variable is absent, so no secret is pinned in the repo.

A model id absent from both the catalog and this file resolves to nothing, and any role pointing at it fails at startup. The `advisor` role reports `no model is assigned` without naming the bad id, so check the id against `omp models <provider>` first. The file declares only `glm-5.3-flash`, whose efforts are `high` and `max`; `glm-5.3` comes from the bundled catalog with `low`, `high`, and `max`, which makes `zai/glm-5.3:xhigh` invalid on both.

### AGY CLI provider

`omp/.omp/agent/extensions/antigravity-cli.ts` registers the `antigravity-cli` provider. It runs the installed `agy` binary, so AGY keeps its own authentication and model access. OMP does not need a Google OAuth token for this provider.

Run `agy` once and complete its authentication flow before the first OMP request. There is no separate `omp login` step for this provider.

The root profile keeps its native model for default, vision, commit, and smol work, and uses the CLI provider for the text-only tiny role. The `mix` profile keeps its existing tool and image roles, and uses the CLI provider for tiny. The `china` profile stays on its existing providers.

After stowing the package, select a model by its provider selector:

```sh
omp --model antigravity-cli/gemini-3.8-flash --thinking high -p "Reply with one word: pong"
```

Role config uses the effort suffix, for example `antigravity-cli/gemini-3.8-flash:high`. Use `AGY_BIN=/path/to/agy` when `agy` is not on `PATH`.

AGY headless mode denies native command tools unless AGY already has an allow rule. To let AGY approve its own native tools without prompting, opt in for that command:

```sh
AGY_OMP_DANGEROUSLY_SKIP_PERMISSIONS=1 omp --model antigravity-cli/gemini-3.8-flash --thinking high
```

The provider returns text only and does not forward OMP tool calls. AGY native tools are separate from OMP's approval UI and remain subject to AGY's own permission rules. The provider rejects image input because it has no image transport.

Before sending the prompt, the bridge renames OMP-specific headers so the headless CLI transport is not misread as third-party API usage.

Profile clients inherit the shared extension through `~/.omp/profiles/*/agent/extensions`. Verify the deployed link before using a profile:

```sh
readlink -f ~/.omp/agent/extensions/antigravity-cli.ts
readlink -f ~/.omp/profiles/mix/agent/extensions/antigravity-cli.ts
```

## Tools

`tools/.local/bin/claude-usage-check` reports Claude Code OAuth usage (5-hour and 7-day window utilization) and can send a formatted report to Telegram. It refreshes the OAuth access token through the same `~/.claude/.credentials.json` the `claude` CLI uses, so it stays authenticated as long as the refresh token stays valid; a dead refresh token triggers a Telegram warning to run `claude auth login` instead of failing silently.

`tools/.config/systemd/user/claude-usage-report.{service,timer}` is a systemd user timer that runs the script with `--telegram` every 5 minutes (`OnUnitActiveSec=5min`, first run 1 min after boot). Each run edits a single pinned Telegram message in place instead of sending new ones — the pinned `message_id` is kept in `~/.config/claude-usage/state.json` (0600, untracked), and a missing or deleted message is re-sent and re-pinned automatically. It needs `loginctl enable-linger $USER` to run without an active login session.

Telegram wiring is a one-time step, and the bot token and chat id are deliberately kept out of the repo:

```sh
TELEGRAM_BOT_TOKEN=<token from @BotFather> claude-usage-check --setup-telegram
```

This writes `~/.config/claude-usage/config` (0600, untracked).

`tools/.local/bin/codex-usage-check` reports usage for every provider OMP supports by wrapping `omp usage --json --redact` with no provider filter. It includes OpenAI Codex, Anthropic, Google Antigravity, OpenCode Go, and ZAI when authenticated, and its limit rows include the provider-reported window and usage unit so similar names such as Google or ZAI meters stay distinct. Rows within each provider are ordered by the next reset time, and reset labels use estimates such as `~in 5 minutes`; the image header shows when the usage data was last updated. Each known provider has a colored initial badge, healthy rows are green, warnings are amber, and exhausted rows are red. It reuses the existing Telegram credentials at `~/.config/claude-usage/config` for the same bot and chat, so no second BotFather setup is needed, and the Claude bot/chat config stays unchanged. In Telegram mode the report is rendered into a readable PNG image with the system ffmpeg and edited as a Telegram photo in place, so the pinned message stays legible instead of wrapping as text; ffmpeg is required for Telegram mode, and the service pins the binary with `FFMPEG_BIN=/usr/bin/ffmpeg`. It keeps only `~/.config/codex-usage/state.json` (0600, untracked) for its separate pinned message, refreshed every five minutes by `tools/.config/systemd/user/codex-usage-report.{service,timer}`. A standalone `codex` installation is not required when OMP is authenticated. Users without an OMP provider account must log in through OMP first.

```sh
systemctl --user daemon-reload
systemctl --user enable --now codex-usage-report.timer
```

## Helpers

`tmux/scripts/tmux-paste-image.sh` sends a WSL clipboard image path into tmux.
