return {
	{
		"nvim-treesitter/nvim-treesitter",
		build = ":TSUpdate",
		config = function()
			require("nvim-treesitter").install({
				"typescript",
				"tsx",
				"javascript",
				"go",
				"lua",
				"java",
				"ruby",
			})

			vim.api.nvim_create_autocmd("FileType", {
				group = "dotfiles",
				pattern = {
					"typescript",
					"typescriptreact",
					"javascript",
					"javascriptreact",
					"go",
					"lua",
					"java",
					"ruby",
				},
				callback = function(args)
					vim.treesitter.start(args.buf)
					vim.bo[args.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
				end,
			})
		end,
	},
}
