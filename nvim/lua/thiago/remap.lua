-- leader = space
vim.g.mapleader = " "

vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv")
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv")

vim.keymap.set("n", "J", "mzJ`z")

vim.keymap.set("n", "<C-u>", "<C-u>zz")
vim.keymap.set("n", "<C-d>", "<C-d>zz")
vim.keymap.set("n", "n", "nzzzv")
vim.keymap.set("n", "N", "Nzzzv")

-- splits
vim.keymap.set("n", "<A-h>", "<C-w>h")
vim.keymap.set("n", "<A-j>", "<C-w>j")
vim.keymap.set("n", "<A-k>", "<C-w>k")
vim.keymap.set("n", "<A-l>", "<C-w>l")

-- tabs
-- leader + t + (n: new, c: close, l: next, h: prev)
vim.keymap.set("n", "<leader>tn", function()
    pcall(vim.cmd.tabnew)
end)

vim.keymap.set("n", "<leader>tc", function()
    pcall(vim.cmd.tabclose)
end)

vim.keymap.set("n", "<s-l>", function()
    pcall(vim.cmd.tabnext)
end)

vim.keymap.set("n", "<s-h>", function()
    pcall(vim.cmd.tabprev)
end)

-- greatest remap ever
vim.keymap.set("x", "<leader>p", [["_dP]])

-- next greatest remap ever : asbjornHaland
vim.keymap.set({ "n", "v" }, "<leader>y", [["+y]])
vim.keymap.set("n", "<leader>Y", [["+Y]])

vim.keymap.set({ "n", "v" }, "<leader>d", [["_d]])

-- This is going to get me cancelled
vim.keymap.set("i", "<C-c>", "<Esc>")

vim.keymap.set("n", "Q", "<nop>")
vim.keymap.set("n", "<leader>f", vim.lsp.buf.format)
vim.keymap.set("n", "<leader>s", [[:%s/\<<C-r><C-w>\>/<C-r><C-w>/gI<Left><Left><Left>]])

-- dont go to next when selecting with *
vim.keymap.set("n", "*", "*``")

-- nvim-tree
vim.keymap.set("n", "<C-n>", function()
    vim.cmd.NvimTreeFindFileToggle()
end)

-- mappings for bufferline
vim.keymap.set("n", "<C-h>", vim.cmd.BufferLineCyclePrev)
vim.keymap.set("n", "<C-l>", vim.cmd.BufferLineCycleNext)

-- mappings for trouble (diagnostics)
vim.keymap.set("n", "<leader>pd", vim.cmd.TroubleToggle)
