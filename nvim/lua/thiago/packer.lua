-- This file can be loaded by calling `lua require('plugins')` from your init.vim
vim.cmd [[packadd packer.nvim]]

return require('packer').startup(function(use)
    -- Packer can manage itself
    use('wbthomason/packer.nvim')

    -- theme
    use { "catppuccin/nvim", as = "catppuccin" }

    -- telescope
    use {
        'nvim-telescope/telescope.nvim', tag = '0.1.0',
        -- or                            , branch = '0.1.x',
        requires = { {
            'nvim-lua/plenary.nvim',
            'nvim-lua/popup.nvim',
        } }
    }
    use('nvim-telescope/telescope-file-browser.nvim')
    use { 'nvim-telescope/telescope-fzf-native.nvim', run = 'make' }


    -- treesitter
    use('nvim-treesitter/nvim-treesitter', { run = ':TSUpdate' })
    use('tpope/vim-fugitive')
    use('mbbill/undotree')

    -- lsp
    use {
        'VonHeikemen/lsp-zero.nvim',
        requires = {
            -- LSP Support
            { 'neovim/nvim-lspconfig' },
            { 'williamboman/mason.nvim' },
            { 'williamboman/mason-lspconfig.nvim' },

            -- Autocompletion
            { 'hrsh7th/nvim-cmp' },
            { 'hrsh7th/cmp-buffer' },
            { 'hrsh7th/cmp-path' },
            { 'saadparwaiz1/cmp_luasnip' },
            { 'hrsh7th/cmp-nvim-lsp' },
            { 'hrsh7th/cmp-nvim-lua' },

            -- Snippets
            { 'L3MON4D3/LuaSnip' },
            { 'rafamadriz/friendly-snippets' },
        }
    }

    -- lualine (status bar)
    use {
        'nvim-lualine/lualine.nvim',
        requires = { 'kyazdani42/nvim-web-devicons', opt = true }
    }

    -- tree
    use {
        'nvim-tree/nvim-tree.lua',
        requires = {
            'nvim-tree/nvim-web-devicons', -- optional, for file icons
        },
        tag = 'nightly' -- optional, updated every week. (see issue #1193)
    }


    -- dev icons for tree plugin
    use('ryanoasis/vim-devicons')
    use('kyazdani42/nvim-web-devicons')
    use { 'akinsho/bufferline.nvim', tag = "v3.*", requires = 'nvim-tree/nvim-web-devicons' }

    -- lsp dianostics
    use {
        "folke/trouble.nvim",
        requires = "kyazdani42/nvim-web-devicons",
    }

    -- maximize with <leader>z
    use {
        'declancm/maximize.nvim',
        config = function() require('maximize').setup() end
    }

    -- session management
    use {
        'rmagatti/auto-session',
        config = function()
            require("auto-session").setup {
                log_level = "error",
                auto_session_suppress_dirs = { "~/", "~/Projects", "~/Downloads", "/" },
                save_extra_cmds = {
                    function()
                        local nvim_tree = require('nvim-tree')
                        nvim_tree.change_dir(vim.fn.getcwd())
                        nvim_tree.refresh()
                    end
                }
            }
        end
    }

    --null-ls
    use('jose-elias-alvarez/null-ls.nvim')
end)
