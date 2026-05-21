return {
	{ -- for fuzzy finding (files, strings, etc)
		'nvim-telescope/telescope.nvim',
		version = '*',
		dependencies = {
			'nvim-lua/plenary.nvim',
			-- optional but recommended
			{ 'nvim-telescope/telescope-fzf-native.nvim', build = 'make' },
		},
		opts = {
			extensions = { -- customize code actions to make it long and short
				["ui-select"] = {
					require("telescope.themes").get_dropdown({
						layout_config = { width = 0.5, height = 0.3, anchor = "E", anchor_padding = 10 }
					})
				}
			},

		},
		keys = {
			{
				"<leader>/",
				function()
					require('telescope.builtin').current_buffer_fuzzy_find(
						require('telescope.themes').get_ivy {
							layout_config = { height = 0.4, width = 0.8 },
						}
					)
				end,
				desc = '[S]earch fuzzi[/]y in current buffer'
			},
			{ "<leader>sf", function() require('telescope.builtin').find_files() end, desc = '[S]earch [f]iles' },
			{
				"<leader>sn",
				function()
					require('telescope.builtin').find_files({
						cwd = vim.fn.expand("$HOME") .. "/dotfiles"
					})
				end,
				desc = '[S]earch [n]eovim (dotfiles)'
			},
			{ "<leader>sl", function() require('telescope.builtin').live_grep() end,  desc = '[S]earch [l]ive grep' },
			{ "<leader>sg", function() require('telescope.builtin').git_files() end,  desc = '[S]earch [g]it' },
			{ "<leader>s.", function() require('telescope.builtin').oldfiles() end,   desc = '[S]earch [.]ld files' },
			{ "<leader>sc", function() require('telescope.builtin').commands() end,   desc = '[S]earch [c]ommands' },
			{
				"<leader>ss",
				function()
					require("telescope.builtin").live_grep()
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
	{ -- for the selection (for code actions  and other things that rely on vim.ui.select)
		"nvim-telescope/telescope-ui-select.nvim",
		dependencies = {
			'nvim-telescope/telescope.nvim',
		},
		config = function()
			require("telescope").load_extension("ui-select")
		end
	}
}
