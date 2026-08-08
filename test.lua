vim.system({ "bash", "-c", "for i in 1 2 3 4 5; do echo $i; sleep 1; done" }, {
	text = true,
	stdout = function(_, data)
		print("CHUNK [" .. data .. "]")
	end,
}, function(obj)
	print("EXIT: " .. obj.code)
end)
