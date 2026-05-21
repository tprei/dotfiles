--
--[[
--Leader and main group (for autocmd's)
--]]
--
-- map leader to space
-- same for local leader
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- create dotfiles autogroup, which gets cleared once config is re-sourced
vim.api.nvim_create_augroup('dotfiles', { clear = true })

-- my opts, globals and autocmds
require('config')

-- my keymaps
require('config.keymaps')

-- lazy.nvim
require('config.lazy')

-- theme, lazy.nvim installed it
vim.cmd.colorscheme("gruvbox")
