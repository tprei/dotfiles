local builtin = require('telescope.builtin')

require('telescope').load_extension('fzf')
require('telescope').load_extension('file_browser')

vim.keymap.set('n', '<leader>pf', builtin.find_files, {})
vim.keymap.set('n', '<leader>pg', builtin.git_files, {})
vim.keymap.set('n', '<leader>pb', builtin.buffers, {})
vim.keymap.set('n', '<leader>ps', builtin.grep_string, {})
vim.keymap.set('n', '<leader>pl', builtin.live_grep, {})

local actions = require('telescope.actions')
require('telescope').setup({
    defaults = {
        mappings = {
            i = {
                ["<C-j>"] = actions.move_selection_next,
                ["<C-k>"] = actions.move_selection_previous,
            },
        }
    }
})

local filebrowser = require("telescope").extensions.file_browser.file_browser
vim.keymap.set("n", "<leader>pt", filebrowser, { noremap = true })
