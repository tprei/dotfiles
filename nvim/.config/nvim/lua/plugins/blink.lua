return {
	{
		"saghen/blink.cmp",
		version = "1.*",
		opts = {
			sources = {
				default = { "lsp" },
			},
			fuzzy = {
				implementation = "lua",
			},
			keymap = {
				preset = "default",
				["<C-l>"] = { "show", "show_documentation", "hide_documentation" }
			}
		},
	}
}
