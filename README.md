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
just usage                # provider usage report
```

## Shell and terminals

- `zsh/.zshrc`: Oh My Zsh (`git`, `z`, autosuggestions, `fzf`), nvim as editor, nvm, brew, bun, pnpm, local secrets, Claude wrappers, clipboard helpers.
- `tmux/.tmux.conf`: `C-a` prefix, `tmux-256color`, mouse, clipboard passthrough, extended keys, vi copy mode, `C-h/j/k/l` pane navigation, Meta bindings for windows, panes, resizing, and WSL helpers. `tmux/scripts/tmux-paste-image.sh` pastes a WSL clipboard image path.
- `herdr/.config/herdr/config.toml`: herdr inside tmux panes on a `ctrl+b` prefix that mirrors tmux. `alt+n/p/w/x`, `alt+1..9` tabs, and `alt+h/j/k/l` resize match tmux root bindings. Copy mode is `alt+]`, `alt+}`, or `alt+{`; tmux forwards Alt+Shift+] and Alt+Shift+[ as `M-}`/`M-{` because herdr drops a forwarded `ESC ]` as an OSC start. Pane focus is `ctrl+alt+h/j/k/l` so plain `ctrl+h/j/k/l` reach the shell, nvim, and ssh inside herdr. `prefix -`/`prefix =` split like tmux `-h`/`-v` (herdr's vertical and horizontal names are reversed). `scripts/open-pane-dir.sh` backs `alt+e`. `@in_nested` and `@vim_navigator_check` include `herdr`, so Alt+Shift and navigator keys pass one level in.
- `nvim/.config/nvim`: `lazy.nvim` with gruvbox, LSP, formatting, linting, Telescope, Treesitter, Blink, `nvim-tree`, render-markdown, lualine, persistence, and tmux navigation.
- `ghostty/.config/ghostty/config`: Gruvbox Light, zsh integration, Option-as-Alt, copy-on-select, top quick terminal, `Ctrl-Shift-V` paste. `alacritty/.config/alacritty`: config plus gruvbox dark.

## MacBook keyboard

`karabiner/assets/complex_modifications/macbook-left-modifiers.json`:

- Control sends Command outside terminals and stays Control inside them.
- `Control-Space` sends `Command-Space` in terminals, for Raycast.
- Option sends Command; Command sends Option.

Disable macOS **Input sources** shortcuts on `Control-Space`. Re-record Raycast with physical `Control-Space` (it should show `Command-Space`) and AltTab with physical `Command-Tab` (it should see `Option-Tab`).

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
- `omp/.omp/agent/models.yml`: model definitions merged over the bundled catalog; each profile symlinks it. Narrows GPT-6 Astra (OpenAI Codex, OpenRouter) to `low` and `medium`.
- `omp/.omp/profiles/{mix,claude,china}/agent/`: per-profile `config.yml`, `agents/`, and optional `rules/`, `APPEND_SYSTEM.md`, `WATCHDOG.md`.
- `omp/.gemini/config/agents/omp-provider/agent.md`: isolated AGY transport agent.

`just omp-verify` fails when `~/.omp/agent/config.yml` resolves outside the repo. `just omp-config-check` fails when a `zai/glm-5.3` or `zai/glm-5.3-flash` selector uses a level other than `max`, or a `shared/agents/*/*.md` pinned to `model: zai/glm-5.3` declares anything but `thinking: max`. Level-less keys under `retry.fallbackChains` name a failing route and stay level-less.

Edit configs here, never in `~/.omp`. A real file under `~/.omp` is drift: reconcile it into the repo and re-stow. `agent.db`, `history.db`, `models.db`, `sessions/`, `logs/`, and `cache/` are untracked runtime state.

A model id missing from the catalog, provider extensions, and `models.yml` resolves to nothing, and the `advisor` role only says `no model is assigned`. Check selectors with `omp models <provider>`.

### AGY CLI provider

`omp/.omp/agent/extensions/antigravity-cli.ts` registers `antigravity-cli`, an `agy` stream-json bridge. AGY isn't ACP; OMP stays the agent process and AGY supplies Gemini turns with its own auth. Run `agy` once to authenticate; there's no `omp login` step. Set `AGY_BIN` when `agy` isn't on `PATH`.

```sh
omp --model antigravity-cli/gemini-3.8-flash --thinking high -p "Reply with one word: pong"
```

Role config uses the effort suffix (`antigravity-cli/gemini-3.8-flash:high`). Root and `mix` profiles use it for advisor and commit roles and the latency-tolerant `surveyor` and `git-commit-specialist` agents, and as a fallback for GPT-6 Luna, GLM-5.3 Flash, and OpenCode Go. Interactive, planner, task, explorer, and latency-sensitive roles keep their primary providers. `china` is unchanged.

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

`omp-runtime/` holds the patches this machine's `omp` is built from; the checkout lives outside the repo with no fork.

- `PIN`: upstream release, baseline commit, tarball URL, ordered patch list.
- `NNNN-*.patch`: `git format-patch` output above the baseline.
- `0001` stops main sessions from selecting disabled providers. `0002` retries a dropped socket mid-answer when the turn's only committed output is text (upstream treats that as replay-unsafe). `0003` stops the legacy pi shim from resolving canonical `@oh-my-pi/*` specifiers, which recursed until Bun aborted with `NameTooLong` and broke `/login`.

`just omp-rebuild` works on any machine: it bootstraps the pinned tarball into `~/.worktrees/oh-my-pi-main-driver-no-agy` (or `OMP_SRC`), applies patches, builds, and relinks every launcher holding an `omp`. After committing in the checkout, run `just omp-runtime-export` then `just omp-rebuild`. `just omp-runtime-check` fails when a patch differs from its source commit (ignoring the sha line), is missing from `PIN`, or `PIN` names a missing file. Run it after upstream bumps.

## Tools

`tools/.local/bin/claude-usage-check` reports Claude Code OAuth usage (5-hour and 7-day windows) and can post to Telegram. It refreshes tokens through `~/.claude/.credentials.json`; a dead refresh token sends a Telegram warning to run `claude auth login`. `tools/.config/systemd/user/claude-usage-report.{service,timer}` runs it with `--telegram` every 5 minutes (first run 1 minute after boot), editing one pinned message in place; the `message_id` lives in `~/.config/claude-usage/state.json` (0600, untracked) and a deleted message is re-sent and re-pinned. Needs `loginctl enable-linger $USER`.

One-time Telegram setup (token and chat id stay out of the repo; writes `~/.config/claude-usage/config`, 0600):

```sh
TELEGRAM_BOT_TOKEN=<token from @BotFather> claude-usage-check --setup-telegram
```

`tools/.local/bin/codex-usage-check` wraps `omp usage --json --redact` for every authenticated OMP provider (OpenAI Codex, Anthropic, Google Antigravity, OpenCode Go, ZAI). It needs OMP auth, not a standalone `codex`. It posts three pinned PNGs every five minutes via `tools/.config/systemd/user/codex-usage-report.{service,timer}`, reusing the Claude Telegram config and keeping message ids in `~/.config/codex-usage/state.json`:

- Limits: rows show provider window and unit, sorted by next reset with estimates like `~in 5 minutes`, provider logos, and colors (green healthy, gold resets within an hour with quota left, amber warning, red exhausted). The header shows data age.
- Tokens: 30 days per provider across all OMP session records, read locally and over strict batch-mode SSH. Known models are priced even without provider cost. Unreachable machines show as partial, not zero. Shared accounts mean it isn't a billing report.
- Forecast: `tools/.local/share/codex-usage/usage_history.py` reads `usage_history` from every OMP `agent.db` on both machines, measures burn over 24 hours (3 hours for windows of 6 hours or less), and projects usage to reset. Each row has a 48-hour sparkline and a verdict: `EXHAUSTED`, `RUN OUT`, `HOT`, `ON PACE`, `SPARE`, `GATED`, or `NO DATA`. Short windows (6 hours or less) are bound to the co-moving long window (24 hours or more) with the least slack; a pooled gain ratio (excluding intervals longer than the short window or containing a dip) prices a full short burn in long-window percent, shown on `SPARE` and `ON PACE` (`~8% of 7d`), and the verdict is `GATED` when that burn exceeds the long window's remaining room. A window that reset inside the lookback counts only post-drop samples; under an hour of history reports `NO DATA`.

When a weekly or monthly window closes at 5% or more used, the run also sends a one-off reset photo (logo, fresh capacity, final usage). 5-hour windows never do. Tracking lives under `reset_watch` in the state file.

```sh
systemctl --user daemon-reload
systemctl --user enable --now codex-usage-report.timer
```
