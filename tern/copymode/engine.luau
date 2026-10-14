--!strict

local types = require("./model")

type Line = types.Line
type Model = types.Model
type Position = types.Position
type Result = types.Result

local MAX_COUNT = 1000000
local COUNT_DIGITS = 7

local INTERVALS: { { number } } = {
	{ 0x0000, 0x001F, 0 },
	{ 0x007F, 0x009F, 0 },
	{ 0x0300, 0x036F, 0 },
	{ 0x0483, 0x0489, 0 },
	{ 0x0591, 0x05BD, 0 },
	{ 0x05BF, 0x05BF, 0 },
	{ 0x05C1, 0x05C2, 0 },
	{ 0x05C4, 0x05C5, 0 },
	{ 0x05C7, 0x05C7, 0 },
	{ 0x0610, 0x061A, 0 },
	{ 0x064B, 0x065F, 0 },
	{ 0x0670, 0x0670, 0 },
	{ 0x06D6, 0x06DC, 0 },
	{ 0x06DF, 0x06E4, 0 },
	{ 0x06E7, 0x06E8, 0 },
	{ 0x06EA, 0x06ED, 0 },
	{ 0x0711, 0x0711, 0 },
	{ 0x0730, 0x074A, 0 },
	{ 0x07A6, 0x07B0, 0 },
	{ 0x07EB, 0x07F3, 0 },
	{ 0x0816, 0x0819, 0 },
	{ 0x081B, 0x0823, 0 },
	{ 0x0825, 0x0827, 0 },
	{ 0x0829, 0x082D, 0 },
	{ 0x0859, 0x085B, 0 },
	{ 0x0898, 0x089F, 0 },
	{ 0x08CA, 0x08E1, 0 },
	{ 0x08E3, 0x0902, 0 },
	{ 0x093A, 0x093A, 0 },
	{ 0x093C, 0x093C, 0 },
	{ 0x0941, 0x0948, 0 },
	{ 0x094D, 0x094D, 0 },
	{ 0x0951, 0x0957, 0 },
	{ 0x0962, 0x0963, 0 },
	{ 0x0981, 0x0981, 0 },
	{ 0x09BC, 0x09BC, 0 },
	{ 0x09C1, 0x09C4, 0 },
	{ 0x09CD, 0x09CD, 0 },
	{ 0x09E2, 0x09E3, 0 },
	{ 0x0A01, 0x0A02, 0 },
	{ 0x0A3C, 0x0A3C, 0 },
	{ 0x0A41, 0x0A42, 0 },
	{ 0x0A47, 0x0A48, 0 },
	{ 0x0A4B, 0x0A4D, 0 },
	{ 0x0A70, 0x0A71, 0 },
	{ 0x0E31, 0x0E31, 0 },
	{ 0x0E34, 0x0E3A, 0 },
	{ 0x0E47, 0x0E4E, 0 },
	{ 0x0EB1, 0x0EB1, 0 },
	{ 0x0EB4, 0x0EBC, 0 },
	{ 0x0EC8, 0x0ECD, 0 },
	{ 0x1100, 0x115F, 2 },
	{ 0x135D, 0x135F, 0 },
	{ 0x180B, 0x180F, 0 },
	{ 0x1AB0, 0x1AFF, 0 },
	{ 0x1DC0, 0x1DFF, 0 },
	{ 0x200B, 0x200F, 0 },
	{ 0x202A, 0x202E, 0 },
	{ 0x2060, 0x2064, 0 },
	{ 0x20D0, 0x20F0, 0 },
	{ 0x231A, 0x231B, 2 },
	{ 0x2329, 0x232A, 2 },
	{ 0x23E9, 0x23EC, 2 },
	{ 0x23F0, 0x23F0, 2 },
	{ 0x23F3, 0x23F3, 2 },
	{ 0x25FD, 0x25FE, 2 },
	{ 0x2614, 0x2615, 2 },
	{ 0x2648, 0x2653, 2 },
	{ 0x267F, 0x267F, 2 },
	{ 0x2693, 0x2693, 2 },
	{ 0x26A1, 0x26A1, 2 },
	{ 0x26AA, 0x26AB, 2 },
	{ 0x26BD, 0x26BE, 2 },
	{ 0x26C4, 0x26C5, 2 },
	{ 0x26CE, 0x26CE, 2 },
	{ 0x26D4, 0x26D4, 2 },
	{ 0x26EA, 0x26EA, 2 },
	{ 0x26F2, 0x26F3, 2 },
	{ 0x26F5, 0x26F5, 2 },
	{ 0x26FA, 0x26FA, 2 },
	{ 0x26FD, 0x26FD, 2 },
	{ 0x2705, 0x2705, 2 },
	{ 0x270A, 0x270B, 2 },
	{ 0x2728, 0x2728, 2 },
	{ 0x274C, 0x274C, 2 },
	{ 0x274E, 0x274E, 2 },
	{ 0x2753, 0x2755, 2 },
	{ 0x2757, 0x2757, 2 },
	{ 0x2795, 0x2797, 2 },
	{ 0x27B0, 0x27B0, 2 },
	{ 0x27BF, 0x27BF, 2 },
	{ 0x2B1B, 0x2B1C, 2 },
	{ 0x2B50, 0x2B50, 2 },
	{ 0x2B55, 0x2B55, 2 },
	{ 0x2E80, 0x303E, 2 },
	{ 0x3041, 0x3098, 2 },
	{ 0x3099, 0x309A, 0 },
	{ 0x309B, 0x33FF, 2 },
	{ 0x3400, 0x4DBF, 2 },
	{ 0x4E00, 0x9FFF, 2 },
	{ 0xA000, 0xA4CF, 2 },
	{ 0xA960, 0xA97F, 2 },
	{ 0xAC00, 0xD7A3, 2 },
	{ 0xF900, 0xFAFF, 2 },
	{ 0xFE00, 0xFE0F, 0 },
	{ 0xFE10, 0xFE19, 2 },
	{ 0xFE20, 0xFE2F, 0 },
	{ 0xFE30, 0xFE52, 2 },
	{ 0xFE54, 0xFE66, 2 },
	{ 0xFE68, 0xFE6B, 2 },
	{ 0xFEFF, 0xFEFF, 0 },
	{ 0xFF00, 0xFF60, 2 },
	{ 0xFFE0, 0xFFE6, 2 },
	{ 0x16FE0, 0x16FE4, 2 },
	{ 0x17000, 0x187F7, 2 },
	{ 0x1F004, 0x1F004, 2 },
	{ 0x1F0CF, 0x1F0CF, 2 },
	{ 0x1F18E, 0x1F18E, 2 },
	{ 0x1F191, 0x1F19A, 2 },
	{ 0x1F1E6, 0x1F1FF, 2 },
	{ 0x1F200, 0x1F202, 2 },
	{ 0x1F210, 0x1F23B, 2 },
	{ 0x1F240, 0x1F248, 2 },
	{ 0x1F250, 0x1F251, 2 },
	{ 0x1F260, 0x1F265, 2 },
	{ 0x1F300, 0x1F320, 2 },
	{ 0x1F32D, 0x1F335, 2 },
	{ 0x1F337, 0x1F37C, 2 },
	{ 0x1F37E, 0x1F393, 2 },
	{ 0x1F3A0, 0x1F3CA, 2 },
	{ 0x1F3CF, 0x1F3D3, 2 },
	{ 0x1F3E0, 0x1F3F0, 2 },
	{ 0x1F3F4, 0x1F3F4, 2 },
	{ 0x1F3F8, 0x1F3FA, 2 },
	{ 0x1F3FB, 0x1F3FF, 0 },
	{ 0x1F400, 0x1F43E, 2 },
	{ 0x1F440, 0x1F440, 2 },
	{ 0x1F442, 0x1F4FC, 2 },
	{ 0x1F4FF, 0x1F53D, 2 },
	{ 0x1F54B, 0x1F54E, 2 },
	{ 0x1F550, 0x1F567, 2 },
	{ 0x1F57A, 0x1F57A, 2 },
	{ 0x1F595, 0x1F596, 2 },
	{ 0x1F5A4, 0x1F5A4, 2 },
	{ 0x1F5FB, 0x1F64F, 2 },
	{ 0x1F680, 0x1F6C5, 2 },
	{ 0x1F6CC, 0x1F6CC, 2 },
	{ 0x1F6D0, 0x1F6D2, 2 },
	{ 0x1F6D5, 0x1F6D7, 2 },
	{ 0x1F6DC, 0x1F6DF, 2 },
	{ 0x1F6EB, 0x1F6EC, 2 },
	{ 0x1F6F4, 0x1F6FC, 2 },
	{ 0x1F7E0, 0x1F7EB, 2 },
	{ 0x1F7F0, 0x1F7F0, 2 },
	{ 0x1F90C, 0x1F93A, 2 },
	{ 0x1F93C, 0x1F945, 2 },
	{ 0x1F947, 0x1F9FF, 2 },
	{ 0x1FA70, 0x1FA7C, 2 },
	{ 0x1FA80, 0x1FA88, 2 },
	{ 0x1FA90, 0x1FABD, 2 },
	{ 0x1FABF, 0x1FAC5, 2 },
	{ 0x1FACE, 0x1FADB, 2 },
	{ 0x1FAE0, 0x1FAE8, 2 },
	{ 0x1FAF0, 0x1FAF8, 2 },
	{ 0x20000, 0x2FFFD, 2 },
	{ 0x30000, 0x3FFFD, 2 },
	{ 0xE0001, 0xE0001, 0 },
	{ 0xE0020, 0xE007F, 0 },
	{ 0xE0100, 0xE01EF, 0 },
}

local function width(codepoint: number): number
	local low, high = 1, #INTERVALS
	while low <= high do
		local middle = (low + high) // 2
		local interval = INTERVALS[middle]
		if codepoint < interval[1] then
			high = middle - 1
		elseif codepoint > interval[2] then
			low = middle + 1
		else
			return interval[3]
		end
	end
	return 1
end

local function next_byte(text: string, index: number): number
	local first = string.byte(text, index)
	if first == nil then
		return index + 1
	end
	local span = if first >= 0xF0 then 4 elseif first >= 0xE0 then 3 elseif first >= 0xC0 then 2 else 1
	return math.min(index + span, #text + 1)
end

local function decode(text: string, index: number): number
	local first = string.byte(text, index)
	if first == nil then
		return 32
	end
	local extra: number
	local value: number
	if first >= 0xF0 then
		extra, value = 3, first % 0x08
	elseif first >= 0xE0 then
		extra, value = 2, first % 0x20
	elseif first >= 0xC0 then
		extra, value = 1, first % 0x40
	else
		return first
	end
	if index + extra > #text then
		return first
	end
	local value_so_far = value
	for offset = 1, extra do
		local continuation = string.byte(text, index + offset)
		if continuation == nil or continuation < 0x80 or continuation >= 0xC0 then
			return first
		end
		value_so_far = value_so_far * 0x40 + continuation % 0x40
	end
	return value_so_far
end

local function length(text: string): number
	local count = 0
	local index = 1
	while index <= #text do
		count += 1
		index = next_byte(text, index)
	end
	return count
end

local function byte(text: string, column: number): number
	local index = 1
	for _ = 2, column do
		index = next_byte(text, index)
	end
	return index
end

local function column_of(text: string, target: number): number
	local column = 1
	local index = 1
	while index < target and index <= #text do
		index = next_byte(text, index)
		column += 1
	end
	return column
end

local function cluster_start(text: string, column: number): number
	local unit = 1
	local index = 1
	local start = 1
	while unit <= column and index <= #text do
		if width(decode(text, index)) > 0 then
			start = unit
		end
		index = next_byte(text, index)
		unit += 1
	end
	return start
end

local function previous_byte(text: string, index: number): number
	local at = index - 1
	if at < 1 then
		return 1
	end
	local first = string.byte(text, at)
	while at > 1 and first ~= nil and first >= 0x80 and first < 0xC0 do
		at -= 1
		first = string.byte(text, at)
	end
	return at
end

local function right(text: string, len: number, column: number, index: number): (number, number)
	local next_column = column + 1
	local next_index = next_byte(text, index)
	while next_column <= len and width(decode(text, next_index)) == 0 do
		next_index = next_byte(text, next_index)
		next_column += 1
	end
	if next_column > len then
		return column, index
	end
	return next_column, next_index
end

local function left(text: string, column: number, index: number): (number, number)
	if column <= 1 then
		return column, index
	end
	local previous_column = column - 1
	local previous_index = previous_byte(text, index)
	while previous_column > 1 and width(decode(text, previous_index)) == 0 do
		previous_index = previous_byte(text, previous_index)
		previous_column -= 1
	end
	return previous_column, previous_index
end

local function ensure_visible(model: Model)
	local entry = model.lines[model.cursor.line]
	if entry == nil or entry.text == "" then
		model.left = 1
		return
	end
	local text = entry.text
	local column = model.cursor.column
	if column < model.left then
		model.left = cluster_start(text, column)
		return
	end
	local cells_max = math.max(model.cols, 1)
	local index = byte(text, column)
	local cells = width(decode(text, index))
	local target = column
	while target > 1 do
		local previous_index = previous_byte(text, index)
		local cluster_index = previous_index
		local cluster_column = target - 1
		local cluster_width = width(decode(text, cluster_index))
		while cluster_column > 1 and cluster_width == 0 do
			cluster_index = previous_byte(text, cluster_index)
			cluster_column -= 1
			cluster_width = width(decode(text, cluster_index))
		end
		if cells + cluster_width > cells_max then
			break
		end
		cells += cluster_width
		index = cluster_index
		target = cluster_column
	end
	model.left = target
end

local function viewport(model: Model)
	local rows = math.max(model.rows, 1)
	local line = model.cursor.line
	if line < model.top then
		model.top = line
	elseif line >= model.top + rows then
		model.top = line - rows + 1
	end
	ensure_visible(model)
end

local function place(model: Model, line: number, column: number, sticky: boolean)
	local total = #model.lines
	if total == 0 then
		return
	end
	local at = math.min(math.max(line, 1), total)
	local entry = model.lines[at]
	local len = if entry ~= nil then length(entry.text) else 0
	local col = math.max(1, math.min(column, math.max(len, 1)))
	if entry ~= nil and len > 0 then
		col = cluster_start(entry.text, col)
	end
	model.cursor.line = at
	model.cursor.column = col
	if sticky then
		model.preferred = col
	end
	viewport(model)
end

local function line_length(model: Model, line: number): number
	local entry = model.lines[line]
	if entry == nil then
		return 0
	end
	return length(entry.text)
end

local function blank(text: string): boolean
	return string.match(text, "%S") == nil
end

local function counted(model: Model): number
	local n = tonumber(model.count) or 1
	model.count = ""
	return math.max(1, math.min(n, MAX_COUNT))
end

local function unsupported(model: Model): Result
	model.count = ""
	return "ignored"
end

local function class_of(codepoint: number, big: boolean): number
	if codepoint == 32 or codepoint == 9 then
		return 0
	end
	if big then
		return 1
	end
	if codepoint < 0x80 then
		if
			(codepoint >= 48 and codepoint <= 57)
			or (codepoint >= 65 and codepoint <= 90)
			or (codepoint >= 97 and codepoint <= 122)
			or codepoint == 95
		then
			return 1
		end
		return 2
	end
	return 1
end

local function word_forward(text: string, len: number, column: number, big: boolean): number
	local unit = math.min(column, len)
	local index = byte(text, unit)
	local class = class_of(decode(text, index), big)
	if class > 0 then
		while unit < len and class_of(decode(text, next_byte(text, index)), big) == class do
			index = next_byte(text, index)
			unit += 1
		end
	end
	while unit < len and class_of(decode(text, next_byte(text, index)), big) == 0 do
		index = next_byte(text, index)
		unit += 1
	end
	if unit < len then
		unit += 1
	end
	return unit
end

local function word_back(text: string, len: number, column: number, big: boolean): number
	local target = column - 1
	if target < 1 then
		return 1
	end
	local unit = 1
	local index = 1
	local run_class = 0
	local last_start = 1
	while unit <= target do
		local class = class_of(decode(text, index), big)
		if class ~= run_class then
			if class ~= 0 then
				last_start = unit
			end
			run_class = class
		end
		if unit >= len then
			break
		end
		index = next_byte(text, index)
		unit += 1
	end
	return last_start
end

local function word_end(text: string, len: number, column: number, big: boolean): number
	local unit = math.min(column, len)
	local index = byte(text, unit)
	while unit < len and class_of(decode(text, next_byte(text, index)), big) == 0 do
		index = next_byte(text, index)
		unit += 1
	end
	if unit >= len then
		return math.max(len, 1)
	end
	index = next_byte(text, index)
	unit += 1
	local class = class_of(decode(text, index), big)
	while unit < len and class_of(decode(text, next_byte(text, index)), big) == class do
		index = next_byte(text, index)
		unit += 1
	end
	return unit
end

local function word_kind(name: string, shift: boolean): (string, boolean)
	local lower = string.lower(name)
	local big = shift or name ~= lower
	if lower == "w" or lower == "b" or lower == "e" then
		return lower, big
	end
	return "", big
end

local function span(anchor: Position, cursor: Position): (Position, Position)
	if anchor.line > cursor.line or (anchor.line == cursor.line and anchor.column > cursor.column) then
		return cursor, anchor
	end
	return anchor, cursor
end

type Prepared = {
	raw: string,
	lowered: string,
	sensitive: boolean,
}

local function prepare(model: Model): Prepared?
	local raw = model.query
	if raw == "" then
		return nil
	end
	return { raw = raw, lowered = string.lower(raw), sensitive = raw ~= string.lower(raw) }
end

local function locate(
	text: string,
	raw: string,
	lowered: string,
	sensitive: boolean,
	init: number,
	cap: number?
): number?
	local found: number? = nil
	local at = init
	local haystack = if sensitive then text else string.lower(text)
	while true do
		local hit = if sensitive then string.find(text, raw, at, true) else string.find(haystack, lowered, at, true)
		if hit == nil then
			break
		end
		if cap ~= nil and hit > cap then
			break
		end
		found = hit
		at = hit + #raw
	end
	return found
end

local function search_forward(model: Model, from: Position): Position?
	local parts = prepare(model)
	if parts == nil or #model.lines == 0 then
		return nil
	end
	local raw, lowered, sensitive = parts.raw, parts.lowered, parts.sensitive
	local total = #model.lines
	for line = from.line, total do
		local text = model.lines[line].text
		local init = if line == from.line then byte(text, from.column) + 1 else 1
		local hit = locate(text, raw, lowered, sensitive, init, nil)
		if hit ~= nil then
			return { line = line, column = column_of(text, hit) }
		end
	end
	for line = 1, from.line - 1 do
		local text = model.lines[line].text
		local hit = locate(text, raw, lowered, sensitive, 1, nil)
		if hit ~= nil then
			return { line = line, column = column_of(text, hit) }
		end
	end
	local text = model.lines[from.line].text
	local haystack = if sensitive then text else string.lower(text)
	local hit = string.find(haystack, lowered, 1, true)
	if hit ~= nil and hit <= byte(text, from.column) then
		return { line = from.line, column = column_of(text, hit) }
	end
	return nil
end

local function search_backward(model: Model, from: Position): Position?
	local parts = prepare(model)
	if parts == nil or #model.lines == 0 then
		return nil
	end
	local raw, lowered, sensitive = parts.raw, parts.lowered, parts.sensitive
	local total = #model.lines
	for line = from.line, 1, -1 do
		local text = model.lines[line].text
		local cap = if line == from.line then byte(text, from.column) - 1 else nil
		local hit = locate(text, raw, lowered, sensitive, 1, cap)
		if hit ~= nil then
			return { line = line, column = column_of(text, hit) }
		end
	end
	for line = total, from.line + 1, -1 do
		local text = model.lines[line].text
		local hit = locate(text, raw, lowered, sensitive, 1, nil)
		if hit ~= nil then
			return { line = line, column = column_of(text, hit) }
		end
	end
	local text = model.lines[from.line].text
	local floor = byte(text, from.column)
	local hit = locate(text, raw, lowered, sensitive, floor, nil)
	if hit ~= nil then
		return { line = from.line, column = column_of(text, hit) }
	end
	return nil
end

local function jump(model: Model, found: Position?): Result
	if found == nil then
		model.message = "no match"
		return "changed"
	end
	model.message = ""
	place(model, found.line, found.column, true)
	return "changed"
end

local function execute_search(model: Model): Result
	local found = if model.searchDirection >= 0
		then search_forward(model, model.cursor)
		else search_backward(model, model.cursor)
	return jump(model, found)
end

local function repeat_search(model: Model, direction: number): Result
	if model.query == "" then
		return unsupported(model)
	end
	local found = if direction >= 0
		then search_forward(model, model.cursor)
		else search_backward(model, model.cursor)
	return jump(model, found)
end

local function slice(text: string, first: number, last: number): string
	if last < first or last < 1 then
		return ""
	end
	local finish = byte(text, last + 1)
	while finish <= #text and width(decode(text, finish)) == 0 do
		finish = next_byte(text, finish)
	end
	return string.sub(text, byte(text, first), finish - 1)
end

local function vertical(model: Model, line: number): Result
	place(model, line, model.preferred, false)
	return "changed"
end

local function scroll(model: Model, delta: number): Result
	local total = #model.lines
	local n = counted(model)
	return vertical(model, math.min(math.max(model.cursor.line + delta * n, 1), total))
end

local function selected(model: Model, line: number): (number?, number?)
	local anchor = model.anchor
	if anchor == nil or line < 1 or line > #model.lines then
		return nil, nil
	end
	local first, last = span(anchor, model.cursor)
	if line < first.line or line > last.line then
		return nil, nil
	end
	local len = line_length(model, line)
	if model.linewise then
		return 1, math.max(len, 1)
	end
	if first.line == last.line then
		return first.column, last.column
	end
	if line == first.line then
		return first.column, math.max(len, first.column)
	elseif line == last.line then
		return 1, last.column
	end
	return 1, math.max(len, 1)
end

local function selection(model: Model): string?
	local anchor = model.anchor
	if anchor == nil then
		local entry = model.lines[model.cursor.line]
		if entry == nil then
			return nil
		end
		return entry.text
	end
	local first, last = span(anchor, model.cursor)
	if first.line < 1 or last.line > #model.lines then
		return nil
	end
	local parts: { string } = {}
	for line = first.line, last.line do
		local start_column, end_column = selected(model, line)
		if start_column ~= nil and end_column ~= nil and end_column >= start_column then
			table.insert(parts, slice(model.lines[line].text, start_column, end_column))
		else
			table.insert(parts, "")
		end
	end
	return table.concat(parts, "\n")
end

local function search_key(model: Model, key: Key): Result
	local name = key.name
	if name == "escape" then
		local origin = model.searchOrigin
		model.searching = false
		model.searchDraft = ""
		model.searchOrigin = nil
		if origin ~= nil then
			model.cursor.line = origin.line
			model.cursor.column = origin.column
			model.preferred = origin.column
			viewport(model)
		end
		return "changed"
	end
	if name == "enter" and not key.ctrl and not key.alt and not key.meta then
		model.searching = false
		model.searchOrigin = nil
		if model.searchDraft ~= "" then
			model.query = model.searchDraft
		end
		model.searchDraft = ""
		return execute_search(model)
	end
	if name == "backspace" and not key.ctrl and not key.alt and not key.meta then
		local draft = model.searchDraft
		if draft ~= "" then
			model.searchDraft = string.sub(draft, 1, byte(draft, length(draft)) - 1)
		end
		return "changed"
	end
	if key.text ~= nil and key.text ~= "" and not key.ctrl and not key.meta then
		model.searchDraft ..= string.gsub(key.text, "[\r\n]", "")
		return "changed"
	end
	return unsupported(model)
end

local function motion_key(model: Model, key: Key): Result
	local name = key.name
	local plain = not key.ctrl and not key.alt and not key.meta
	if plain and name == "escape" then
		if model.anchor ~= nil then
			model.anchor = nil
			model.linewise = false
			return "changed"
		end
		return "quit"
	end
	if plain and name == "q" then
		return "quit"
	end
	if plain and (name == "y" or name == "enter") then
		counted(model)
		return "copy"
	end
	if plain and (name == "v" or name == "space") and not key.shift then
		counted(model)
		model.anchor = { line = model.cursor.line, column = model.cursor.column }
		model.linewise = false
		return "changed"
	end
	if plain and (name == "V" or (name == "v" and key.shift)) then
		counted(model)
		model.anchor = { line = model.cursor.line, column = model.cursor.column }
		model.linewise = true
		return "changed"
	end
	if plain and name == "o" then
		local anchor = model.anchor
		if anchor == nil then
			return unsupported(model)
		end
		counted(model)
		local line, column = model.cursor.line, model.cursor.column
		model.cursor.line = anchor.line
		model.cursor.column = anchor.column
		model.anchor = { line = line, column = column }
		model.preferred = anchor.column
		viewport(model)
		return "changed"
	end
	if plain and string.match(name, "^[1-9]$") ~= nil then
		if #model.count < COUNT_DIGITS then
			model.count ..= name
		end
		return "changed"
	end
	if plain and name == "0" and model.count ~= "" then
		if #model.count < COUNT_DIGITS then
			model.count ..= "0"
		end
		return "changed"
	end
	if plain and (name == "h" or name == "left") then
		local n = counted(model)
		local entry = model.lines[model.cursor.line]
		local column = model.cursor.column
		if entry ~= nil then
			local text = entry.text
			local index = byte(text, column)
			for _ = 1, n do
				local moved_column, moved_index = left(text, column, index)
				if moved_column == column then
					break
				end
				column, index = moved_column, moved_index
			end
		end
		place(model, model.cursor.line, column, true)
		return "changed"
	end
	if plain and (name == "l" or name == "right") then
		local n = counted(model)
		local entry = model.lines[model.cursor.line]
		local column = model.cursor.column
		if entry ~= nil then
			local text = entry.text
			local len = length(text)
			local index = byte(text, column)
			for _ = 1, n do
				local moved_column, moved_index = right(text, len, column, index)
				if moved_column == column then
					break
				end
				column, index = moved_column, moved_index
			end
		end
		place(model, model.cursor.line, column, true)
		return "changed"
	end
	if plain and (name == "j" or name == "down") then
		return scroll(model, 1)
	end
	if plain and (name == "k" or name == "up") then
		return scroll(model, -1)
	end
	if plain and name == "0" then
		counted(model)
		place(model, model.cursor.line, 1, true)
		return "changed"
	end
	if plain and name == "^" then
		counted(model)
		local text = model.lines[model.cursor.line].text
		local lead = string.match(text, "^%s*") or ""
		place(model, model.cursor.line, column_of(text, #lead + 1), true)
		return "changed"
	end
	if plain and (name == "$" or name == "end") then
		counted(model)
		place(model, model.cursor.line, line_length(model, model.cursor.line), true)
		return "changed"
	end
	if plain and name == "home" then
		counted(model)
		place(model, model.cursor.line, 1, true)
		return "changed"
	end
	if plain and (name == "{" or name == "}") then
		local total = #model.lines
		local n = counted(model)
		local step = if name == "{" then -1 else 1
		local line = model.cursor.line
		local hits = 0
		while hits < n and line + step >= 1 and line + step <= total do
			line += step
			if blank(model.lines[line].text) then
				hits += 1
			end
		end
		return vertical(model, line)
	end
	if plain and (name == "page_down" or name == "page_up") then
		local rows = math.max(model.rows, 1)
		return scroll(model, if name == "page_down" then rows else -rows)
	end
	if key.ctrl and not key.alt and not key.meta and (name == "f" or name == "b" or name == "d" or name == "u") then
		local rows = math.max(model.rows, 1)
		local delta = if name == "f" or name == "b" then rows else math.max(rows // 2, 1)
		return scroll(model, if name == "f" or name == "d" then delta else -delta)
	end
	if plain and (name == "w" or name == "W" or name == "b" or name == "B" or name == "e" or name == "E") then
		local kind, big = word_kind(name, key.shift)
		if kind == "" then
			return unsupported(model)
		end
		local n = counted(model)
		local entry = model.lines[model.cursor.line]
		local text = entry.text
		local len = length(text)
		local column = model.cursor.column
		local step: (string, number, number, boolean) -> number = if kind == "w" then word_forward elseif kind == "b" then word_back else word_end
		for _ = 1, n do
			local next_column = step(text, len, column, big)
			if next_column == column then
				break
			end
			column = next_column
		end
		place(model, model.cursor.line, column, true)
		return "changed"
	end
	if plain and name == "g" and not key.shift then
		local n = counted(model)
		local total = #model.lines
		return vertical(model, if n > 1 then math.min(n, total) else 1)
	end
	if plain and (name == "G" or (name == "g" and key.shift)) then
		local total = #model.lines
		local given = model.count ~= ""
		local n = counted(model)
		return vertical(model, if given then math.min(n, total) else total)
	end
	if plain and name == "/" then
		counted(model)
		model.searching = true
		model.searchDirection = 1
		model.searchDraft = ""
		model.searchOrigin = { line = model.cursor.line, column = model.cursor.column }
		model.message = ""
		return "changed"
	end
	if plain and name == "?" then
		counted(model)
		model.searching = true
		model.searchDirection = -1
		model.searchDraft = ""
		model.searchOrigin = { line = model.cursor.line, column = model.cursor.column }
		model.message = ""
		return "changed"
	end
	if plain and name == "n" then
		counted(model)
		return repeat_search(model, model.searchDirection)
	end
	if plain and (name == "N" or (name == "n" and key.shift)) then
		counted(model)
		return repeat_search(model, -model.searchDirection)
	end
	return unsupported(model)
end

local function key(model: Model, key: Key): Result
	if model.status ~= "ready" then
		if key.name == "escape" or (key.name == "q" and not key.ctrl and not key.alt and not key.meta) then
			return "quit"
		end
		return unsupported(model)
	end
	if model.searching then
		return search_key(model, key)
	end
	return motion_key(model, key)
end

local function new(): Model
	return {
		lines = {},
		cursor = { line = 1, column = 1 },
		anchor = nil,
		linewise = false,
		top = 1,
		left = 1,
		cols = 0,
		rows = 0,
		preferred = 1,
		query = "",
		searching = false,
		searchDirection = 1,
		searchOrigin = nil,
		searchDraft = "",
		count = "",
		status = "loading",
		message = "",
	}
end

local function load(model: Model, lines: { Line })
	model.lines = lines
	local total = #lines
	if total == 0 then
		return
	end
	model.cursor.line = total
	model.cursor.column = 1
	model.preferred = 1
	model.anchor = nil
	model.top = math.max(1, total - math.max(model.rows, 1) + 1)
	viewport(model)
end

local function resize(model: Model, cols: number, rows: number)
	model.cols = cols
	model.rows = rows
	viewport(model)
end

return {
	new = new,
	load = load,
	resize = resize,
	key = key,
	selection = selection,
	selected = selected,
	length = length,
	byte = byte,
	width = width,
}
