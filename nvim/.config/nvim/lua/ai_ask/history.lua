local cnt = 0
local items = {}

---@alias ChunkType "answer"|"error"
local chunk_type = {
	answer = "answer",
	error = "error",
}

---@alias AskStatus "created"|"processing"|"succeeded"|"errored"
local status_type = {
	created = "created",
	processing = "processing",
	succeeded = "succeeded",
	errored = "errored",
}

---@class HistoryItem
---@field id number
---@field prompt string
---@field enriched_prompt string
---@field answer_chunks string[]
---@field error_chunks string[]
---@field status AskStatus

-- create new item given a prompt and enriched_prompt
---@return HistoryItem
local function create_item(prompt, enriched_prompt)
	cnt = cnt + 1
	local new_item = {
		id = cnt,
		prompt = prompt,
		enriched_prompt = enriched_prompt,
		answer_chunks = {},
		error_chunks = {},
		status = status_type.created,
	}

	table.insert(items, new_item)

	return new_item
end

-- append chunk of answer text to an item by id
---@param type ChunkType
local function append_chunk_by_id(id, chunk, type)
	if items[id] == nil then
		error("id not found: " .. id)
	end

	if type == "answer" then
		table.insert(items[id]["answer_chunks"], chunk)
	elseif type == "error" then
		table.insert(items[id]["error_chunks"], chunk)
	else
		error("unexpected chunk type" .. type)
	end
end

-- note marking as failed doesn't mean we will stop receiving other chunks
---@param status AskStatus
local function mark_as(id, status)
	if items[id] == nil then
		error("id not found: " .. id)
	end
	items[id]["status"] = status
end

local function list_items()
	return items
end

local function get_by_id(id)
	return items[id]
end

return {
	create_item = create_item,
	append_chunk_by_id = append_chunk_by_id,
	mark_as = mark_as,
	list_items = list_items,
	get_by_id = get_by_id,
	chunk_type = chunk_type,
	status_type = status_type,
}
