--!strict

local types = require("./model")
local engine = require("./engine")

local ui = tern.ui

type Model = types.Model
type Line = types.Line
type Position = types.Position
type Sgr = { [number]: string }
type Hit = { first: number, last: number }
type Glyph = {
	first: number,
	last: number,
	firstByte: number,
	lastByte: number,
	overlay: string,
}

local ESC = "\27"
local RESET = ESC .. "[0m"
local CURSOR = ESC .. "[0;7m"
local SELECT = ESC .. "[0;97;44m"
local MATCH = ESC .. "[0;30;43m"
local SELECT_MATCH = ESC .. "[0;4;97;44m"
local CURSOR_MATCH = ESC .. "[0;4;7m"

local function next_byte(text: string, at: number): number
	local lead = string.byte(text, at)
	if lead < 0x80 then
		return at + 1
	elseif lead < 0xE0 then
		return at + 2
	elseif lead < 0xF0 then
		return at + 3
	end
	return at + 4
end

local function sgr(state: Sgr, sequence: string): ()
	local parameters = string.split(string.sub(sequence, 3, -2), ";")
	local index = 1
	while index <= #parameters do
		local parameter = parameters[index]
		local colon = string.find(parameter, ":", 1, true)
		local code = tonumber(if colon then string.sub(parameter, 1, colon - 1) else parameter)
		if parameter == "" then
			code = 0
		end
		if code == 0 then
			table.clear(state)
		elseif code == 1 then
			state[1] = parameter
		elseif code == 2 then
			state[2] = parameter
		elseif code == 22 then
			state[1], state[2] = nil, nil
		elseif code == 3 or code == 20 then
			state[3] = parameter
		elseif code == 23 then
			state[3] = nil
		elseif code == 4 or code == 21 then
			if parameter == "4:0" then
				state[4] = nil
			else
				state[4] = parameter
			end
		elseif code == 24 then
			state[4] = nil
		elseif code == 5 or code == 6 then
			state[5] = parameter
		elseif code == 25 then
			state[5] = nil
		elseif code == 7 then
			state[6] = parameter
		elseif code == 27 then
			state[6] = nil
		elseif code == 8 then
			state[7] = parameter
		elseif code == 28 then
			state[7] = nil
		elseif code == 9 then
			state[8] = parameter
		elseif code == 29 then
			state[8] = nil
		elseif code and code >= 10 and code <= 19 then
			if code == 10 then
				state[9] = nil
			else
				state[9] = parameter
			end
		elseif code == 26 then
			state[10] = parameter
		elseif code == 50 then
			state[10] = nil
		elseif code == 51 or code == 52 then
			state[11] = parameter
		elseif code == 54 then
			state[11] = nil
		elseif code == 53 then
			state[12] = parameter
		elseif code == 55 then
			state[12] = nil
		elseif code and code >= 60 and code <= 64 then
			state[13] = parameter
		elseif code == 65 then
			state[13] = nil
		elseif code == 73 or code == 74 then
			state[14] = parameter
		elseif code == 75 then
			state[14] = nil
		elseif code == 38 or code == 48 or code == 58 then
			local slot = if code == 38 then 15 elseif code == 48 then 16 else 17
			if colon then
				state[slot] = parameter
			else
				local mode = parameters[index + 1]
				local count = if mode == "2" then 4 elseif mode == "5" then 2 else 0
				if count > 0 and index + count <= #parameters then
					state[slot] = table.concat(parameters, ";", index, index + count)
					index += count
				end
			end
		elseif code and ((code >= 30 and code <= 37) or (code >= 90 and code <= 97)) then
			state[15] = parameter
		elseif code == 39 then
			state[15] = nil
		elseif code and ((code >= 40 and code <= 47) or (code >= 100 and code <= 107)) then
			state[16] = parameter
		elseif code == 49 then
			state[16] = nil
		elseif code == 59 then
			state[17] = nil
		end
		index += 1
	end
end

local function restore(state: Sgr): string
	local parameters: { string } = {}
	for slot = 1, 17 do
		local parameter = state[slot]
		if parameter then
			table.insert(parameters, parameter)
		end
	end
	if #parameters > 0 then
		return RESET .. ESC .. "[" .. table.concat(parameters, ";") .. "m"
	end
	return RESET
end

local function glyphs(text: string, left: number, cols: number): { Glyph }
	local first = left
	local at = engine.byte(text, first)
	while at <= #text and engine.width(utf8.codepoint(text, at, at)) == 0 and first > 1 do
		local previous = utf8.offset(text, -1, at)
		if not previous then
			break
		end
		first -= 1
		at = previous
	end
	local visible: { Glyph } = {}
	local column = first
	local cells = 0
	while at <= #text do
		local following = next_byte(text, at)
		local width = engine.width(utf8.codepoint(text, at, at))
		if width == 0 and #visible > 0 then
			local previous = visible[#visible]
			previous.last = column
			previous.lastByte = following - 1
		else
			if cells + width > cols then
				break
			end
			table.insert(visible, {
				first = column,
				last = column,
				firstByte = at,
				lastByte = following - 1,
				overlay = "",
			})
			cells += width
		end
		column += 1
		at = following
	end
	return visible
end

local function hits(text: string, query: string, fold: boolean, first: number, last: number): { Hit }
	local matches: { Hit } = {}
	if query == "" then
		return matches
	end
	local start = math.max(1, first - #query + 1)
	local finish = math.min(#text, last + #query - 1)
	local source = string.sub(text, start, finish)
	if fold then
		source = string.lower(source)
	end
	local at = 1
	while at <= #source do
		local from, to = string.find(source, query, at, true)
		if not from or not to then
			break
		end
		if to + start - 1 >= first and from + start - 1 <= last then
			table.insert(matches, { first = from + start - 1, last = to + start - 1 })
		end
		at = from + 1
	end
	return matches
end

local function overlays(model: Model, row: number, text: string, visible: { Glyph }, query: string, fold: boolean): ()
	if #visible == 0 then
		return
	end
	local first, last = engine.selected(model, row)
	local matches = hits(text, query, fold, visible[1].firstByte, visible[#visible].lastByte)
	local hit = 1
	for _, glyph in visible do
		while hit <= #matches and matches[hit].last < glyph.firstByte do
			hit += 1
		end
		local matched = hit <= #matches and matches[hit].first <= glyph.lastByte
		local selected = first ~= nil and last ~= nil and first <= glyph.last and last >= glyph.first
		local cursor = model.cursor.line == row
			and model.cursor.column >= glyph.first
			and model.cursor.column <= glyph.last
		if cursor then
			glyph.overlay = if matched or selected then CURSOR_MATCH else CURSOR
		elseif selected then
			glyph.overlay = if matched then SELECT_MATCH else SELECT
		elseif matched then
			glyph.overlay = MATCH
		end
	end
end

local function control(text: string, at: number): (number, string?)
	local second = string.byte(text, at + 1)
	if second == 91 then
		local finish = at + 2
		while finish <= #text do
			local code = string.byte(text, finish)
			if code >= 0x40 and code <= 0x7E then
				return finish + 1, if code == 109 then string.sub(text, at, finish) else nil
			end
			finish += 1
		end
		return #text + 1, nil
	elseif second == 93 then
		local finish = at + 2
		while finish <= #text do
			local code = string.byte(text, finish)
			if code == 7 then
				return finish + 1, nil
			elseif code == 27 and string.byte(text, finish + 1) == 92 then
				return finish + 2, nil
			end
			finish += 1
		end
		return #text + 1, nil
	end
	local finish = at + 1
	while finish <= #text and string.byte(text, finish) >= 0x20 and string.byte(text, finish) <= 0x2F do
		finish += 1
	end
	return math.min(#text + 1, finish + 1), nil
end

local function viewport_line(model: Model, row: number, line: Line, query: string, fold: boolean): string
	local visible = glyphs(line.text, model.left, model.cols)
	overlays(model, row, line.text, visible, query, fold)
	local state: Sgr = {}
	local output: { string } = {}
	local column = 1
	local at = 1
	local current = 1
	local active = ""
	local started = false
	local captured: string? = nil
	local runFirst = 0
	local runLast = 0
	local finish = if #visible > 0 then visible[#visible].last else 0
	while at <= #line.ansi do
		local code = string.byte(line.ansi, at)
		if code == 27 then
			if runFirst > 0 then
				table.insert(output, string.sub(line.ansi, runFirst, runLast))
				runFirst = 0
			end
			local following, sequence = control(line.ansi, at)
			if sequence then
				sgr(state, sequence)
				captured = nil
				if started then
					table.insert(output, sequence)
					if active ~= "" then
						table.insert(output, active)
					end
				end
			end
			at = following
		elseif code < 32 or code == 127 then
			if runFirst > 0 then
				table.insert(output, string.sub(line.ansi, runFirst, runLast))
				runFirst = 0
			end
			at += 1
		else
			if column > finish then
				break
			end
			local following = next_byte(line.ansi, at)
			if column >= visible[1].first then
				while column > visible[current].last do
					current += 1
				end
				local overlay = visible[current].overlay
				if not started or overlay ~= active then
					if runFirst > 0 then
						table.insert(output, string.sub(line.ansi, runFirst, runLast))
						runFirst = 0
					end
					local styled: string
					if captured == nil then
						styled = restore(state)
						captured = styled
					else
						styled = captured
					end
					table.insert(output, styled)
					if overlay ~= "" then
						table.insert(output, overlay)
					end
					started = true
					active = overlay
				end
				if runFirst == 0 then
					runFirst = at
				end
				runLast = following - 1
			end
			column += 1
			at = following
		end
	end
	if runFirst > 0 then
		table.insert(output, string.sub(line.ansi, runFirst, runLast))
	end
	if #visible == 0 then
		local first, last = engine.selected(model, row)
		if model.cursor.line == row then
			table.insert(output, CURSOR)
		elseif first ~= nil and last ~= nil and (line.text == "" or (first <= model.left and last >= model.left)) then
			table.insert(output, SELECT)
		end
		table.insert(output, " ")
	end
	table.insert(output, RESET)
	return table.concat(output)
end

local function label(role: string, spans: { Span | string }, grow: number?): Node
	return ui.node("text", {
		role = role,
		spans = spans,
		wrap = "none",
		lines = 1,
		grow = grow,
	})
end

local function position(position: Position): string
	return tostring(position.line) .. ":" .. tostring(position.column)
end

local function selection(model: Model, anchor: Position): string
	local first = anchor
	local last = model.cursor
	if first.line > last.line or (first.line == last.line and first.column > last.column) then
		first, last = last, first
	end
	if model.linewise then
		return tostring(first.line) .. "–" .. tostring(last.line)
	end
	return position(first) .. "–" .. position(last)
end

local function draft(text: string, cells: number): string
	local at = #text + 1
	local used = 0
	while at > 1 do
		local previous = utf8.offset(text, -1, at)
		if not previous then
			break
		end
		local width = engine.width(utf8.codepoint(text, previous, previous))
		if used + width > cells then
			break
		end
		used += width
		at = previous
	end
	while at <= #text and engine.width(utf8.codepoint(text, at, at)) == 0 do
		at = next_byte(text, at)
	end
	return string.sub(text, at)
end

local function hints(model: Model): string
	if model.status ~= "ready" then
		return "q/Esc exit"
	elseif model.anchor then
		if model.cols < 34 then
			return "y copy  q exit  Esc clear"
		end
		return "y/Enter copy · Esc clear · q exit · o swap · hjkl move · /? find"
	elseif model.cols < 24 then
		return "y copy  q exit"
	elseif model.cols < 50 then
		return "y copy  q exit  v select  / find"
	end
	return "y/Enter copy · q/Esc exit · hjkl move · v/V select · /? find · n/N next · g/G ends"
end

local function dock(model: Model): Node
	local mode = "COPY"
	if model.status == "loading" then
		mode = "LOADING"
	elseif model.status == "error" then
		mode = "ERROR"
	elseif model.searching then
		mode = "SEARCH"
	elseif model.anchor then
		mode = if model.linewise then "LINES" else "SELECT"
	end
	local details: { Span | string } = {}
	if model.searching then
		table.insert(details, ui.span("Enter find · Esc cancel", "muted"))
	else
		if model.message ~= "" and model.status == "ready" then
			table.insert(details, model.message)
		end
		if model.anchor then
			if #details > 0 then
				table.insert(details, "  ")
			end
			table.insert(details, ui.span(selection(model, model.anchor), "mono"))
		end
		if model.query ~= "" then
			if #details > 0 then
				table.insert(details, "  ")
			end
			table.insert(details, ui.span((if model.searchDirection < 0 then "?" else "/") .. model.query, "accent"))
		end
	end
	if model.count ~= "" then
		if #details > 0 then
			table.insert(details, "  ")
		end
		table.insert(details, ui.span("×" .. model.count, "strong mono"))
	end
	local header: { Node } = {
		label("copymode.mode", { mode }),
		label("copymode.details", details, 1),
	}
	if model.status == "ready" then
		table.insert(header, label("copymode.position", { tostring(model.cursor.line) .. "/" .. tostring(#model.lines) }))
	end
	local second: Node
	if model.searching then
		local prefix = if model.searchDirection < 0 then "?" else "/"
		second = label("copymode.search", {
			ui.span(prefix, "accent"),
			ui.span(draft(model.searchDraft, math.max(0, model.cols - 2))),
			ui.span(" ", "mark"),
		})
	else
		second = label("copymode.hints", { hints(model) })
	end
	local root = ui.col({
		ui.node("col", { role = "copymode.dock-content", gap = "none" }, {
			ui.node("row", { role = "copymode.status", gap = "none" }, header),
			second,
		}),
	})
	root.p = { role = "copymode.dock" }
	return root
end

local function render(model: Model): BlockView
	local content: { Node } = {}
	if model.status == "ready" then
		local query = if model.searching then model.searchDraft else model.query
		local fold = not string.find(query, "%u")
		if fold then
			query = string.lower(query)
		end
		for row = model.top, math.min(#model.lines, model.top + model.rows - 1) do
			local text = viewport_line(model, row, model.lines[row], query, fold)
			local line = ui.ansi(text)
			line.p = {
				text = text,
				key = tostring(row),
				role = "copymode.line",
				cols = model.cols,
				min = { h = "1lines" },
			}
			table.insert(content, line)
		end
	else
		table.insert(content, ui.node("text", {
			role = "copymode.message",
			text = model.message,
			tone = if model.status == "error" then "error" else "pending",
			wrap = "word",
			lines = math.min(3, model.rows),
		}))
	end
	local viewport = ui.node("col", {
		role = "copymode.viewport",
		gap = "none",
		min = { h = tostring(model.rows) .. "lines" },
		max = { h = tostring(model.rows) .. "lines" },
	}, content)
	local main = ui.col({ viewport })
	main.p = { role = "copymode.main" }
	return {
		main = main,
		dock = dock(model),
	}
end

return { render = render }
