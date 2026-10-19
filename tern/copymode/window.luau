--!strict

local ORIGIN_MODULO = 17592186044416
local CLOSE_URL = "copymode://close"
local COPY_BLOCK = "copymode.copy"
local RECORDS_KEY = "active"

export type Record = {
	origin: number,
	copy: number,
	tab: number,
}

local records: { [number]: Record } = {}
local dirty: { [number]: boolean } = {}
local last_focus: number? = nil

local function decode_records(value: any): { [number]: Record }
	local decoded: { [number]: Record } = {}
	if type(value) ~= "table" then
		return decoded
	end
	for _, entry in value do
		if
			type(entry) == "table"
			and type(entry.origin) == "number"
			and type(entry.copy) == "number"
			and type(entry.tab) == "number"
			and entry.origin > 0
			and entry.copy > 0
		then
			decoded[entry.copy] = {
				origin = entry.origin,
				copy = entry.copy,
				tab = entry.tab,
			}
		end
	end
	return decoded
end

local function persist()
	local ok, stored = pcall(function()
		return decode_records(tern.kv.get(RECORDS_KEY))
	end)
	if not ok or type(stored) ~= "table" then
		stored = {}
	end
	for copy in dirty do
		stored[copy] = records[copy]
	end
	table.clear(dirty)
	local merged: { Record } = {}
	for _, record in stored do
		merged[#merged + 1] = record
	end
	tern.kv.set(RECORDS_KEY, merged)
end

local function record_for_copy(copy: number): Record?
	return records[copy]
end

local function forget(record: Record)
	if records[record.copy] == record then
		records[record.copy] = nil
		dirty[record.copy] = true
		persist()
	end
end

local function pane_of(cx: WindowCx, pane: number): PaneInfo?
	for _, info in cx.session:panes() do
		if info.pane == pane then
			return info
		end
	end
	return nil
end

local function has_tab(cx: WindowCx, tab: number): boolean
	for _, info in cx.session:tabs() do
		if info.id == tab then
			return true
		end
	end
	return false
end

local function deal_back(cx: WindowCx, record: Record): boolean
	local info = pane_of(cx, record.origin)
	if info == nil then
		return false
	end
	if info.parked == true then
		cx.layout:unpark(record.origin, { focus = false })
		info = pane_of(cx, record.origin)
		if info == nil then
			return true
		end
		if info.parked == true then
			return false
		end
	end
	if info.tab ~= record.tab and has_tab(cx, record.tab) then
		cx.layout:move_to_tab(record.origin, record.tab, { focus = false })
	end
	return true
end

local function finish(cx: WindowCx, record: Record, focus_origin: boolean)
	forget(record)
	cx.layout:close(record.copy)
	if focus_origin then
		cx.layout:focus(record.origin)
	end
end

local function recover(cx: WindowCx, record: Record, refocus: boolean)
	if not deal_back(cx, record) then
		return
	end
	forget(record)
	if refocus and pane_of(cx, record.origin) ~= nil then
		cx.layout:focus(record.origin)
	end
end

local function recover_orphans(cx: WindowCx, previous: number?)
	for _, record in records do
		if pane_of(cx, record.copy) == nil then
			recover(cx, record, previous == record.copy)
		end
	end
end

local function restore(cx: WindowCx, record: Record)
	local info = pane_of(cx, record.origin)
	if info ~= nil and info.parked == true then
		local ok, why = cx.layout:unpark(record.origin, { focus = false })
		info = pane_of(cx, record.origin)
		if not ok and info ~= nil and info.parked == true then
			cx:toast("error", "Copy mode couldn't restore the pane", tostring(why))
			return
		end
	end
	if info == nil then
		cx:toast("error", "Copy mode's origin pane exited", "It can't be restored")
		finish(cx, record, false)
		return
	end
	if not cx.layout:move(record.origin, record.copy, "swap", { focus = false }) then
		cx:toast("error", "Copy mode couldn't put the pane back in place", "Close copy mode again to retry")
		return
	end
	finish(cx, record, true)
end

local function reconcile(cx: WindowCx)
	last_focus = cx.session:focused()
	recover_orphans(cx, nil)
end

tern.command({
	id = "open",
	title = "Browse this pane's scrollback in copy mode",
	run = function(cx)
		local origin = cx.session:focused()
		if origin == nil then
			return
		end
		local active = record_for_copy(origin)
		if active ~= nil then
			restore(cx, active)
			return
		end
		local pane = cx.session:pane(origin)
		if pane == nil then
			return
		end
		if pane.block == COPY_BLOCK then
			cx:toast("error", "Copy mode lost track of this block", "Close it and start again")
			return
		end
		if pane.kind ~= "terminal" and pane.kind ~= "agent" then
			cx:toast("error", "Copy mode starts from a terminal pane")
			return
		end
		if pane.floating == true then
			cx:toast("error", "Copy mode can't split a picture in picture", "Dock it first")
			return
		end
		for _, record in records do
			if record.origin == origin then
				if pane_of(cx, record.copy) ~= nil then
					cx:toast("error", "Copy mode is already open for this pane")
					return
				end
				forget(record)
			end
		end
		local tab = cx.session:tab_of(origin)
		local copy = cx.layout:split(origin, "down", {
			block = COPY_BLOCK,
			args = { tostring(origin % ORIGIN_MODULO) },
		})
		if copy == nil then
			cx:toast("error", "Copy mode couldn't open its block", "Is the plugin enabled on the pane's host?")
			return
		end
		if tab == nil then
			cx.layout:close(copy)
			return
		end
		local ok, why = cx.layout:park(origin)
		if not ok then
			cx.layout:close(copy)
			cx:toast("error", "Copy mode couldn't freeze the pane", tostring(why))
			return
		end
		records[copy] = {
			origin = origin,
			copy = copy,
			tab = tab,
		}
		dirty[copy] = true
		persist()
	end,
})

tern.command({
	id = "close",
	title = "Exit copy mode and restore the pane",
	run = function(cx)
		local focused = cx.session:focused()
		if focused == nil then
			return
		end
		local record = record_for_copy(focused)
		if record ~= nil then
			restore(cx, record)
		end
	end,
})

tern.override("close_pane", function(cx)
	local focused = cx.session:focused()
	if focused == nil then
		return nil
	end
	local record = record_for_copy(focused)
	if record == nil then
		return nil
	end
	restore(cx, record)
	return true
end)

tern.route.link(function(link, cx)
	if link.url ~= CLOSE_URL or link.pane == nil then
		return nil
	end
	local record = record_for_copy(link.pane)
	if record ~= nil then
		restore(cx, record)
		return { handled = true }
	end
	local pane = pane_of(cx, link.pane)
	if pane ~= nil and pane.block == COPY_BLOCK then
		cx.layout:close(link.pane)
		return { handled = true }
	end
	return nil
end)

tern.on("focus", function(ev, cx)
	local previous = last_focus
	last_focus = ev.pane
	recover_orphans(cx, previous)
end)

tern.on("pane_closed", function(ev, cx)
	local record = record_for_copy(ev.pane)
	if record ~= nil then
		recover(cx, record, last_focus == ev.pane)
	end
end)

tern.on("window_start", reconcile)

records = decode_records(tern.kv.get(RECORDS_KEY))
