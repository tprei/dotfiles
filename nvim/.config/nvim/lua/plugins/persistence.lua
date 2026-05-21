return {
	{
		"folke/persistence.nvim",
			event = "BufReadPre",
			opts = {},
			keys = {
				{
					"<leader>ll",
					function()
						require("persistence").load()
						end,
					desc = "[L]oad [l]ast",
				},
				{
					"<leader>ls",
					function()
						require("persistence").select()
						end,
					desc = "[L]oad [s]elect",
				},
			},
	},
}
