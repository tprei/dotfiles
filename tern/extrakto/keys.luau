--!strict

local types = require("./model")

type Model = types.Model
type Intent = types.Intent

local function length(text: string): number
	local count = utf8.len(text)
	assert(count ~= nil)
	return count
end

local function byte_at(text: string, cursor: number): number
	local offset = utf8.offset(text, cursor + 1)
	assert(offset ~= nil)
	return offset
end

local function edit(model: Model, first: number, last: number, text: string): Intent
	local query = string.sub(model.query, 1, byte_at(model.query, first) - 1)
		.. text
		.. string.sub(model.query, byte_at(model.query, last))
	return { kind = "query", query = query, cursor = first + length(text) }
end

local function space_at(text: string, cursor: number): boolean
	return string.match(string.sub(text, byte_at(text, cursor), byte_at(text, cursor + 1) - 1), "%s") ~= nil
end

local function word_back(text: string, cursor: number): number
	local at = cursor
	while at > 0 and space_at(text, at - 1) do
		at -= 1
	end
	while at > 0 and not space_at(text, at - 1) do
		at -= 1
	end
	return at
end

local function word_forward(text: string, cursor: number): number
	local at = cursor
	local count = length(text)
	while at < count and not space_at(text, at) do
		at += 1
	end
	while at < count and space_at(text, at) do
		at += 1
	end
	return at
end

local function caret(model: Model, cursor: number): Intent
	return { kind = "query", query = model.query, cursor = cursor }
end

local function intent(model: Model, key: Key): Intent
	local name = key.name
	local cursor = model.cursor
	if name == "paste" and key.text then
		local text = string.gsub(key.text, "[\r\n]", "")
		return edit(model, cursor, cursor, text)
	end
	if key.meta then
		return { kind = "none" }
	end
	if key.ctrl and not key.alt then
		if name == "p" or name == "k" then
			return { kind = "move", by = -1 }
		elseif name == "n" or name == "j" then
			return { kind = "move", by = 1 }
		elseif name == "h" then
			return caret(model, math.max(0, cursor - 1))
		elseif name == "l" then
			return caret(model, math.min(length(model.query), cursor + 1))
		elseif name == "home" then
			return { kind = "first" }
		elseif name == "end" then
			return { kind = "last" }
		elseif name == "e" then
			return { kind = "edit" }
		elseif name == "f" then
			return { kind = "filter" }
		elseif name == "g" then
			return { kind = "scope" }
		elseif name == "w" then
			return edit(model, word_back(model.query, cursor), cursor, "")
		elseif name == "u" then
			return edit(model, 0, cursor, "")
		end
		return { kind = "none" }
	end
	if key.alt and not key.ctrl then
		if name == "left" then
			return caret(model, word_back(model.query, cursor))
		elseif name == "right" then
			return caret(model, word_forward(model.query, cursor))
		elseif name == "backspace" then
			return edit(model, word_back(model.query, cursor), cursor, "")
		end
	end
	if not key.ctrl and not key.alt then
		if name == "escape" then
			return { kind = "close" }
		elseif name == "tab" then
			if key.shift then
				return { kind = "mark" }
			end
			return { kind = "paste" }
		elseif name == "enter" then
			return { kind = "copy" }
		elseif name == "up" then
			return { kind = "move", by = -1 }
		elseif name == "down" then
			return { kind = "move", by = 1 }
		elseif name == "page_up" then
			return { kind = "move", by = -10 }
		elseif name == "page_down" then
			return { kind = "move", by = 10 }
		elseif name == "left" then
			return caret(model, math.max(0, cursor - 1))
		elseif name == "right" then
			return caret(model, math.min(length(model.query), cursor + 1))
		elseif name == "home" then
			return caret(model, 0)
		elseif name == "end" then
			return caret(model, length(model.query))
		elseif name == "backspace" then
			return edit(model, math.max(0, cursor - 1), cursor, "")
		elseif name == "delete" then
			return edit(model, cursor, math.min(length(model.query), cursor + 1), "")
		end
	end
	if key.text and not key.ctrl then
		return edit(model, cursor, cursor, key.text)
	end
	return { kind = "none" }
end

local function event_intent(model: Model, ev: UiEvent): Intent
	if ev.id ~= "layer.extract" then
		return { kind = "none" }
	end
	if ev.ev == "select" and type(ev.item) == "string" then
		local selected_index: number? = nil
		local item_index: number? = nil
		for index, match in model.matches do
			if match.candidate.id == model.selected then
				selected_index = index
			end
			if match.candidate.id == ev.item then
				item_index = index
			end
		end
		if selected_index and item_index then
			return { kind = "move", by = item_index - selected_index }
		end
	elseif ev.ev == "activate" and type(ev.item) == "string" then
		return { kind = "paste" }
	elseif ev.ev == "action" then
		if ev.act == "paste" then
			return { kind = "paste" }
		elseif ev.act == "copy" then
			return { kind = "copy" }
		elseif ev.act == "edit" then
			return { kind = "edit" }
		elseif ev.act == "close" then
			return { kind = "close" }
		elseif ev.act == "mark" then
			return { kind = "mark" }
		elseif ev.act == "clear" then
			return { kind = "query", query = "", cursor = 0 }
		end
	end
	return { kind = "none" }
end

return { intent = intent, event_intent = event_intent }
