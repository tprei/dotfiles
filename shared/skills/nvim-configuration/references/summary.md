# Neovim Configuration Summary

## Overview

Your Neovim config is based on **kickstart.nvim**, a minimal starter configuration. It uses Lua for configuration and lazy.nvim for plugin management.

## Core Plugins

### Installed & Active

1. **telescope.nvim** — Fuzzy finder for files, buffers, LSP, help, and more
   - Extensions: fzf-native, ui-select
   - Primary search prefix: `<leader>s*`

2. **nvim-lspconfig** — Language Server Protocol client
   - Provides goto definition, references, implementations, etc.
   - Keybindings: `gr*` (e.g., `grd` for definition)

3. **nvim-cmp** — Autocompletion engine with sources
   - Sources: LSP, buffer, path, nvim_lua

4. **LuaSnip** — Snippet engine (integrates with nvim-cmp)

5. **gitsigns.nvim** — Git integration
   - Shows git signs in gutter (add, change, delete)
   - Provides git commands and keybindings

6. **which-key.nvim** — Keybinding help
   - Shows available commands when you press a keybinding prefix
   - Delay set to 0 (immediate)

7. **guess-indent.nvim** — Auto-detect indentation style

8. **tokyonight.nvim** — Theme (disabled by default, uncomment to use)

### Optional Plugins (Commented Out)

The following plugins are available but disabled in your config:

- `debug.nvim` — Debugger integration (nvim-dap)
- `indent_line.lua` — Visual indent guides
- `lint.lua` — Linting with conform.nvim
- `autopairs.lua` — Auto-closing brackets/quotes
- `neo-tree.lua` — File explorer

To enable any, uncomment the corresponding line in init.lua near line 1823.

## Configuration Structure

```
~/.config/nvim/
├── init.lua                    # Main configuration
├── lua/
│   ├── custom/
│   │   └── plugins/
│   │       └── init.lua       # Your custom plugins
│   └── kickstart/
│       ├── plugins/           # Optional plugin configs
│       └── health.lua         # Health check
├── README.md
└── doc/kickstart.txt
```

## Key Settings

- **Leader key**: Space (default)
- **Theme**: Not set (use `:colorscheme tokyonight` to switch)
- **Indent**: Auto-detected by guess-indent.nvim
- **Terminal escape**: `<Esc><Esc>` to exit terminal mode

## Common Tasks

### Enable an optional plugin

1. Open `~/.config/nvim/init.lua`
2. Find the commented line for the plugin (around line 1823)
3. Uncomment it (remove `--`)
4. Reload config: `:source $MYVIMRC` or restart Neovim

### Add a new plugin

1. Edit `~/.config/nvim/lua/custom/plugins/init.lua`
2. Follow the kickstart.nvim plugin spec (lazy.nvim format)
3. Reload or restart Neovim

### Check plugin status

```vim
:Lazy              " View plugin manager status
:checkhealth       " Check nvim health & dependencies
```

## Kickstart.nvim Philosophy

Kickstart is intentionally minimal. It provides:
- ✅ A good foundation
- ✅ Clear examples of how to structure plugins
- ❌ Not a complete IDE experience

Add plugins as you discover you need them.
