# Personal dotfiles

Personal WSL/Linux and MacBook config for shell, tmux, nvim, terminals, keyboard, and agents.

## Shell

`zsh/.zshrc` uses Oh My Zsh with `git`, `z`, autosuggestions, and `fzf`. It sets nvim as the editor, loads nvm, brew, bun, pnpm, local secrets, Claude wrappers, and clipboard helpers.

## Tmux

`tmux/.tmux.conf` uses zsh, `tmux-256color`, mouse support, clipboard passthrough, extended keys, `C-a` as prefix, vi copy mode, and `C-h/j/k/l` pane navigation. Meta bindings handle windows, panes, resizing, and WSL helpers.

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
- `omp/.omp/profiles/{mix,claude,china}/agent/` — per-profile overrides, each with its own `config.yml`, `agents/`, and optional `rules/`, `APPEND_SYSTEM.md`, `WATCHDOG.md`.

Verification, in order:

1. `stow -n -v -t ~ omp` prints nothing but the simulation warning.
2. `readlink -f ~/.omp/agent/config.yml` resolves into `~/dotfiles/omp/`.
3. `find ~/.omp -maxdepth 4 -type l` lists every managed path, including `agent/rules`, `agent/extensions`, and the profile directories.

Edit configs in this repository, never in `~/.omp`. Anything under `~/.omp` that is a real file is drift; reconcile it into the repo and re-stow. The rest of `~/.omp` (`agent.db`, `history.db`, `models.db`, `sessions/`, `logs/`, `cache/`) is runtime state and stays untracked.

## Helpers

`tmux/scripts/tmux-paste-image.sh` sends a WSL clipboard image path into tmux.
