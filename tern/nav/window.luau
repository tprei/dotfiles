--!strict

type Dir = "left" | "down" | "up" | "right"

local CONTROL_BYTES: { [Dir]: string } = {
	left = "\x08",
	down = "\x0a",
	up = "\x0b",
	right = "\x0c",
}

local PICKER_ACTIONS: { [Dir]: string } = {
	left = "text:\27[D",
	down = "text:\27[B",
	up = "text:\27[A",
	right = "text:\27[C",
}

local KEY_OWNERS: { [string]: boolean } = {
	view = true,
	fzf = true,
	ssh = true,
	mosh = true,
	tmux = true,
	herdr = true,
}

local function owns_navigation_keys(pane: PaneInfo): boolean
	if pane.program == nil or pane.exited ~= nil then
		return false
	end
	local name = string.gsub(pane.program, "^.*/", "")
	return KEY_OWNERS[name] == true or string.match(name, "^l?n?vim?x?$") ~= nil
end

local function navigate(cx: WindowCx, dir: Dir)
	local pane = cx.session:pane("@focused")
	if pane ~= nil and pane.block == "extrakto.picker" then
		cx:action(PICKER_ACTIONS[dir])
		return
	end
	if pane ~= nil and owns_navigation_keys(pane) then
		cx:run(pane.pane, CONTROL_BYTES[dir])
		return
	end
	cx:action("focus_pane:" .. dir)
end

type Key = { rank: number, position: number }

local function session_ranks(cx: WindowCx): { [number]: number }
	local ranks: { [number]: number } = {}
	for index, session in cx.sessions:list() do
		ranks[session.id] = index
	end
	return ranks
end

type Row = { session: number, tab: number, position: number, pane: number }

local function sidebar_rows(cx: WindowCx, session_rank: { [number]: number }): { Row }
	local rows: { Row } = {}
	for _, tab in cx.session:tabs() do
		if session_rank[tab.session] ~= nil then
			table.insert(rows, { session = tab.session, tab = tab.id, position = tab.position, pane = tab.pane })
		end
	end
	table.sort(rows, function(a: Row, b: Row): boolean
		if a.session ~= b.session then
			return session_rank[a.session] < session_rank[b.session]
		end
		return a.position < b.position
	end)
	return rows
end

local function key_before(a: Key, b: Key): boolean
	if a.rank ~= b.rank then
		return a.rank < b.rank
	end
	return a.position < b.position
end

local function step_workspace(cx: WindowCx, delta: number)
	local session_rank = session_ranks(cx)
	local rows = sidebar_rows(cx, session_rank)
	if #rows == 0 then
		return
	end
	local anchor: Key = { rank = session_rank[cx.sessions:current().id] or 0, position = 0 }
	local focused = cx.session:focused()
	if focused ~= nil then
		local current_tab = cx.session:tab_of(focused)
		if current_tab ~= nil then
			for _, row in rows do
				if row.tab == current_tab then
					anchor = { rank = session_rank[row.session], position = row.position }
					break
				end
			end
		end
	end
	local target: Row? = nil
	if delta > 0 then
		for _, row in rows do
			if key_before(anchor, { rank = session_rank[row.session], position = row.position }) then
				target = row
				break
			end
		end
	else
		for index = #rows, 1, -1 do
			local row = rows[index]
			if key_before({ rank = session_rank[row.session], position = row.position }, anchor) then
				target = row
				break
			end
		end
	end
	local chosen: Row = target or rows[if delta > 0 then 1 else #rows]
	cx.layout:focus(chosen.pane)
end

local DIRS: { Dir } = { "left", "down", "up", "right" }

for index, dir in DIRS do
	tern.command({
		id = dir,
		title = "Focus pane " .. dir .. ", or pass the key to vim",
		run = function(cx)
			navigate(cx, DIRS[index])
		end,
	})
end

tern.command({
	id = "next_session",
	title = "Next workspace in the sidebar, skipping empty ones",
	run = function(cx)
		step_workspace(cx, 1)
	end,
})

tern.command({
	id = "previous_session",
	title = "Previous workspace in the sidebar, skipping empty ones",
	run = function(cx)
		step_workspace(cx, -1)
	end,
})

for n = 1, 9 do
	tern.command({
		id = "session_" .. n,
		title = "Switch to session " .. n,
		run = function(cx)
			local session = cx.sessions:list()[n]
			if session ~= nil then
				cx.sessions:switch(session.id)
			end
		end,
	})

	tern.command({
		id = "agent_" .. n,
		title = "Focus agent " .. n,
		run = function(cx)
			local agent = cx.agents:list()[n]
			if agent ~= nil then
				cx.layout:focus(agent.pane)
			end
		end,
	})
end
