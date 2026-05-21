return {
	{

		"stevearc/conform.nvim",
		opts = {
			formatters_by_ft = {
				lua = { "stylua" },
				go = { "goimports", "gofmt" },
				javascript = { "prettierd" },
				typescript = { "prettierd" },
				typescriptreact = { "prettierd" },
				ruby = { "rubocop" },
			},
			default_format_opts = {
				lsp_format = "fallback",
			},

		}

	}
}
