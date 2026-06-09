local function executable(name)
	return vim.fn.executable(name) == 1
end

local function version_at_least(current, minimum)
	local function parse(version)
		local parts = {}

		for piece in string.gmatch(version, "%d+") do
			table.insert(parts, tonumber(piece))
		end

		return parts
	end

	local current_parts = parse(current)
	local minimum_parts = parse(minimum)
	local len = math.max(#current_parts, #minimum_parts)

	for i = 1, len do
		local current_part = current_parts[i] or 0
		local minimum_part = minimum_parts[i] or 0

		if current_part ~= minimum_part then
			return current_part > minimum_part
		end
	end

	return true
end

local function ruby_version()
	if not executable("ruby") then
		return nil
	end

	local version = vim.trim(vim.fn.system({ "ruby", "-e", "print RUBY_VERSION" }))
	if vim.v.shell_error ~= 0 or version == "" then
		return nil
	end

	return version
end

local function has_supported_ruby()
	local version = ruby_version()
	return version ~= nil and version_at_least(version, "2.7.0")
end

local function ensure_installed_servers()
	local servers = {
		"eslint",
		"lua_ls",
		"pyright",
		"ruff",
		"ts_ls",
	}

	if executable("go") then
		table.insert(servers, "gopls")
	end

	if executable("gem") and has_supported_ruby() then
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
