local herdr_directions = { h = "left", j = "down", k = "up", l = "right" }
local tmux_commands = { h = "TmuxNavigateLeft", j = "TmuxNavigateDown", k = "TmuxNavigateUp", l = "TmuxNavigateRight" }

local function navigate(key)
	local in_herdr = vim.env.HERDR_ENV == "1"
	if vim.env.TMUX and not in_herdr then
		vim.cmd(tmux_commands[key])
		return
	end
	local window = vim.fn.winnr()
	vim.cmd.wincmd(key)
	if in_herdr and vim.fn.winnr() == window then
		vim.system({ vim.env.HERDR_BIN_PATH, "pane", "focus", "--direction", herdr_directions[key], "--current" })
	end
end

return {
	{
		"christoomey/vim-tmux-navigator",
		init = function()
			vim.g.tmux_navigator_no_mappings = 1
		end,
		cmd = {
			"TmuxNavigateLeft",
			"TmuxNavigateDown",
			"TmuxNavigateUp",
			"TmuxNavigateRight",
			"TmuxNavigatePrevious",
			"TmuxNavigatorProcessList",
		},
		keys = {
			{ "<c-h>", function() navigate("h") end, desc = "Window or pane left" },
			{ "<c-j>", function() navigate("j") end, desc = "Window or pane down" },
			{ "<c-k>", function() navigate("k") end, desc = "Window or pane up" },
			{ "<c-l>", function() navigate("l") end, desc = "Window or pane right" },
			{ "<c-\\>", "<cmd><C-U>TmuxNavigatePrevious<cr>" },
		},
	}
}
