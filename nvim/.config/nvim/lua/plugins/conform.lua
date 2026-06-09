return {
	{

		"stevearc/conform.nvim",
		opts = {
			formatters_by_ft = {
				lua = { "stylua" },
				go = { "goimports", "gofmt" },
				javascript = { "prettier" },
				javascriptreact = { "prettier" },
				typescript = { "prettier" },
				typescriptreact = { "prettier" },
				ruby = { "rubocop" },
			},
			default_format_opts = {
				lsp_format = "fallback",
			},

		}

	}
}
