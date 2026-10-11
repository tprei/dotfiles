--!strict

local types = require("./model")

type Model = types.Model
type Pane = types.Pane

type PickerItem = {
	id: string,
	label: string,
	mono: boolean,
	icon: string,
	tone: string,
	chips: { { text: string, dot: string } },
	badges: { { text: string, tone: string } },
	hits: { { number } },
	title: string,
}

local ui = tern.ui

local KINDS: { [string]: { icon: string, tone: string } } = {
	word = { icon = "type", tone = "accent" },
	path = { icon = "folder", tone = "info" },
	url = { icon = "link", tone = "success" },
	quote = { icon = "message", tone = "warning" },
	["s-quote"] = { icon = "message", tone = "warning" },
	line = { icon = "align-left", tone = "pending" },
}

local function utf16_offsets(text: string): { number }
	local offsets = { 0 }
	local units = 0
	for _, codepoint in utf8.codes(text) do
		units += if codepoint > 0xFFFF then 2 else 1
		table.insert(offsets, units)
	end
	return offsets
end

local function pane_color(pane: Pane): string
	local program = string.lower(pane.program)
	if string.find(program, "git", 1, true) then
		return "syntaxNumber"
	elseif
		string.find(program, "omp", 1, true)
		or string.find(program, "claude", 1, true)
		or string.find(program, "codex", 1, true)
	then
		return "syntaxKeyword"
	elseif
		string.find(program, "node", 1, true)
		or string.find(program, "python", 1, true)
		or string.find(program, "log", 1, true)
	then
		return "syntaxType"
	end
	return "syntaxString"
end

local function pane_label(pane: Pane): string
	return pane.title .. " · " .. tostring(pane.id)
end

local function workspace(panes: { Pane }): Node
	local cards: { Node } = {}
	for _, pane in panes do
		local lines: { string } = {}
		for index = math.max(1, #pane.lines - 7), #pane.lines do
			table.insert(lines, pane.lines[index])
		end
		local heading: { Span | string } =
			{ ui.span(pane_label(pane), "strong"), ui.span("  " .. pane.program, "muted") }
		if pane.origin then
			table.insert(heading, ui.span("  Paste target", "accent"))
		end
		table.insert(
			cards,
			ui.node("card", {
				key = tostring(pane.id),
				role = "extrakto.source",
				head = heading,
			}, {
				ui.node("text", { role = "extrakto.capture", text = table.concat(lines, "\n") }),
			})
		)
	end
	return ui.node("col", { role = "extrakto.workspace" }, {
		ui.node("col", { role = "extrakto.sources" }, cards),
	})
end

local function render(model: Model): BlockView
	local sources: { [number]: { pane: Pane, label: string, color: string } } = {}
	local target: string? = nil
	for _, pane in model.panes do
		local label = pane_label(pane)
		sources[pane.id] = { pane = pane, label = label, color = pane_color(pane) }
		if pane.origin then
			target = label
		end
	end
	local items: { PickerItem } = {}
	for _, match in model.matches do
		local candidate = match.candidate
		local source = sources[candidate.pane]
		local pane = source.pane
		local kind = KINDS[candidate.kind]
		local icon = "tag"
		local tone = "info"
		if kind then
			icon = kind.icon
			tone = kind.tone
		end
		local hits: { { number } } = {}
		if #match.hits > 0 then
			local offsets = utf16_offsets(candidate.text)
			for _, hit in match.hits do
				table.insert(hits, { offsets[hit[1] + 1], offsets[hit[2] + 1] })
			end
		end
		local badges: { { text: string, tone: string } } = {}
		if pane.origin then
			table.insert(badges, { text = "target", tone = "accent" })
		end
		table.insert(items, {
			id = candidate.id,
			label = candidate.text,
			mono = true,
			icon = icon,
			tone = tone,
			chips = { { text = source.label, dot = source.color } },
			badges = badges,
			hits = hits,
			title = source.label
				.. " · "
				.. pane.program
				.. " · line "
				.. tostring(candidate.line)
				.. "\n"
				.. candidate.source,
		})
	end
	local current: { string } = {}
	for id, marked in model.marked do
		if marked then
			table.insert(current, id)
		end
	end
	table.sort(current)
	local count = #current
	local disabled = model.searching or model.status ~= "ready" or (count == 0 and model.selected == nil)
	local paste_label = if count > 0 then "Paste " .. tostring(count) else "Paste"
	local subtitle = if target then "Into " .. target else "From the current tab"
	local query_offsets = utf16_offsets(model.query)
	return {
		main = workspace(model.panes),
		layer = ui.col({
			ui.node("picker", {
				key = "extract",
				role = "extrakto.picker",
				size = "md",
				layout = "rows",
				preview = "none",
				title = "Extract",
				subtitle = subtitle,
				icon = "search",
				noun = "captured items",
				placeholder = "Search captured text…",
				query = model.query,
				cursor = query_offsets[model.cursor + 1],
				state = model.status,
				message = model.message,
				empty = "No captured text in this scope",
				items = items,
				selected = model.selected,
				current = current,
				total = model.total,
				tabs = {
					{ id = "word", label = "Words" },
					{ id = "all", label = "Paths, URLs & quotes" },
					{ id = "line", label = "Lines" },
				},
				tab = model.filter,
				scopes = {
					{ id = "tab", label = "Whole tab", icon = "tabs-h" },
					{ id = "pane", label = "Origin pane", icon = "terminal" },
					{ id = "screen", label = "Visible screen", icon = "monitor" },
				},
				scope = model.scope,
				actions = {
					{ id = "close", label = "Close", keys = { "esc" } },
					{ id = "edit", label = "Edit", keys = { "ctrl", "e" }, disabled = disabled },
					{
						id = "copy",
						label = if count > 0 then "Copy " .. tostring(count) else "Copy",
						keys = { "enter" },
						disabled = disabled,
					},
					{
						id = "mark",
						label = if count > 0 then tostring(count) .. " marked" else "Mark",
						keys = if model.selected then { "shift", "tab" } else {},
						on = count > 0,
						disabled = model.searching or model.status ~= "ready" or model.selected == nil,
					},
					{
						id = "paste",
						label = paste_label,
						keys = if disabled then {} else { "tab" },
						primary = true,
						disabled = disabled,
					},
				},
			}),
		}),
	}
end

return { render = render }
