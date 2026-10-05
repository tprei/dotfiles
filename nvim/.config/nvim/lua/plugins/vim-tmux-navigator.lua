local directions = { h = "left", j = "down", k = "up", l = "right" }
local tmux_commands = { h = "TmuxNavigateLeft", j = "TmuxNavigateDown", k = "TmuxNavigateUp", l = "TmuxNavigateRight" }

local function tern_rects(node, x, y, w, h, rects)
	if node.Leaf then
		rects[node.Leaf] = { x = x, y = y, w = w, h = h }
		return
	end
	local split = node.Split
	if split.axis == "Row" then
		tern_rects(split.a, x, y, w * split.ratio, h, rects)
		tern_rects(split.b, x + w * split.ratio, y, w * (1 - split.ratio), h, rects)
	else
		tern_rects(split.a, x, y, w, h * split.ratio, rects)
		tern_rects(split.b, x, y + h * split.ratio, w, h * (1 - split.ratio), rects)
	end
end

local function gap(from, to, direction)
	if direction == "left" then
		return from.x - (to.x + to.w)
	end
	if direction == "right" then
		return to.x - (from.x + from.w)
	end
	if direction == "up" then
		return from.y - (to.y + to.h)
	end
	return to.y - (from.y + from.h)
end

local function overlap(from, to, direction)
	if direction == "left" or direction == "right" then
		return math.min(from.y + from.h, to.y + to.h) - math.max(from.y, to.y)
	end
	return math.min(from.x + from.w, to.x + to.w) - math.max(from.x, to.x)
end

local function tern_neighbor(rects, pane, direction)
	local from = rects[pane]
	local best, best_overlap = nil, 1e-6
	for id, to in pairs(rects) do
		local shared = overlap(from, to, direction)
		if math.abs(gap(from, to, direction)) < 1e-6 and shared > best_overlap then
			best, best_overlap = id, shared
		end
	end
	return best
end

local function tern(args)
	local result = vim.system(vim.list_extend({ "tern" }, args), { text = true }):wait(1000)
	assert(result.code == 0, ("tern %s exited %d: %s"):format(args[1], result.code, result.stderr))
	return result.stdout
end

local function tern_focus(direction)
	local pane = tonumber(vim.env.TERN_PANE)
	for _, session in ipairs(vim.json.decode(tern({ "ls", "--json" })).sessions) do
		for _, tab in ipairs(session.tabs) do
			local rects = {}
			tern_rects(tab.splits, 0, 0, 1, 1, rects)
			if rects[pane] then
				local target = tern_neighbor(rects, pane, direction)
				if target then
					tern({ "focus", string.format("%d", target) })
				end
				return
			end
		end
	end
end

local function navigate(key)
	local in_herdr = vim.env.HERDR_ENV == "1"
	if vim.env.TMUX and not in_herdr then
		vim.cmd(tmux_commands[key])
		return
	end
	local window = vim.fn.winnr()
	vim.cmd.wincmd(key)
	if vim.fn.winnr() ~= window then
		return
	end
	if in_herdr then
		vim.system({ vim.env.HERDR_BIN_PATH, "pane", "focus", "--direction", directions[key], "--current" })
	elseif vim.env.TERN_PANE then
		tern_focus(directions[key])
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
