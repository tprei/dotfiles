local history = require("ai_ask.history")

-- Main coordinationg function for asking a question
local function ask(prompt)
	-- TODO: call a refiner module that actually extracts the context necessary
	local enriched_prompt = "[enriched] " .. prompt

	-- create history
	local new_item = history.create_item(prompt, enriched_prompt)

	-- update history (processing)
	history.mark_as(new_item.id, history.status_type.processing)

	-- call provider
	require("ai_ask.provider").run(enriched_prompt, {
		on_stdout = function(chunk)
			-- a nil chunk is ignored as it would truncate the table
			if chunk ~= nil then
				history.append_chunk_by_id(new_item.id, chunk, history.chunk_type.answer)
			end
		end,
		on_stderr = function(chunk)
			history.append_chunk_by_id(new_item.id, chunk, history.chunk_type.error)
		end,
		on_exit = function(code)
			if code == 0 then
				history.mark_as(new_item.id, history.status_type.succeeded)
			else
				history.mark_as(new_item.id, history.status_type.errored)
			end
		end,
	})

	-- return item
	return new_item
end

return {
	ask = ask,
}
