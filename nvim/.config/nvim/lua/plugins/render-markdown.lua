return {
    {
        "MeanderingProgrammer/render-markdown.nvim",
        dependencies = {
            "nvim-treesitter/nvim-treesitter",
            "nvim-tree/nvim-web-devicons",
        },
        opts = {
            heading = {
                enabled = true,
                sign = false,
                icons = { "", "", "", "", "", "" },
                width = "block",
            },

            code = {
                sign = false,
                width = "block",
                border = "thin",
            },


            bullet = {
                enabled = true,
            },
        },
    },
}
