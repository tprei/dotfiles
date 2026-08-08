-- starts a timer with some callbacks and returns immediately
--
-- these callbacks are on_stdout, on_stderr, on_exit
local function run(enriched_prompt, callbacks)
	local stdout_f = function(_, data)

		vim.schedule(function ()
			vim.notify(vim.inspect(data))
		end)
		callbacks.on_stdout(data)
	end

	local stderr_f = function(_, data)
		callbacks.on_stderr(data)
	end

	local exit_f = function(obj)
		callbacks.on_exit(obj.code)
	end

	vim.system({ "pi", enriched_prompt, "--provider", "zai", "--model", "glm-5-turbo", "-p", "--mode", "--json" }, { stdout = stdout_f, stderr = stderr_f, text = true }, exit_f)
end

return {
	run = run,
}
