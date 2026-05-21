return {
	{
		"nvim-tree/nvim-tree.lua",
		opts = {
			git = {
				enable = false,
			},
		},
		config = function (_, opts)
			require('nvim-tree').setup(opts)
			vim.keymap.set('n', '<M-,>', '<cmd>NvimTreeFindFileToggle<CR>', { desc = '[E]xplore [T]oggle'})
		end
	}
}
