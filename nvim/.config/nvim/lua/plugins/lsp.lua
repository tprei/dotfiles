local function executable(name)
	return vim.fn.executable(name) == 1
end

local function ensure_installed_servers()
	local servers = {
		"eslint",
		"lua_ls",
		"ruff",
		"ts_ls",
	}

	if executable("go") then
		table.insert(servers, "gopls")
	end

	if executable("gem") then
		table.insert(servers, "ruby_lsp")
	end

	return servers
end

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
				ensure_installed = ensure_installed_servers(),
			}
		end,
	},
}
