---
name: nvim-configuration
description: Quick reference for browsing and understanding nvim configuration, keybindings, and plugins
type: skill
---

# nvim configuration

Answer questions about the user's Neovim keybindings, plugins, settings, and troubleshooting. Read the live config; don't answer from memory.

Config: `nvim/.config/nvim/` in the dotfiles repo, stowed to `~/.config/nvim/`. `lazy.nvim`, leader is Space, colorscheme gruvbox.
- `init.lua`: entry point and core options
- `lua/config/{lazy,keymaps}.lua`: plugin manager setup and global keymaps
- `lua/plugins/*.lua`: one spec per plugin (blink, conform, lint, lsp, telescope, treesitter, nvim-tree, which-key, vim-tmux-navigator, and more)
- `lua/ai_ask/`: local AI ask module

Find mappings with `rg -n "keymap.set|keys = " nvim/.config/nvim`. Add a plugin as a new `lua/plugins/<name>.lua`.

Commands: `:Lazy` (plugin status), `:checkhealth`, `:e $MYVIMRC`, `:so $MYVIMRC`.
