local function append_text_lines(lines, text)
	local split = vim.split(text, "\n", { plain = true })
	while #split > 0 and split[#split] == "" do
		table.remove(split)
	end
	for _, line in ipairs(split) do
		table.insert(lines, line)
	end
end

local function history(opts)
	local pickers = require("telescope.pickers")
	local finders = require("telescope.finders")
	local conf = require("telescope.config").values
	local actions = require("telescope.actions")
	local actions_state = require("telescope.actions.state")
	local previewers = require("telescope.previewers")

	local items_history = require("ai_ask.history")

	local opts = opts or {}

	-- create the picker and search previous asks
	pickers
		.new(opts, {
			prompt_title = "Previous asks",
			finder = finders.new_table({
				results = items_history.list_items(),
				entry_maker = function(item)
					return {
						value = item,
						display = item.prompt,
						ordinal = item.prompt,
					}
				end,
			}),
			sorter = conf.generic_sorter(opts),
			attach_mappings = function(prompt_bufnr, map)
				actions.select_default:replace(function()
					local selection = actions_state.get_selected_entry()
					actions.close(prompt_bufnr)
				end)
				return true
			end,
			previewer = previewers.new_buffer_previewer({
				define_preview = function(self, entry)
					local item = entry.value
					local lines = {
						"Prompt: " .. item.prompt,
						"Status: " .. item.status,
						"",
						"Answer:",
					}

					append_text_lines(lines, table.concat(item.answer_chunks, ""))

					table.insert(lines, "")
					table.insert(lines, "Error:")

					append_text_lines(lines, table.concat(item.error_chunks, ""))

					vim.api.nvim_buf_set_lines(self.state.bufnr, 0, -1, false, lines)
				end,
			}),
		})
		:find()
end

-- creates a input for the user to ask any questions
-- if the string is cancelled or empty, do nothing, otherwise calls core.ask(prompt)
local function prompt()
	vim.ui.input({ prompt = "Ask away" }, function(input)
		if input == nil or input == "" then -- aborted
			return
		end

		local core = require("ai_ask.core")
		core.ask(input)

		history()
	end)
end

return {
	prompt = prompt,
	history = history,
}
