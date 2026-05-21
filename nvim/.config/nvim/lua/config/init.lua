--
--[[
-- Globals / Options
--]]
-- show numbers, make them relative
vim.o.number = true
vim.o.relativenumber = true

-- theme
vim.o.background = "light"

-- Allow undoing/redoing even after closing a file
vim.o.undofile = true

-- Always render the sign column
-- This is useful not only if we have indicators like warnings, errors and so on
-- But also without it it nvim can feel "tight"
vim.o.signcolumn = 'yes'

-- Decrease update time. We're in 2026 goddami
vim.o.updatetime = 250

-- Time to perform a mapped action
-- I'm a newbie so I use 1k (which is also the default, but I put it here explicitly in case I want to get better at this and change it in the future
vim.o.timeoutlen = 1000

-- ignore case in search, unless there's a UPPERCASE LETTER IN IT
vim.o.ignorecase = true
vim.o.smartcase = true

-- always wrap really long lines, and keep indentation
vim.o.wrap = true
vim.o.breakindent = true

-- I set true to hlsearch (default) because I map ESC to clear it later
vim.o.hlsearch = true

-- I personally like 4 spaces for tab
-- also set shiftwidth to the same value, this way when we do >> it indents with the same space
vim.o.tabstop = 4
vim.o.softtabstop = 4
vim.o.shiftwidth = 4

-- keep tabs as \t and not spaces
vim.o.expandtab = false

-- Configure how new splits should be opened
-- Note: I don't use much cause I have tmux and I love tmux, but still keeping this just in case it's used by other plugins and so on
vim.o.splitright = true
vim.o.splitbelow = true

-- show characters like tab/ trailing spaces and so on
vim.o.list = true
vim.opt.listchars = { tab = '» ', trail = '·', nbsp = '␣' }

-- Preview substitutions live, as you type!
vim.o.inccommand = 'split'

-- Show which line your cursor is on
-- I like it cause sometimes there might be some contrast / visibility issues
vim.o.cursorline = true

-- Minimal number of screen lines to keep above and below the cursor.
vim.o.scrolloff = 10

-- if performing an operation that would fail due to unsaved changes in the buffer (like `:q`),
-- instead raise a dialog asking if you wish to save the current file(s)
-- See `:help 'confirm'`
vim.o.confirm = true

-- [[
-- Clipboard
-- ]]
--
-- schedules after UiEnter to use + register as the clipboard -- this is to sync such that we can yank into the OS clipboard
vim.schedule(function() vim.o.clipboard = 'unnamedplus' end)

-- [[
-- Diagnostic
-- ]]
--
vim.diagnostic.config {
	-- already default but making explicit -- don't update the diagnostics window in insert mode
	update_in_insert = false,

	-- sort by severity, higher comes first
	severity_sort = true,

	-- shows the error message at the end of the line
	virtual_text = true,

	--  rounded border, and show sources
	float = { border = 'rounded', source = 'if_many' },

	-- only underline errors
	underline = { severity = { min = vim.diagnostic.severity.ERROR } },

	-- Default options for jumping with [d and ]d
	-- Auto open the float on jump, so you can easily read the errors
	jump = { float = true },
}



-- [[
-- Autocommands
-- ]]
--
-- Highlight when yanking
vim.api.nvim_create_autocmd('TextYankPost', {
	desc = 'Highlights on yanking',
	group = 'dotfiles',
	callback = function()
		vim.hl.on_yank()
	end
})

-- Adds basic LSP actions
vim.api.nvim_create_autocmd('LspAttach', {
	-- reason we don't create on opening a buffer and instead use attach is that these functions
	-- wouldnt be available
	desc = "Defines LSP keymaps whenever LSP attaches to the buffer",
	group = "dotfiles",
	callback = function(args)
		local map = function(keys, func, desc)
			vim.keymap.set("n", keys, func, {
				buffer = args.buf,
				desc = "LSP: " .. desc,
			})
		end

		map("<leader> ", vim.lsp.buf.code_action, "Code action")
		map("gd", vim.lsp.buf.definition, "[G]o to [d]efinition")
		map("gr", vim.lsp.buf.references, "[G]o to [r]eference")
		map("gi", vim.lsp.buf.implementation, "[G]o to [i]mplementation")
		map("<leader>rn", vim.lsp.buf.rename, "[r]e[n]ame")
		map("K", vim.lsp.buf.hover, "Hover documentation")
	end
})
