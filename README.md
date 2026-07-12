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

Shared agent assets live under `shared/`: `shared/skills` is the canonical workflow library, `shared/prompts` is only a compatibility directory for any remaining prompt/command files, `shared/agents` holds tool-specific agent definitions, and `shared/context/agent-guidance.md` is the shared instruction file. OMP's global configuration is versioned at `omp/.omp/agent/config.yml`; repo-local discovery paths and the stow-managed home paths for Claude, Codex, OMP, and Pi point back into this repository.

## Helpers

`tmux/scripts/tmux-paste-image.sh` sends a WSL clipboard image path into tmux. `run_claude_update.sh` and `claude_pattern_updater.py` support Claude guidance updates.
