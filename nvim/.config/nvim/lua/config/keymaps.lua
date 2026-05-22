--[[
--Leader
--]]
--
-- map leader to space
-- same for local leader
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- [[
-- Basic Keymaps
-- ]]
--

-- save on <leader>w
vim.keymap.set('n', '<leader>w', '<cmd>write<CR>', { desc = '[W]rite file' })

-- refresh search highlighting on ESC
vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')

-- yank whole buffer with <leader>ya
vim.keymap.set('n', '<leader>ya', 'ggVGy<C-o>zz<CR>', { desc = "[Y]ank [a]ll" })

-- diagnostics
vim.keymap.set('n', '<leader>d', vim.diagnostic.open_float, { desc = "Open [D]iagnostics Float" })
vim.keymap.set('n', '<leader>q', vim.diagnostic.setloclist, { desc = "Open Diagnostics [Q]uickfix list" })
vim.keymap.set('n', '[[', function() vim.diagnostic.jump({ count = -1, float = true }) end,
	{ desc = "Go to previous diagnostic" })
vim.keymap.set('n', ']]', function() vim.diagnostic.jump({ count = 1, float = true }) end,
	{ desc = "Go to next diagnostic" })


-- delete inside quotes
vim.keymap.set('n', 'diq', 'di\"', { desc = '[Delete] [i]nner [q]uotes' })

-- change inside quotes
vim.keymap.set('n', 'ciq', 'ci\"', { desc = '[change] [i]nner [q]uotes' })

-- delete inside braces
vim.keymap.set('n', 'dib', 'di{', { desc = '[Delete] [i]nner [b]races' })

-- delete around braces
vim.keymap.set('n', 'dab', 'da{', { desc = '[Delete] [a]round [b]races' })

-- change inside braces
vim.keymap.set('n', 'cib', 'ci{', { desc = '[change] [i]nner [b]races' })

-- change around braces
vim.keymap.set('n', 'cab', 'ca{', { desc = '[change] [a]round [b]races' })


-- [[
-- Movement
-- ]]
--
-- Nuke arrow keys in normal mode
vim.keymap.set('n', '<left>', '')
vim.keymap.set('n', '<right>', '')
vim.keymap.set('n', '<down>', '')
vim.keymap.set('n', '<up>', '')

-- map 'gm' as go to mark
vim.keymap.set('n', 'gm', "`", {desc = '[G]o to [M]ark'})


-- [[
-- Formatting
-- ]]
vim.keymap.set(
	'n',
	"<leader>f",
	function()
		require('conform').format({ async = true, lsp_format = 'fallback' })
	end,
	{ desc = "[F]ormat buffer" }
)
