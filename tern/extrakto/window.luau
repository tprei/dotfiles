--!strict

local pickers: { [number]: boolean } = {}

tern.command({
	id = "open",
	title = "Extract text from this tab",
	run = function(cx)
		local origin = cx.session:focused()
		if origin == nil or pickers[origin] then
			return
		end
		local pane = cx.session:pane(origin)
		if pane == nil or (pane.kind ~= "terminal" and pane.kind ~= "agent") then
			cx:toast("error", "Extrakto starts from a terminal pane")
			return
		end
		if pane.floating == true then
			cx:toast("error", "Extrakto can't split a picture in picture", "Dock it first")
			return
		end
		local picker = cx.layout:split(origin, "down", { command = 'PATH="$HOME/.local/bin:$PATH" tern-extrakto' })
		if picker == nil then
			cx:toast("error", "Extrakto couldn't open its picker")
			return
		end
		pickers[picker] = true
		cx:action("zoom")
	end,
})

tern.on("pane_closed", function(ev, _cx)
	pickers[ev.pane] = nil
end)
