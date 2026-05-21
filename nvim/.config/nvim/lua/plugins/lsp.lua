return {
	{
		"mason-org/mason.nvim",
		opts = {},
	},
	{
		"mason-org/mason-lspconfig.nvim",
		dependencies = {
			"mason-org/mason.nvim",
			"neovim/nvim-lspconfig",
			"saghen/blink.cmp",
		},
		opts = function()
			vim.lsp.config("*", { capabilities = require("blink.cmp").get_lsp_capabilities() })

			return {
				ensure_installed = {
					"eslint",
					"gopls",
					"lua_ls",
					"ruff",
					"ruby_lsp",
					"ts_ls",
				},
			}
		end,
	},
}
