# Raycast Hyper+F for the focused omp session

## Contract

Caps Lock held with F invokes Raycast's `Fork focused omp session` script command. The script asks Tern's native fork operation to fork the focused pane in the shown tab into a right-hand pane. Tern resolves its own omp session, preserves the source and its draft, and starts `omp --fork` for the child. Never select a session by modification time, process argv, or filename. Never type `/fork` into the composer.

The current workstation uses macOS, zsh, Tern 0.9.21, and one Tern window. Raycast's database is encrypted, and desktop Accessibility is disabled. Script registration and recording its hotkey require Raycast Settings unless another supported registration interface is discovered. Do not edit the encrypted database or claim the binding is installed without evidence.

## Files and slices

1. Add `raycast/scripts/omp-fork.py` and focused behavioral tests at `raycast/tests/test_omp_fork.py`. Like `tern/`, `raycast/` isn't a Stow package: Raycast reads the script directory from the checkout, and the tests stay out of `$HOME`.
2. Edit `karabiner/.config/karabiner/karabiner.json` and `aerospace/.aerospace.toml`.
3. After smoke verification, update the existing `README.md` keyboard and Raycast setup instructions. No other documentation besides this required plan.

## Raycast command

Use `#!/usr/bin/python3` and required Raycast metadata `schemaVersion 1`, title `Fork focused omp session`, `mode silent`, packageName `omp`, description describing the shown focused Tern pane. Mark executable. No decorative icon.

Use Python stdlib only. Fixed Tern binary `/Applications/Tern.app/Contents/MacOS/tern`; socket is `TERN_DAEMON_SOCKET` if explicitly supplied, otherwise `~/Library/Application Support/Tern/daemon.sock`. Run Tern subprocesses with the same daemon socket, removing inherited pane/window selection variables so a Raycast invocation cannot accidentally select the agent's launch pane. Set a finite subprocess and socket timeout.

Functions:

```python
def focused_pane(snapshot: dict) -> int: ...
def receive_frame(connection: socket.socket) -> dict: ...
def send_frame(connection: socket.socket, message: dict) -> None: ...
def fork_focused() -> int: ...
def main() -> int: ...
```

`fork_focused()` runs `tern inspect --json` with clean selection environment. Reject anything other than exactly one distinct window client (`kind == "window"`) before any mutation. From sessions with `shown == true`, then tabs with `shown == true`, select blocks with `focused == true`; require exactly one. Use `panes` metadata to reject a pane without `omp_session_file`. Pass opaque numeric pane IDs unchanged. Do not derive IDs for remote hosts.

Connect to the daemon socket. Each frame is 4-byte little-endian payload size followed by UTF-8 JSON. Read exactly the requested byte count in a loop; reject EOF and frames over 256 MiB. Send `{"hello":{}}`, receive welcome, require `fork` in `welcome.ops`. Send `{"id":1,"fork":{"block":P,"dir":"right"}}`. Correlate response ID and channel; surface `fork.error.message` as failure. Return `fork.ok.block` and print a short success message. No fallback path. Catch only meaningful IO/JSON/protocol/subprocess errors at the CLI boundary, print readable errors to stderr, and return nonzero. Do not suppress failures.

Permanent tests cover the uncertain selection boundary: hidden tabs also have focused blocks; only the shown tab qualifies, hidden sessions do not qualify, multiple windows/ambiguous or non-omp focus fails without choosing an arbitrary pane. Add fragmented frame/EOF coverage if protocol helper implementation warrants it. No source-text or metadata tests.

## Keyboard slice

Keep the terminal app condition list unchanged. In its Caps Lock manipulator change `to` from Escape to `left_shift` with `left_command,left_control,left_option`, and add `to_if_alone` Escape. Leave nonterminal Caps Lock mapping unchanged.

Preserve physical Option+Shift+F fullscreen while freeing Hyper+F: the existing `from` with `key_code f`, mandatory `right_command,shift` consumes physical modifiers; change its emitted modifiers from `left_control,left_option,left_command,left_shift` to `left_control,left_option,left_command`. Update AeroSpace fullscreen binding from `ctrl-alt-cmd-shift-f` to `ctrl-alt-cmd-f`. Do not change any other AeroSpace key or modifier mapping.

## Verification

Do not run checks during implementation. Parent runs focused unittest tests once after both slices finish. Smoke against an isolated Tern daemon/window and temporary omp session, invoke the actual script, and observe a new pane/session with parent lineage and unchanged source. Also exercise non-omp focus failure. Never fork the user's unrelated active finance/other sessions as a test.

Validate JSON and AeroSpace config through installed tooling. Preview the intended keyboard changes before live deployment. Live physical hotkey and Raycast GUI verification depend on desktop permissions; state any unavailable proof explicitly.

## Constraints

No database manipulation, suppressions, compatibility shims, composer keystroke injection, session-file heuristics, or unsupported guessed APIs. Keep scope limited to this shortcut and unavoidable modifier conflict resolution. No build/lint/test/formatter runs by implementers. No code comments beyond executable shebang and required Raycast metadata.
