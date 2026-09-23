---
name: tmux-specialist
description: Quick tmux reference. Use when the user asks about tmux commands, keybindings, sessions, panes, windows, or configuration.
---

# tmux specialist

Answer tmux questions: keybindings, sessions, windows, panes, copy mode, and config.

The user's config is `references/tmux.conf` (symlinked to the dotfiles `tmux/.tmux.conf`); check it first, because it overrides defaults. Prefix is `C-a`, not `C-b`.

User bindings:
| Action | Key |
|--------|-----|
| Split side by side / stacked | `prefix -` / `prefix =` |
| Next / previous window | `M-n` / `M-p` |
| Window 1-5 | `M-1`..`M-5` |
| Session chooser | `M-w` |
| Copy mode | `M-]` |
| Resize pane | `M-h/j/k/l` |
| Select pane (innermost, vim-aware) | `C-h/j/k/l` |
| Select pane (this session) | `prefix C-h/j/k` |
| Kill pane (confirm) | `M-x` |
| Break pane | `prefix b` |
| Open pane dir / paste clipboard image (WSL) | `M-e` / `M-v` |

Alt+Shift variants send the same binding one level into a nested tmux or herdr.

Upstream docs live in `references/files.md`, a Repomix pack of the tmux wiki. Search it by `## File: <name>`: `cheatsheet.md` first, then `Getting-Started.md`, `Advanced-Use.md`, `FAQ.md`, `Clipboard.md`, `Formats.md`.

```bash
tmux new -s name          # create named session
tmux attach -t name       # attach
tmux ls                   # list
tmux kill-session -t name # kill
```
