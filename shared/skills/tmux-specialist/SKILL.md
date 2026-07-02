---
name: tmux-specialist
description: Quick tmux reference. Use when the user asks about tmux commands, keybindings, sessions, panes, windows, or configuration.
---

# tmux Specialist

Quick reference for tmux commands, keybindings, and workflows.

## When to use

Invoke this skill when the user asks about:
- tmux keybindings (e.g., "how do I split panes?")
- session management (create, attach, detach, kill)
- window and pane operations
- copy mode and buffer commands
- configuration options

## Reference files

| File | Contents |
|------|----------|
| `references/cheatsheet.md` | **Start here** — quick reference tables for all commands. |
| `references/Getting-Started.md` | Comprehensive tmux introduction and concepts. |
| `references/Advanced-Use.md` | Advanced configuration and scripting. |
| `references/FAQ.md` | Common issues and solutions. |
| `references/Clipboard.md` | Clipboard integration. |
| `references/Formats.md` | Format strings and variables. |
| `references/tmux.conf` | The user's personal tmux configuration (symlinked to dotfiles). |

## Quick reference

### Prefix
All tmux shortcuts use `Ctrl+b` as the prefix key.

### Most common operations

| Action | Shortcut |
|--------|----------|
| Split horizontal | `Ctrl+b "` |
| Split vertical | `Ctrl+b %` |
| New window | `Ctrl+b c` |
| Next window | `Ctrl+b n` |
| Detach | `Ctrl+b d` |
| List sessions | `Ctrl+b s` |
| Enter copy mode | `Ctrl+b [` |
| Paste | `Ctrl+b ]` |

### Session commands

```bash
tmux new -s name          # Create named session
tmux attach -t name       # Attach to session
tmux ls                   # List sessions
tmux kill-session -t name # Kill session
```

## How to use

1. Check `references/cheatsheet.md` for quick lookups.
2. Check `references/Getting-Started.md` for detailed explanations.
3. Check `references/FAQ.md` for troubleshooting.
