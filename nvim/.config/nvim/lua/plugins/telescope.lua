local function dotfiles_dir()
	local candidates = {
		vim.fn.expand("$HOME/repos/dotfiles"),
		vim.fn.expand("$HOME/dotfiles"),
	}

	for _, path in ipairs(candidates) do
		if vim.fn.isdirectory(path) == 1 then
			return path
		end
	end

	return vim.fn.getcwd()
end

return {
	{
		"nvim-telescope/telescope.nvim",
		version = "*",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-telescope/telescope-ui-select.nvim",
			{ "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
		},
		opts = function()
			local themes = require("telescope.themes")

			return {
				extensions = {
					["ui-select"] = themes.get_dropdown({
						layout_config = { width = 0.5, height = 0.3, anchor = "E", anchor_padding = 10 },
					}),
				},
			}
		end,
		config = function(_, opts)
			local telescope = require("telescope")

			telescope.setup(opts)
			pcall(telescope.load_extension, "fzf")
			pcall(telescope.load_extension, "ui-select")
		end,
		keys = {
			{
				"<leader>/",
				function()
					require("telescope.builtin").current_buffer_fuzzy_find(
						require("telescope.themes").get_ivy({
							layout_config = { height = 0.4, width = 0.8 },
						})
					)
				end,
				desc = "[S]earch fuzzi[/]y in current buffer",
			},
			{ "<leader>sf", function() require("telescope.builtin").find_files() end, desc = "[S]earch [f]iles" },
			{
				"<leader>sa",
				function()
					require("telescope.builtin").find_files({ hidden = true })
				end,
				desc = "[S]earch [a]ll (includes hidden)",
			},
			{
				"<leader>sn",
				function()
					require("telescope.builtin").find_files({
						cwd = dotfiles_dir(),
						hidden = true,
					})
				end,
				desc = "[S]earch [n]eovim (dotfiles)",
			},
			{ "<leader>sl", function() require("telescope.builtin").live_grep() end, desc = "[S]earch [l]ive grep" },
			{ "<leader>sg", function() require("telescope.builtin").git_files() end, desc = "[S]earch [g]it" },
			{ "<leader>s.", function() require("telescope.builtin").oldfiles() end, desc = "[S]earch [.]ld files" },
			{ "<leader>sc", function() require("telescope.builtin").commands() end, desc = "[S]earch [c]ommands" },
			{
				"<leader>ss",
				function()
					require("telescope.builtin").grep_string()
				end,
				mode = { "n", "v" },
				desc = "[S]earch [s]tring (grep)",
			},
			{
				"<leader>sh",
				function()
					require("telescope.builtin").help_tags()
				end,
				desc = "[S]earch [H]elp",
			},
		},
	},
}
