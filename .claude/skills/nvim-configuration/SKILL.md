---
name: nvim-configuration
description: Quick reference for browsing and understanding nvim configuration, keybindings, and plugins
type: skill
---

# nvim-configuration

Quick reference skill for navigating your Neovim setup and answering questions about configuration, keybindings, plugins, and troubleshooting.

## Usage

Ask about:
- **Keybindings**: What key combination does X do? How do I rebind something?
- **Plugins**: What plugins are installed? How do I configure them?
- **Configuration**: Where is setting X? How do I add a new plugin?
- **Troubleshooting**: Why isn't X working? How do I debug this?

Examples:
- "What does `<leader>ss` do in my config?"
- "How do I add a new plugin?"
- "What's the keybinding for goto definition?"
- "Show me the keybindings for telescope"

## Setup

Your config is stored at `~/.config/nvim/` and uses **kickstart.nvim** as a starting point with custom plugins in `lua/custom/plugins/`.

## Key Files

- `init.lua` - Main configuration file (keybindings, plugins, settings)
- `lua/custom/plugins/init.lua` - Custom plugins you've added
- `lua/kickstart/plugins/` - Kickstart plugin configurations

## Common Commands

- `:e $MYVIMRC` or `:e ~/.config/nvim/init.lua` - Edit main config
- `:so $MYVIMRC` - Reload config
- `:checkhealth` - Check nvim health/dependencies
