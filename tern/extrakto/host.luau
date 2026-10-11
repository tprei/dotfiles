--!strict

local types = require("./model")
local keys = require("./keys")
local renderer = require("./view")

type Candidate = types.Candidate
type Filter = types.Filter
type Intent = types.Intent
type Model = types.Model
type Scope = types.Scope

type Known = {
	candidate: Candidate,
	ord: number,
}

type State = {
	model: Model,
	origin: number?,
	busy: boolean,
	closed: boolean,
	db: string,
	gen: number,
	searching: boolean,
	known: { [string]: Known },
}

type SearchHeader = {
	total: number,
	count: number,
}

type SearchRow = {
	id: string,
	text: string,
	kind: string,
	pane: number,
	screen: boolean,
	line: number,
	source: string,
	ord: number,
	hits: { { number } },
}

local CAPTURE_TIMEOUT_MS = 60000
local SEARCH_TIMEOUT_MS = 10000
local ACTION_TIMEOUT_MS = 20000
local running: { [number]: State } = {}
local serial = 0

local function shell(): string
	return tern.getenv("SHELL") or "/bin/sh"
end

local function trim(text: string): string
	text = string.gsub(text, "^%s+", "")
	return string.gsub(text, "%s+$", "")
end

local function failure_message(result: ProcessResult, action: string, timeout: string?): string
	local reason = trim(result.stderr)
	if reason ~= "" then
		return reason
	end
	if result.timed_out then
		return if timeout then action .. " timed out after " .. timeout else action .. " timed out"
	end
	if result.status < 0 then
		return action .. " was killed"
	end
	return action .. " failed with exit " .. tostring(result.status)
end

local function live(pane: number): boolean
	for _, info in tern.pane.list() do
		if info.pane == pane then
			return true
		end
	end
	return false
end

local function gone(state: State, pane: number): boolean
	return state.closed or running[pane] ~= state or not live(pane)
end

local function retire(state: State, pane: number)
	if running[pane] == state then
		running[pane] = nil
	end
end

local function remove_db(path: string)
	if path == "" then
		return
	end
	local ok, err = pcall(function()
		if tern.fs.exists(path) then
			tern.fs.remove(path)
		end
	end)
	if not ok then
		tern.log.warn("extrakto: cannot remove " .. path .. ": " .. trim(tostring(err)))
	end
end

local function sweep()
	local active_panes: { [number]: boolean } = {}
	for _, info in tern.pane.list() do
		active_panes[info.pane] = true
	end
	for pane, st in running do
		if not active_panes[pane] then
			st.closed = true
			remove_db(st.db)
			running[pane] = nil
		end
	end

	local active_dbs: { [string]: boolean } = {}
	for _, st in running do
		if not st.closed and st.db ~= "" then
			active_dbs[st.db] = true
		end
	end

	local ok, result = pcall(function(): { string }
		if not tern.fs.exists(tern.plugin.data) then
			return {}
		end
		return tern.fs.list(tern.plugin.data)
	end)
	if not ok then
		tern.log.warn("extrakto: cannot list " .. tern.plugin.data .. ": " .. trim(tostring(result)))
		return
	end
	local entries: { string } = result

	for _, name in entries do
		if string.match(name, "^extrakto%-capture%-.+%.db$") ~= nil then
			local full_path = tern.plugin.data .. "/" .. name
			if not active_dbs[full_path] then
				remove_db(full_path)
			end
		end
	end
end

local function as_filter(value: any): Filter?
	if value == "word" then
		return "word"
	end
	if value == "all" then
		return "all"
	end
	if value == "line" then
		return "line"
	end
	return nil
end

local function as_scope(value: any): Scope?
	if value == "tab" then
		return "tab"
	end
	if value == "pane" then
		return "pane"
	end
	if value == "screen" then
		return "screen"
	end
	return nil
end

local NEXT_FILTER: { [Filter]: Filter } = { word = "all", all = "line", line = "word" }
local NEXT_SCOPE: { [Scope]: Scope } = { tab = "pane", pane = "screen", screen = "tab" }

local function next_filter(current: Filter): Filter
	return NEXT_FILTER[current]
end

local function next_scope(current: Scope): Scope
	return NEXT_SCOPE[current]
end

local function action_items(state: State): { Candidate }
	local entries: { Known } = {}
	for id, is_marked in state.model.marked do
		if is_marked then
			local entry = state.known[id]
			if entry ~= nil then
				table.insert(entries, entry)
			end
		end
	end
	if #entries > 0 then
		table.sort(entries, function(a, b)
			return a.ord < b.ord
		end)
		local items: { Candidate } = {}
		for _, entry in entries do
			table.insert(items, entry.candidate)
		end
		return items
	end
	if state.model.selected ~= nil then
		local entry = state.known[state.model.selected]
		if entry ~= nil then
			return { entry.candidate }
		end
	end
	return {}
end

local function joined(items: { Candidate }): string
	local text = items[1].text
	for index = 2, #items do
		local separator = if items[index].kind == "word" and items[index - 1].kind == "word" then " " else "\n"
		text ..= separator .. items[index].text
	end
	return text
end

local function quoted(items: { Candidate }): string
	local parts: { string } = {}
	for _, item in items do
		table.insert(parts, "'" .. string.gsub(item.text, "'", "'\\''") .. "'")
	end
	return table.concat(parts, " ")
end

local function paste_action(state: State, cx: BlockCx)
	local origin = state.origin
	if origin == nil then
		return
	end
	local items = action_items(state)
	if #items == 0 then
		return
	end
	state.busy = true
	local argv = {
		shell(),
		"-lc",
		'PATH="$HOME/.local/bin:$PATH"; exec tern send "$1" paste "$2"',
		"_",
		tostring(origin),
		joined(items),
	}
	local ok, err = pcall(function()
		tern.process.run(argv, { timeout_ms = ACTION_TIMEOUT_MS }, function(result: ProcessResult)
			state.busy = false
			if gone(state, cx.pane) then
				state.closed = true
				remove_db(state.db)
				retire(state, cx.pane)
				return
			end
			if result.status == 0 then
				state.closed = true
				remove_db(state.db)
				retire(state, cx.pane)
				cx:exit(0)
			else
				cx:toast("error", failure_message(result, "Paste"))
			end
		end)
	end)
	if not ok then
		state.busy = false
		cx:toast("error", trim(tostring(err)))
	end
end

local function edit_action(state: State, cx: BlockCx)
	local origin = state.origin
	if origin == nil then
		return
	end
	local items = action_items(state)
	if #items == 0 then
		return
	end
	state.busy = true
	local argv = {
		shell(),
		"-lc",
		'PATH="$HOME/.local/bin:$PATH"; exec tern run "$1" "$2"',
		"_",
		tostring(origin),
		'"${EDITOR:-vi}" -- ' .. quoted(items),
	}
	local ok, err = pcall(function()
		tern.process.run(argv, { timeout_ms = ACTION_TIMEOUT_MS }, function(result: ProcessResult)
			state.busy = false
			if gone(state, cx.pane) then
				state.closed = true
				remove_db(state.db)
				retire(state, cx.pane)
				return
			end
			if result.status == 0 then
				state.closed = true
				remove_db(state.db)
				retire(state, cx.pane)
				cx:exit(0)
			else
				cx:toast("error", failure_message(result, "Edit"))
			end
		end)
	end)
	if not ok then
		state.busy = false
		cx:toast("error", trim(tostring(err)))
	end
end

local function copy_action(state: State, cx: BlockCx)
	local items = action_items(state)
	if #items == 0 then
		return
	end
	cx:copy(joined(items))
	state.closed = true
	remove_db(state.db)
	retire(state, cx.pane)
	cx:exit(0)
end

local function decode_search(text: string, valid_panes: { [number]: boolean }): (SearchHeader?, { SearchRow }?, string?)
	local lines: { string } = {}
	for line in string.gmatch(text, "[^\r\n]+") do
		table.insert(lines, line)
	end
	if #lines == 0 then
		return nil, nil, "empty search output"
	end

	local ok_header, header = pcall(function()
		return tern.json.decode(lines[1])
	end)
	if not ok_header or type(header) ~= "table" then
		return nil, nil, "invalid search header JSON"
	end
	if type(header.total) ~= "number" or type(header.count) ~= "number" then
		return nil, nil, "invalid search header fields"
	end
	if header.count < 0 or header.count > 300 then
		return nil, nil, "search count out of bounds"
	end
	if #lines - 1 ~= header.count then
		return nil,
			nil,
			"search row count mismatch: expected " .. tostring(header.count) .. ", got " .. tostring(#lines - 1)
	end

	local rows: { SearchRow } = {}
	for i = 2, #lines do
		local ok_row, row = pcall(function()
			return tern.json.decode(lines[i])
		end)
		if not ok_row or type(row) ~= "table" then
			return nil, nil, "invalid search row JSON at line " .. tostring(i)
		end
		if
			type(row.id) ~= "string"
			or type(row.text) ~= "string"
			or type(row.kind) ~= "string"
			or type(row.pane) ~= "number"
			or type(row.screen) ~= "boolean"
			or type(row.line) ~= "number"
			or type(row.source) ~= "string"
			or type(row.ord) ~= "number"
			or type(row.hits) ~= "table"
		then
			return nil, nil, "invalid search row schema at line " .. tostring(i)
		end
		if not valid_panes[row.pane] then
			return nil, nil, "search row references unknown pane: " .. tostring(row.pane)
		end
		table.insert(rows, row)
	end

	return header, rows, nil
end

local function spawn_search(state: State, cx: BlockCx)
	local origin = state.origin
	if origin == nil then
		return
	end
	state.searching = true
	local req_gen = state.gen
	local req_filter = state.model.filter
	local req_scope = state.model.scope
	local req_query = state.model.query

	local argv = {
		shell(),
		"-lc",
		'PATH="$HOME/.local/bin:$PATH"; exec python3 "$1" search "$2" "$3" "$4" "$5" "$6"',
		"_",
		tern.plugin.dir .. "/extract.py",
		state.db,
		req_filter,
		req_scope,
		tostring(origin),
		req_query,
	}

	local ok, err = pcall(function()
		tern.process.run(argv, { timeout_ms = SEARCH_TIMEOUT_MS }, function(result: ProcessResult)
			if gone(state, cx.pane) then
				remove_db(state.db)
				return
			end

			state.searching = false

			if state.gen ~= req_gen then
				spawn_search(state, cx)
				return
			end

			if result.status ~= 0 then
				state.model.status = "error"
				state.model.message = failure_message(result, "Search", tostring(SEARCH_TIMEOUT_MS / 1000) .. " s")
				table.clear(state.model.matches)
				state.model.selected = nil
				state.model.total = 0
				state.model.searching = false
				cx:render()
				return
			end

			local valid_panes: { [number]: boolean } = {}
			for _, p in state.model.panes do
				valid_panes[p.id] = true
			end

			local header, rows, decode_err = decode_search(result.stdout, valid_panes)
			if header == nil or rows == nil then
				state.model.status = "error"
				state.model.message = decode_err or "failed to decode search results"
				table.clear(state.model.matches)
				state.model.selected = nil
				state.model.total = 0
				state.model.searching = false
				cx:render()
				return
			end

			local matches: { types.Match } = {}
			local next_known: { [string]: Known } = {}

			for id, is_marked in state.model.marked do
				if is_marked then
					local existing = state.known[id]
					if existing ~= nil then
						next_known[id] = existing
					end
				end
			end

			for _, row in rows do
				local candidate: Candidate = {
					id = row.id,
					text = row.text,
					kind = row.kind,
					pane = row.pane,
					screen = row.screen,
					line = row.line,
					source = row.source,
				}
				table.insert(matches, {
					candidate = candidate,
					hits = row.hits,
				})
				next_known[row.id] = { candidate = candidate, ord = row.ord }
			end

			state.known = next_known
			state.model.matches = matches
			state.model.total = header.total

			local found = false
			if state.model.selected ~= nil then
				for _, m in matches do
					if m.candidate.id == state.model.selected then
						found = true
						break
					end
				end
			end
			if not found then
				local first = matches[1]
				state.model.selected = if first then first.candidate.id else nil
			end

			state.model.searching = false
			state.model.status = "ready"
			state.model.message = nil
			cx:render()
		end)
	end)

	if not ok then
		state.searching = false
		state.model.status = "error"
		state.model.message = trim(tostring(err))
		table.clear(state.model.matches)
		state.model.selected = nil
		state.model.total = 0
		state.model.searching = false
		cx:render()
	end
end

local function invalidate_search(state: State, cx: BlockCx)
	state.gen += 1
	state.model.searching = true
	if not state.searching then
		spawn_search(state, cx)
	end
end

local function set_filter(state: State, value: Filter, cx: BlockCx): boolean
	if value == state.model.filter then
		return false
	end
	state.model.filter = value
	table.clear(state.model.marked)
	invalidate_search(state, cx)
	return true
end

local function set_scope(state: State, value: Scope, cx: BlockCx): boolean
	if value == state.model.scope then
		return false
	end
	state.model.scope = value
	table.clear(state.model.marked)
	invalidate_search(state, cx)
	return true
end

local function apply(state: State, intent: Intent, cx: BlockCx): boolean
	local model = state.model
	if intent.kind == "none" then
		return false
	elseif intent.kind == "query" then
		local changed = intent.query ~= model.query
		model.query = intent.query
		model.cursor = intent.cursor
		if changed then
			invalidate_search(state, cx)
		end
		return true
	elseif intent.kind == "move" then
		if model.status ~= "ready" or model.searching then
			return false
		end
		local index = 0
		for position, entry in model.matches do
			if entry.candidate.id == model.selected then
				index = position
				break
			end
		end
		local target: number?
		if index > 0 then
			target = math.clamp(index + intent.by, 1, #model.matches)
		elseif intent.by > 0 and #model.matches > 0 then
			target = 1
		end
		local id = if target then model.matches[target].candidate.id else nil
		if id == model.selected then
			return false
		end
		model.selected = id
		return true
	elseif intent.kind == "first" then
		if model.status ~= "ready" or model.searching then
			return false
		end
		local first = model.matches[1]
		local id = if first then first.candidate.id else nil
		if id == model.selected then
			return false
		end
		model.selected = id
		return true
	elseif intent.kind == "last" then
		if model.status ~= "ready" or model.searching then
			return false
		end
		local last = model.matches[#model.matches]
		local id = if last then last.candidate.id else nil
		if id == model.selected then
			return false
		end
		model.selected = id
		return true
	elseif intent.kind == "mark" then
		if model.status ~= "ready" or model.searching then
			return false
		end
		local id = model.selected
		if id == nil then
			return false
		end
		model.marked[id] = not model.marked[id]
		local index = 0
		for position, entry in model.matches do
			if entry.candidate.id == id then
				index = position
				break
			end
		end
		if index > 0 and index < #model.matches then
			model.selected = model.matches[index + 1].candidate.id
		end
		return true
	elseif intent.kind == "filter" then
		return set_filter(state, next_filter(model.filter), cx)
	elseif intent.kind == "scope" then
		return set_scope(state, next_scope(model.scope), cx)
	elseif intent.kind == "paste" then
		if model.status == "ready" and not model.searching and not state.busy then
			paste_action(state, cx)
		end
		return false
	elseif intent.kind == "copy" then
		if model.status == "ready" and not model.searching and not state.busy then
			copy_action(state, cx)
		end
		return false
	elseif intent.kind == "edit" then
		if model.status == "ready" and not model.searching and not state.busy then
			edit_action(state, cx)
		end
		return false
	elseif intent.kind == "close" then
		if not state.busy then
			state.closed = true
			remove_db(state.db)
			retire(state, cx.pane)
			cx:exit(0)
		end
		return false
	end
	return false
end

local function decode_capture(text: string, expected_db: string): (any, string?)
	local ok, decoded = pcall(function()
		return tern.json.decode(text)
	end)
	if not ok then
		return nil, trim(tostring(decoded))
	end
	if
		type(decoded) ~= "table"
		or decoded.db ~= expected_db
		or type(decoded.origin) ~= "number"
		or type(decoded.panes) ~= "table"
		or type(decoded.candidates) ~= "number"
	then
		return nil, "Extrakto helper printed unexpected output"
	end
	for _, pane in decoded.panes do
		if type(pane) ~= "table" or type(pane.id) ~= "number" then
			return nil, "Extrakto helper printed unexpected output"
		end
	end
	return decoded, nil
end

local function capture(state: State, cx: BlockCx)
	local pane = cx.pane
	local argv = {
		shell(),
		"-lc",
		'PATH="$HOME/.local/bin:$PATH"; exec python3 "$1" capture "$2" "$3"',
		"_",
		tern.plugin.dir .. "/extract.py",
		tostring(pane),
		state.db,
	}
	local ok, err = pcall(function()
		if not tern.fs.exists(tern.plugin.data) then
			tern.fs.mkdir(tern.plugin.data)
		end
		tern.fs.write(state.db, "")
		tern.process.run(argv, { timeout_ms = CAPTURE_TIMEOUT_MS }, function(result: ProcessResult)
			if gone(state, pane) then
				remove_db(state.db)
				return
			end
			if result.status ~= 0 then
				remove_db(state.db)
				state.model.status = "error"
				state.model.message = failure_message(result, "Capture", tostring(CAPTURE_TIMEOUT_MS / 1000) .. " s")
				cx:render()
				return
			end
			local decoded, decode_error = decode_capture(result.stdout, state.db)
			if decoded == nil then
				remove_db(state.db)
				state.model.status = "error"
				state.model.message = decode_error
				cx:render()
				return
			end
			state.origin = decoded.origin
			state.model.panes = decoded.panes
			state.model.message = nil
			invalidate_search(state, cx)
		end)
	end)
	if not ok then
		remove_db(state.db)
		state.model.status = "error"
		state.model.message = trim(tostring(err))
		cx:render()
	end
end

tern.block.define("picker", {
	init = function(cx: BlockCx, _args: { string }, _saved: any): State
		serial += 1
		local db_path = tern.plugin.data
			.. "/extrakto-capture-"
			.. tostring(cx.pane)
			.. "-"
			.. tostring(tern.now())
			.. "-"
			.. tostring(serial)
			.. ".db"

		local previous = running[cx.pane]
		if previous ~= nil then
			previous.closed = true
			remove_db(previous.db)
		end

		local state: State = {
			model = {
				status = "loading",
				searching = false,
				message = nil,
				panes = {},
				filter = "word",
				scope = "tab",
				query = "",
				cursor = 0,
				matches = {},
				total = 0,
				selected = nil,
				marked = {},
			},
			origin = nil,
			busy = false,
			closed = false,
			db = db_path,
			gen = 0,
			searching = false,
			known = {},
		}
		running[cx.pane] = state
		tern.timer(0, function()
			if gone(state, cx.pane) then
				remove_db(state.db)
				return
			end
			sweep()
			if gone(state, cx.pane) then
				remove_db(state.db)
				return
			end
			capture(state, cx)
		end)
		return state
	end,
	view = function(state: State, _cx: BlockCx): BlockView
		return renderer.render(state.model)
	end,
	key = function(state: State, key: Key, cx: BlockCx): boolean?
		return apply(state, keys.intent(state.model, key), cx)
	end,
	event = function(state: State, ev: UiEvent, cx: BlockCx)
		if ev.id ~= "layer.extract" then
			return
		end
		if ev.ev == "activate" then
			if state.model.status ~= "ready" or state.model.searching then
				return
			end
			local item = ev.item
			if type(item) ~= "string" then
				return
			end
			local known = false
			for _, entry in state.model.matches do
				if entry.candidate.id == item then
					known = true
					break
				end
			end
			if not known then
				return
			end
			state.model.selected = item
		elseif ev.ev == "action" then
			local act = ev.act
			if act == "tab" then
				local filter: Filter? = as_filter(ev.value)
				if filter ~= nil and set_filter(state, filter, cx) then
					cx:render()
				end
				return
			elseif act == "scope" then
				local scope: Scope? = as_scope(ev.value)
				if scope ~= nil and set_scope(state, scope, cx) then
					cx:render()
				end
				return
			end
		end
		if apply(state, keys.event_intent(state.model, ev), cx) then
			cx:render()
		end
	end,
})
