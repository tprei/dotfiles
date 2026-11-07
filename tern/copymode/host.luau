--!strict

local engine = require("./engine")
local types = require("./model")
local renderer = require("./view")

type Line = types.Line
type Model = types.Model

type State = {
	model: Model,
	origin: number?,
	snapshot: string?,
	raw: string?,
	pos: number,
	carry: string,
	parsed: { Line },
	closed: boolean,
}

local CLOSE_URL = "copymode://close"
local PARK_URL = "copymode://park"
local CAPTURE_TIMEOUT_MS = 60000
local PARSE_LINES_PER_TICK = 4000
local PARSE_BYTES_PER_TICK = 1024 * 1024
local SWEEP_INTERVAL_MS = 5000
local SNAPSHOT_PATTERN = "^copymode%-snapshot%-%d+%-%d+%-%d+%.ansi$"

local running: { [number]: State } = {}
local serial = 0
local sweeper_armed = false

local function shell(): string
	return tern.getenv("SHELL") or "/bin/sh"
end

local function trim(text: string): string
	text = string.gsub(text, "^%s+", "")
	return string.gsub(text, "%s+$", "")
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

local function remove_snapshot(path: string?)
	if path == nil or path == "" then
		return
	end
	local ok, err = pcall(function()
		if tern.fs.exists(path) then
			tern.fs.remove(path)
		end
	end)
	if not ok then
		tern.log.warn("copymode: cannot remove " .. path .. ": " .. trim(tostring(err)))
	end
end

local function failure_message(result: ProcessResult, action: string): string
	if result.timed_out then
		return action .. " timed out after " .. tostring(CAPTURE_TIMEOUT_MS // 1000) .. " s"
	end
	local reason = trim(result.stderr)
	if reason ~= "" then
		return action .. ": " .. reason
	end
	return action .. " failed with exit " .. tostring(result.status)
end

local function sweep()
	local live_panes: { [number]: boolean } = {}
	for _, info in tern.pane.list() do
		live_panes[info.pane] = true
	end
	for pane, state in running do
		if not live_panes[pane] then
			state.closed = true
			remove_snapshot(state.snapshot)
			running[pane] = nil
		end
	end
	local active_files: { [string]: boolean } = {}
	for _, state in running do
		if not state.closed and state.snapshot ~= nil then
			active_files[state.snapshot] = true
		end
	end
	local ok, entries = pcall(function(): { string }
		if not tern.fs.exists(tern.plugin.data) then
			return {}
		end
		return tern.fs.list(tern.plugin.data)
	end)
	if not ok then
		tern.log.warn("copymode: cannot list " .. tern.plugin.data .. ": " .. trim(tostring(entries)))
		return
	end
	for _, name in entries do
		if string.match(name, SNAPSHOT_PATTERN) ~= nil then
			local full_path = tern.plugin.data .. "/" .. name
			if not active_files[full_path] then
				local pane_id = tonumber(string.match(name, "^copymode%-snapshot%-(%d+)%-"))
				if pane_id == nil or not live_panes[pane_id] then
					remove_snapshot(full_path)
				end
			end
		end
	end
end

local function arm_sweeper()
	if sweeper_armed then
		return
	end
	sweeper_armed = true
	local function beat()
		if next(running) == nil then
			sweeper_armed = false
			return
		end
		sweep()
		tern.timer(SWEEP_INTERVAL_MS, beat)
	end
	tern.timer(SWEEP_INTERVAL_MS, beat)
end

local function is_blank(text: string): boolean
	return string.match(text, "^%s*$") ~= nil
end

local function trim_padding(lines: { Line }): { Line }
	local last = #lines
	while last > 0 and is_blank(lines[last].text) do
		last -= 1
	end
	if last == #lines then
		return lines
	end
	local trimmed: { Line } = {}
	for index = 1, last do
		trimmed[index] = lines[index]
	end
	return trimmed
end

local function parse_batch(state: State): (number, boolean)
	local raw = state.raw
	if raw == nil then
		return 0, true
	end
	local total = #raw
	local pos = state.pos
	local carry = state.carry
	local parsed = 0
	local consumed = 0
	while parsed < PARSE_LINES_PER_TICK and pos <= total do
		local nl = string.find(raw, "\n", pos, true)
		local finish = if nl ~= nil then nl - 1 else total
		local line_end = if nl ~= nil then nl + 1 else total + 1
		if parsed > 0 and consumed + (line_end - pos) > PARSE_BYTES_PER_TICK then
			break
		end
		local text_parts: { string } = {}
		local ansi_parts: { string } = {}
		if carry ~= "" then
			table.insert(ansi_parts, carry)
		end
		local i = pos
		local column = 0
		while i <= finish do
			local b = string.byte(raw, i)
			if b == 27 then
				local kind = string.byte(raw, i + 1)
				if kind == nil then
					i = finish + 1
				elseif kind == 91 then
					local j = i + 2
					while j <= finish do
						local c = string.byte(raw, j)
						if c >= 0x40 and c <= 0x7e then
							break
						end
						j += 1
					end
					if j <= finish then
						local final = string.byte(raw, j)
						if final == 109 then
							local seq = string.sub(raw, i, j)
							table.insert(ansi_parts, seq)
							if seq == "\27[0m" or seq == "\27[m" then
								carry = seq
							else
								carry ..= seq
							end
						end
						i = j + 1
					else
						i = finish + 1
					end
				elseif kind == 93 or kind == 80 or kind == 88 or kind == 94 or kind == 95 then
					local j = i + 2
					local stop: number? = nil
					while j <= finish do
						local c = string.byte(raw, j)
						if c == 7 then
							stop = j
							break
						end
						if c == 27 and string.byte(raw, j + 1) == 92 then
							stop = j + 1
							break
						end
						j += 1
					end
					i = if stop ~= nil then stop + 1 else finish + 1
				elseif kind == 40 or kind == 41 or kind == 42 or kind == 43 or kind == 45 or kind == 46 or kind == 47 then
					i += 3
				else
					i += 2
				end
			elseif b == 9 then
				local stop = (column // 8 + 1) * 8
				local gap = string.rep(" ", stop - column)
				table.insert(text_parts, gap)
				table.insert(ansi_parts, gap)
				column = stop
				i += 1
			elseif b < 32 or b == 127 then
				i += 1
			else
				local start = i
				i += 1
				while i <= finish do
					local c = string.byte(raw, i)
					if c >= 0x80 and c < 0xc0 then
						i += 1
					else
						break
					end
				end
				local chunk = string.sub(raw, start, i - 1)
				table.insert(text_parts, chunk)
				table.insert(ansi_parts, chunk)
				column += engine.width(utf8.codepoint(chunk, 1, 1))
			end
		end
		state.parsed[#state.parsed + 1] = {
			text = table.concat(text_parts),
			ansi = table.concat(ansi_parts),
		}
		parsed += 1
		consumed += line_end - pos
		pos = line_end
	end
	state.pos = pos
	state.carry = carry
	local done = pos > total
	if done then
		state.raw = nil
	end
	return parsed, done
end

local function finish_load(state: State, cx: BlockCx)
	local lines = trim_padding(state.parsed)
	state.parsed = {}
	if #lines == 0 then
		remove_snapshot(state.snapshot)
		state.snapshot = nil
		state.model.status = "error"
		state.model.message = "Copy mode captured no content from this pane"
		cx:render()
		return
	end
	engine.load(state.model, lines)
	state.model.status = "ready"
	state.model.message = ""
	cx:render()
	sweep()
end

local function load_snapshot(state: State, cx: BlockCx, path: string)
	local ok, raw = pcall(function()
		return tern.fs.read(path)
	end)
	if not ok or type(raw) ~= "string" then
		state.model.status = "error"
		state.model.message = "Copy mode couldn't read its snapshot: " .. trim(tostring(raw))
		cx:render()
		return
	end
	state.raw = raw
	state.pos = 1
	state.carry = ""
	local function tick()
		if gone(state, cx.pane) then
			remove_snapshot(state.snapshot)
			return
		end
		local _, done = parse_batch(state)
		if not done then
			tern.timer(0, tick)
			return
		end
		finish_load(state, cx)
	end
	tern.timer(0, tick)
end

local function start_capture(state: State, cx: BlockCx, origin: number)
	if not tern.fs.exists(tern.plugin.data) then
		tern.fs.mkdir(tern.plugin.data)
	end
	local path = tern.plugin.data
		.. "/copymode-snapshot-"
		.. tostring(cx.pane)
		.. "-"
		.. tostring(math.floor(tern.now()))
		.. "-"
		.. tostring(serial)
		.. ".ansi"
	state.snapshot = path
	local argv = {
		shell(),
		"-lc",
		'PATH="$HOME/.local/bin:$PATH"; exec python3 "$1" --origin "$2" --output "$3" --copy "$4"',
		"_",
		tern.plugin.dir .. "/capture.py",
		tostring(origin),
		path,
		tostring(cx.pane),
	}
	local ok, err = pcall(function()
		tern.process.run(argv, { timeout_ms = CAPTURE_TIMEOUT_MS }, function(result: ProcessResult)
			if gone(state, cx.pane) then
				remove_snapshot(state.snapshot)
				return
			end
			if result.status ~= 0 then
				remove_snapshot(state.snapshot)
				state.model.status = "error"
				state.model.message = failure_message(result, "Capture")
				cx:render()
				return
			end
			load_snapshot(state, cx, path)
		end)
	end)
	if not ok then
		remove_snapshot(state.snapshot)
		state.model.status = "error"
		state.model.message = trim(tostring(err))
		cx:render()
	end
end

local function request_close(state: State, cx: BlockCx)
	state.closed = true
	remove_snapshot(state.snapshot)
	state.snapshot = nil
	cx:open(CLOSE_URL)
end

local function find_origin(state: State, cx: BlockCx)
	local argv = {
		shell(),
		"-lc",
		'PATH="$HOME/.local/bin:$PATH"; exec python3 "$1" --origin-of "$2"',
		"_",
		tern.plugin.dir .. "/capture.py",
		tostring(cx.pane),
	}
	local ok, err = pcall(function()
		tern.process.run(argv, { timeout_ms = CAPTURE_TIMEOUT_MS }, function(result: ProcessResult)
			if gone(state, cx.pane) then
				return
			end
			if result.status ~= 0 then
				state.model.status = "error"
				state.model.message = failure_message(result, "Finding the pane to capture")
				cx:render()
				return
			end
			local origin = tonumber(string.match(result.stdout, "(%d+)%s*$") or "")
			if origin == nil or origin <= 0 then
				state.model.status = "error"
				state.model.message = "Copy mode couldn't tell which pane to capture"
				cx:render()
				return
			end
			state.origin = origin
			cx:save()
			cx:open(PARK_URL)
			start_capture(state, cx, origin)
		end)
	end)
	if not ok then
		state.model.status = "error"
		state.model.message = trim(tostring(err))
		cx:render()
	end
end

local copy: BlockDef<State> = {
	init = function(cx: BlockCx, _args: { string }, saved: any): State
		serial += 1
		local previous = running[cx.pane]
		if previous ~= nil then
			previous.closed = true
			remove_snapshot(previous.snapshot)
		end
		local model = engine.new()
		engine.resize(model, cx.cols, math.max(1, cx.rows - 2))
		local state: State = {
			model = model,
			origin = nil,
			snapshot = nil,
			raw = nil,
			pos = 1,
			carry = "",
			parsed = {},
			closed = false,
		}
		running[cx.pane] = state
		arm_sweeper()

		local origin_id: number? = nil
		local restore_path: string? = nil
		if type(saved) == "table" then
			if type(saved.origin) == "number" and saved.origin > 0 then
				origin_id = saved.origin
			end
			if type(saved.path) == "string" and tern.fs.exists(saved.path) then
				restore_path = saved.path
			end
		end
		if restore_path ~= nil then
			state.origin = origin_id
			state.snapshot = restore_path
		elseif origin_id ~= nil then
			state.origin = origin_id
		end

		tern.timer(0, function()
			if gone(state, cx.pane) then
				remove_snapshot(state.snapshot)
				return
			end
			sweep()
			if gone(state, cx.pane) then
				remove_snapshot(state.snapshot)
				return
			end
			if state.snapshot ~= nil then
				load_snapshot(state, cx, state.snapshot)
			elseif state.origin ~= nil then
				start_capture(state, cx, state.origin)
			else
				find_origin(state, cx)
			end
		end)
		return state
	end,
	view = function(state: State, _cx: BlockCx): BlockView
		return renderer.render(state.model)
	end,
	resize = function(state: State, cols: number, rows: number, _cx: BlockCx)
		engine.resize(state.model, cols, math.max(1, rows - 2))
	end,
	key = function(state: State, key: Key, cx: BlockCx): boolean?
		if state.closed then
			return false
		end
		local model = state.model
		if model.status ~= "ready" then
			if key.name == "q" or key.name == "escape" then
				request_close(state, cx)
			end
			return false
		end
		local result = engine.key(model, key)
		if result == "copy" then
			local text = engine.selection(model)
			if text ~= nil then
				cx:copy(text)
			end
			request_close(state, cx)
			return false
		end
		if result == "quit" then
			request_close(state, cx)
			return false
		end
		return result == "changed"
	end,
	save = function(state: State): any
		if state.origin == nil then
			return nil
		end
		if state.model.status == "ready" and state.snapshot ~= nil then
			return { origin = state.origin, path = state.snapshot }
		end
		return { origin = state.origin }
	end,
}

tern.block.define("copy", copy)
