# Keybindings Reference

## Navigation & Window Management

| Keybinding | Mode | Action |
|-----------|------|--------|
| `<C-h>` | Normal | Move focus to left window |
| `<C-l>` | Normal | Move focus to right window |
| `<C-j>` | Normal | Move focus to lower window |
| `<C-k>` | Normal | Move focus to upper window |

## Insert Mode

| Keybinding | Mode | Action |
|-----------|------|--------|
| `jk` | Insert | Exit insert mode |
| `<Esc>` | Normal | Clear highlight search |

## Telescope (Fuzzy Finder)

| Keybinding | Mode | Action |
|-----------|------|--------|
| `<leader>sh` | Normal | Search Help tags |
| `<leader>sk` | Normal | Search Keymaps |
| `<leader>sf` | Normal | Search Files |
| `<leader>ss` | Normal | Search Select (all Telescope builtins) |
| `<leader>sw` | Normal/Visual | Search current Word |
| `<leader>sg` | Normal | Search by Grep |
| `<leader>sd` | Normal | Search Diagnostics |
| `<leader>sr` | Normal | Search Resume (last search) |
| `<leader>s.` | Normal | Search Recent Files |
| `<leader>sc` | Normal | Search Commands |
| `<leader><leader>` | Normal | Find existing Buffers |
| `<leader>sn` | Normal | Search Neovim config files |

## LSP (Language Server Protocol)

### Goto commands (when LSP is attached):

| Keybinding | Mode | Action |
|-----------|------|--------|
| `grd` | Normal | Goto Definition |
| `gri` | Normal | Goto Implementation |
| `grr` | Normal | Goto References |
| `grt` | Normal | Goto Type Definition |
| `gO` | Normal | Open Document Symbols |
| `gW` | Normal | Open Workspace Symbols |

## Other

| Keybinding | Mode | Action |
|-----------|------|--------|
| `<leader>q` | Normal | Open diagnostic Quickfix list |
| `<leader>/` | Normal | Fuzzy search within current buffer |
| `<Esc><Esc>` | Terminal | Exit terminal mode |

## Notes

- `<leader>` is space by default in this config
- Capital letters in descriptions show which part the key maps to (`[S]earch [F]iles` → `<leader>sf`)
- Many Telescope keybindings share the `<leader>s` prefix for "search"
