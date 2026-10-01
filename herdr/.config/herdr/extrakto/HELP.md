# extrakto for Herdr

`prefix+tab` opens this popup over the focused pane. Type a few characters to fuzzy-match an entry, `shift-tab` marks several, and `esc` or `ctrl-c` closes the popup.

## Filters (`ctrl-f`)

- `word`: words of at least five characters. This is the default.
- `all`: every filter marked `in_all` in `extrakto.conf`, including paths, URLs, and quotes, prefixed with the filter name.
- `line`: whole lines.

Add or override filters in `~/.config/extrakto/extrakto.conf`.

## Grab area (`ctrl-g`)

- `window full`: the last 2000 lines of every pane in this tab. This is the default.
- `recent`: the focused pane's visible screen plus 10 lines of history.
- `window recent`: the same for every pane in this tab.
- `full`: the last 2000 lines of the focused pane.

## Actions

- `tab`: type the selection into the focused pane.
- `enter`: copy the selection to the clipboard.
- `ctrl-o`: open the selection with `open` on macOS or `xdg-open` on Linux, from the pane's directory.
- `ctrl-e`: run `$EDITOR -- <selection>` in the focused pane.

Press `q` to return to the picker.
