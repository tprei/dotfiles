# Personal dotfiles

Personal WSL/Linux and MacBook config for shell, tmux, nvim, terminals, keyboard, and agents.

## Tasks

`justfile` holds the repeatable procedures. `just` lists them:

```sh
just                      # every recipe with its one-line description
just stow-check omp       # dry-run one package (omit the name for all of them)
just stow omp             # link it
just omp-verify           # prove the omp package is live in $HOME
just omp-config-check     # parse configs, compile extensions, check GLM thinking levels
just omp-rebuild          # bootstrap the pinned source, apply patches, rebuild, relink
just omp-runtime-export   # regenerate omp-runtime/*.patch from the source checkout
just omp-runtime-check    # fail on patch drift against the source checkout and PIN
just usage                # provider usage report
```

Install it with `cargo binstall just`, `brew install just`, or the prebuilt binary from the [releases page](https://github.com/casey/just/releases). Recipes assume this repository is the working directory; `OMP_SRC` overrides the runtime source path.

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
just stow-check omp   # must report no conflicts
just stow omp
```

`stow` refuses to link over real files. If the dry run reports `existing target is neither a link nor a directory`, move those files aside (back them up, don't delete) and re-run. OMP recreates `config.yml` as a plain file on first launch, so this conflict is expected on a fresh machine.

Layout:

- `omp/.omp/agent/config.yml` — root profile: model roles, thinking level, subagent model overrides, retry fallback chains.
- `omp/.omp/agent/rules/`, `omp/.omp/agent/extensions/` — global rules and TypeScript extensions.
- `omp/.omp/agent/models.yml` — custom model definitions merged over the bundled catalog. Each profile symlinks it.
- `omp/.omp/profiles/{mix,claude,china}/agent/` — per-profile overrides, each with its own `config.yml`, `agents/`, and optional `rules/`, `APPEND_SYSTEM.md`, `WATCHDOG.md`.
- `omp/.gemini/config/agents/omp-provider/agent.md` — isolated AGY transport agent installed by the same Stow package.

Verification:

```sh
just omp-verify         # dry-run stow, resolve config.yml, list every managed link
just omp-config-check   # yaml parse, extension build, GLM thinking-level drift
```

`omp-verify` fails when `~/.omp/agent/config.yml` resolves outside this repository, which is the signal that OMP wrote its own defaults. `omp-config-check` fails when any `zai/glm-5.3` or `zai/glm-5.3-flash` selector carries a level other than `max`, and when a `shared/agents/*/*.md` definition pinned to `model: zai/glm-5.3` declares anything but `thinking: max`. Level-less keys under `retry.fallbackChains` name a failing route and stay level-less on purpose.

Edit configs in this repository, never in `~/.omp`. Anything under `~/.omp` that is a real file is drift; reconcile it into the repo and re-stow. The rest of `~/.omp` (`agent.db`, `history.db`, `models.db`, `sessions/`, `logs/`, `cache/`) is runtime state and stays untracked.

`models.yml` narrows the tracked GPT-6 Astra overrides for OpenAI Codex and OpenRouter to the supported `low` and `medium` effort levels. The rest of the bundled catalog remains unchanged.

A model id absent from the bundled catalog, provider extension, and this file resolves to nothing. The `advisor` role reports `no model is assigned` without naming the bad id, so check selectors with `omp models <provider>`.

### AGY CLI provider

`omp/.omp/agent/extensions/antigravity-cli.ts` registers the `antigravity-cli` provider as an `agy` stream-json bridge. AGY is not an ACP implementation. OMP remains the agent process exposed to ACP clients, while AGY supplies Gemini model turns with its own authentication and model access.

Run `agy` once and complete its authentication flow before the first OMP request. There is no separate `omp login` step for this provider.

The root and `mix` profiles use Gemini 3.8 Flash for the advisor and commit roles, plus the latency-tolerant `surveyor`, `adversary`, and `git-commit-specialist` background agents. Gemini 3.8 Flash high is also a fallback for GPT-5.6 Luna, GLM-5.3 Flash, and OpenCode Go. Interactive driver, planner, generic task, explorer, and latency-sensitive roles keep their primary providers. The `china` profile stays unchanged.

After stowing the package, select a model by its provider selector:

```sh
omp --model antigravity-cli/gemini-3.8-flash --thinking high -p "Reply with one word: pong"
```

Role config uses the effort suffix, for example `antigravity-cli/gemini-3.8-flash:high`. Use `AGY_BIN=/path/to/agy` when `agy` is not on `PATH`.

The tracked `omp-provider` AGY agent removes AGY's default prompt components and inherited MCP tools. The bridge never grants AGY native-tool permissions. Instead, it renders OMP's tool catalog with OMP's XML dialect, parses Gemini's XML calls into normal OMP `toolCall` blocks, and leaves execution and approval to OMP.

The bridge reuses an AGY conversation only while the complete OMP transcript prefix still matches. Each tool batch adds another local AGY process round trip. The provider rejects image input because it has no image transport.

Before sending the prompt, the bridge renames OMP-specific headers only in OMP-authored system text. User messages, tool results, and quoted source remain unchanged.

Profile clients inherit the shared extension through `~/.omp/profiles/*/agent/extensions`. Verify the deployed link before using a profile:

```sh
readlink -f ~/.omp/agent/extensions/antigravity-cli.ts
readlink -f ~/.omp/profiles/mix/agent/extensions/antigravity-cli.ts
```

### Patched OMP runtime

`omp/` tracks configuration. `omp-runtime/` tracks the source patches this machine's `omp` binary is built from, because the OMP checkout itself lives outside the repository and has no fork to push to.

- `PIN` — upstream release, baseline commit, tarball URL, and the ordered patch inventory.
- `0001-*.patch`, `0002-*.patch` — `git format-patch` output for every commit above the baseline.
- `just omp-rebuild` is the single entry point on any machine, fresh or not: it bootstraps `~/src/oh-my-pi` from the pinned tarball, applies the patches, builds, and relinks every launcher that already holds an `omp`.

`0001` stops main sessions from selecting disabled providers. `0002` retries a transient transport failure (a dropped socket mid-answer) when the turn's only committed output is text, which upstream treats as replay-unsafe and drops.

After committing in the source checkout, `just omp-runtime-export` refreshes the patch files and `just omp-rebuild` rebuilds the runtime. `just omp-runtime-check` is the drift gate: it fails when a patch file does not match the source commit (everything but the commit sha line, which a fresh bootstrap legitimately changes), when a patch is not listed in `PIN`, and when `PIN` names a file that no longer exists. Running it after an upstream bump catches a stale `PIN` before the next machine rebuild trusts it.

## Tools

`tools/.local/bin/claude-usage-check` reports Claude Code OAuth usage (5-hour and 7-day window utilization) and can send a formatted report to Telegram. It refreshes the OAuth access token through the same `~/.claude/.credentials.json` the `claude` CLI uses, so it stays authenticated as long as the refresh token stays valid; a dead refresh token triggers a Telegram warning to run `claude auth login` instead of failing silently.

`tools/.config/systemd/user/claude-usage-report.{service,timer}` is a systemd user timer that runs the script with `--telegram` every 5 minutes (`OnUnitActiveSec=5min`, first run 1 min after boot). Each run edits a single pinned Telegram message in place instead of sending new ones — the pinned `message_id` is kept in `~/.config/claude-usage/state.json` (0600, untracked), and a missing or deleted message is re-sent and re-pinned automatically. It needs `loginctl enable-linger $USER` to run without an active login session.

Telegram wiring is a one-time step, and the bot token and chat id are deliberately kept out of the repo:

```sh
TELEGRAM_BOT_TOKEN=<token from @BotFather> claude-usage-check --setup-telegram
```

This writes `~/.config/claude-usage/config` (0600, untracked).

`tools/.local/bin/codex-usage-check` reports usage for every provider OMP supports by wrapping `omp usage --json --redact` with no provider filter. It includes OpenAI Codex, Anthropic, Google Antigravity, OpenCode Go, and ZAI when authenticated, and its limit rows include the provider-reported window and usage unit so similar names such as Google or ZAI meters stay distinct. Rows within each provider are ordered by the next reset time, and reset labels use estimates such as `~in 5 minutes`; the limits image header shows when the usage data was last updated. Each known provider is identified by its fetched logo asset instead of a letter badge, healthy rows are green, limits with available quota that reset within one hour are gold, warnings are amber, and exhausted rows are red. The token chart aggregates thirty days of token usage per provider across every OMP session record, prices known models even when the provider reports no cost, and marks an unreachable machine as incomplete partial coverage rather than counted as zero. The collector reads OMP session records locally and over strict batch-mode SSH, so shared provider accounts do not make the chart a complete account billing report. A third pinned PNG forecasts each OpenAI Codex, Anthropic, ZAI, and OpenCode Go limit window: `tools/.local/share/codex-usage/usage_history.py` reads the `usage_history` table of every OMP `agent.db` on both machines, measures the burn rate over the last 24 hours (3 hours for windows of 6 hours or less), and projects the used percentage forward to the window's reset. Each row carries a 48-hour hourly sparkline and a verdict of `EXHAUSTED`, `RUN OUT`, `HOT`, `ON PACE`, `SPARE`, `GATED`, or `NO DATA`, so a window that hits 100% before it resets says tone it down and one with spare quota says crank it up. Because usage against a short window also drains the provider's long window, each window of 6 hours or less is priced against every co-moving long window (24 hours or more) of the same provider and bound to the one with the least slack; the pooled gain ratio (intervals longer than the short window or containing a visible dip are excluded) prices a full short-window burn in long-window percent, `SPARE` and `ON PACE` advice carries that cost (for example `~8% of 7d`), and the verdict becomes `GATED` when the burn exceeds the bound window's remaining room at its reset. A window that reset inside the lookback only counts samples recorded after the drop, and a window with under an hour of history reports `NO DATA` instead of a guess. All three images reuse the existing Telegram credentials at `~/.config/claude-usage/config`, keep separate message IDs in `~/.config/codex-usage/state.json`, and refresh every five minutes through `tools/.config/systemd/user/codex-usage-report.{service,timer}`. A standalone `codex` installation is not required when OMP is authenticated. Users without an OMP provider account must log in through OMP first.

```sh
systemctl --user daemon-reload
systemctl --user enable --now codex-usage-report.timer
```

## Helpers

`tmux/scripts/tmux-paste-image.sh` sends a WSL clipboard image path into tmux.
