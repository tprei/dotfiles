-- examples for your init.lua

-- disable netrw at the very start of your init.lua (strongly advised)
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

-- set termguicolors to enable highlight groups
vim.opt.termguicolors = true

-- OR setup with some options
require("nvim-tree").setup({
    hijack_directories = {
        auto_open = false,
    },
    sort_by = "case_sensitive",
    actions = {
        open_file = {
            quit_on_open = true
        },
    },
    view = {
        open_file = {
            quit_on_open = true
        },
        adaptive_size = true,
        mappings = {
            list = {
                { key = "u", action = "dir_up" },
            },
        },
        centralize_selection = true,
        relativenumber = true,
    },
    update_focused_file = {
        enable = true,
    },
    renderer = {
        group_empty = true,
    },
    filters = {
        dotfiles = true,
    },
    remove_keymaps = { "<C-l>", "<C-h>" }
})
