# extrakto for Tern

`ctrl+a tab` opens this picker in a zoomed split under the focused pane; the split closes when you're done. Type a few characters to fuzzy-match an entry, `shift-tab` marks several, and `esc` or `ctrl-c` closes the picker.

## Filters (`ctrl-f`)

- `word`: words of at least five characters. This is the default.
- `all`: every filter marked `in_all` in `extrakto.conf`, including paths, URLs, and quotes, prefixed with the filter name.
- `line`: whole lines.

Add or override filters in `~/.config/extrakto/extrakto.conf`.

## Grab area (`ctrl-g`)

- `window full`: the last 2000 lines of every terminal pane in this tab, including picture-in-picture panes. This is the default.
- `recent`: the visible screen of the pane you started from.
- `window recent`: the same for every pane in this tab.
- `full`: the last 2000 lines of the pane you started from.

File panes aren't read.

## Actions

- `tab`: paste the selection into the pane you started from.
- `enter`: copy the selection over OSC 52.
- `ctrl-e`: run `$EDITOR -- <selection>` in the pane you started from.

Press `q` to return to the picker.
