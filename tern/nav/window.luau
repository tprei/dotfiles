--!strict

type Dir = "left" | "down" | "up" | "right"

local CONTROL_BYTES: { [Dir]: string } = {
	left = "\x08",
	down = "\x0a",
	up = "\x0b",
	right = "\x0c",
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
	if pane ~= nil and owns_navigation_keys(pane) then
		cx:run(pane.pane, CONTROL_BYTES[dir])
		return
	end
	cx:action("focus_pane:" .. dir)
end

local function step_session(cx: WindowCx, delta: number)
	local sessions = cx.sessions:list()
	local current = cx.sessions:current().id
	for i, session in sessions do
		if session.id == current then
			cx.sessions:switch(sessions[(i - 1 + delta) % #sessions + 1].id)
			return
		end
	end
end

local DIRS: { Dir } = { "left", "down", "up", "right" }

for _, dir in DIRS do
	tern.command({
		id = dir,
		title = "Focus pane " .. dir .. ", or pass the key to vim",
		run = function(cx)
			navigate(cx, dir)
		end,
	})
end

tern.command({
	id = "next_session",
	title = "Next session",
	run = function(cx)
		step_session(cx, 1)
	end,
})

tern.command({
	id = "previous_session",
	title = "Previous session",
	run = function(cx)
		step_session(cx, -1)
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
