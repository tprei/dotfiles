--!strict

local PICKER_BLOCK = "extrakto.picker"

local function forward_picker_key(cx: WindowCx, action: string): boolean
	local pane = cx.session:pane("@focused")
	if pane == nil or pane.block ~= PICKER_BLOCK then
		return false
	end
	cx:action(action)
	return true
end

tern.override("move_pane:left", function(cx)
	return forward_picker_key(cx, "text:\27[1;3D")
end)

tern.override("move_pane:right", function(cx)
	return forward_picker_key(cx, "text:\27[1;3C")
end)

tern.command({
	id = "open",
	title = "Extract text from this tab",
	run = function(cx)
		local origin = cx.session:focused()
		if origin == nil then
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
		local picker = cx.layout:split(origin, "down", { block = "extrakto.picker" })
		if picker == nil then
			cx:toast("error", "Extrakto couldn't open its picker")
			return
		end
		tern.timer(0, function(zcx)
			if zcx == nil or zcx.session:focused() ~= picker then
				return
			end
			local tab = zcx.session:tab_of(picker)
			if tab == nil then
				return
			end
			local tree = zcx.session:layout(tab)
			if tree == nil or tree.zoomed then
				return
			end
			zcx:action("zoom")
		end)
	end,
})
