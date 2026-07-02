# Files

## File: cheatsheet.md
```markdown
# Tmux Cheat Sheet

## Sessions

### Create Sessions
| Description | Shell Command | Tmux Command | Shortcut |
|-------------|---------------|--------------|----------|
| Start a new session | `tmux` or `tmux new` or `tmux new-session` | `new` | - |
| Start a new session or attach to existing | `tmux new-session -A -s mysession` | - | - |
| Start a named session | `tmux new -s mysession` | `new -s mysession` | - |

### Kill Sessions
| Description | Shell Command | Tmux Command | Shortcut |
|-------------|---------------|--------------|----------|
| Kill current session | - | `kill-session` | - |
| Kill specific session | `tmux kill-ses -t mysession` or `tmux kill-session -t mysession` | - | - |
| Kill all sessions except current | `tmux kill-session -a` | - | - |
| Kill all sessions except named | `tmux kill-session -a -t mysession` | - | - |

### Session Management
| Description | Shell Command | Tmux Command | Shortcut |
|-------------|---------------|--------------|----------|
| Rename session | - | - | `Ctrl+b $` |
| Detach from session | - | - | `Ctrl+b d` |
| Detach others (maximize) | - | `attach -d` | - |
| List sessions | `tmux ls` or `tmux list-sessions` | - | `Ctrl+b s` |
| Attach to last session | `tmux a` or `tmux at` or `tmux attach` or `tmux attach-session` | - | - |
| Attach to named session | `tmux a -t mysession` or `tmux attach -t mysession` | - | - |
| Session/Window preview | - | - | `Ctrl+b w` |
| Previous session | - | - | `Ctrl+b (` |
| Next session | - | - | `Ctrl+b )` |

## Windows

### Create & Close
| Description | Shell Command | Tmux Command | Shortcut |
|-------------|---------------|--------------|----------|
| New session with named window | `tmux new -s mysession -n mywindow` | - | - |
| Create window | - | - | `Ctrl+b c` |
| Rename window | - | - | `Ctrl+b ,` |
| Close window | - | - | `Ctrl+b &` |

### Navigation
| Description | Shell Command | Tmux Command | Shortcut |
|-------------|---------------|--------------|----------|
| List windows | - | - | `Ctrl+b w` |
| Previous window | - | - | `Ctrl+b p` |
| Next window | - | - | `Ctrl+b n` |
| Select by number | - | - | `Ctrl+b 0-9` |
| Toggle last active | - | - | `Ctrl+b l` |

### Reorder Windows
| Description | Tmux Command |
|-------------|--------------|
| Swap windows 2 and 1 | `swap-window -s 2 -t 1` |
| Move window left | `swap-window -t -1` |
| Move window between sessions | `move-window -s src_ses:win -t target_ses:win` |
| Reposition in current session | `move-window -s src_session:src_window` |
| Renumber to remove gaps | `move-window -r` or `movew -r` |

## Panes

### Split Panes
| Description | Tmux Command | Shortcut |
|-------------|--------------|----------|
| Split vertically (side by side) | `split-window -h` | `Ctrl+b %` |
| Split horizontally (stacked) | `split-window -v` | `Ctrl+b "` |
| Join windows as panes | `join-pane -s 2 -t 1` | - |
| Move pane to another window | `join-pane -s 2.1 -t 1.0` | - |

### Pane Navigation
| Description | Shortcut |
|-------------|----------|
| Toggle last active pane | `Ctrl+b ;` |
| Move pane left | `Ctrl+b {` |
| Move pane right | `Ctrl+b }` |
| Switch to pane direction | `Ctrl+b ↑/↓/←/→` |
| Switch to next pane | `Ctrl+b o` |
| Show pane numbers | `Ctrl+b q` |
| Select pane by number | `Ctrl+b q 0-9` |

### Pane Management
| Description | Tmux Command | Shortcut |
|-------------|--------------|----------|
| Toggle synchronize-panes | `setw synchronize-panes` | - |
| Toggle pane layouts | - | `Ctrl+b Space` |
| Toggle pane zoom | - | `Ctrl+b z` |
| Convert pane to window | - | `Ctrl+b !` |
| Close current pane | - | `Ctrl+b x` |

### Resize Panes
| Description | Shortcut |
|-------------|----------|
| Resize height up | `Ctrl+b ↑` or `Ctrl+b Ctrl+↑` |
| Resize height down | `Ctrl+b ↓` or `Ctrl+b Ctrl+↓` |
| Resize width left | `Ctrl+b ←` or `Ctrl+b Ctrl+←` |
| Resize width right | `Ctrl+b →` or `Ctrl+b Ctrl+→` |

## Copy Mode

### Setup
| Description | Tmux Command |
|-------------|--------------|
| Enable vi keys | `setw -g mode-keys vi` |

### Enter/Exit
| Description | Shortcut |
|-------------|----------|
| Enter copy mode | `Ctrl+b [` |
| Enter copy mode + scroll up | `Ctrl+b PgUp` |
| Quit copy mode | `q` |

### Navigation (vi mode)
| Description | Shortcut |
|-------------|----------|
| Go to top | `g` |
| Go to bottom | `G` |
| Scroll up | `↑` |
| Scroll down | `↓` |
| Move left | `h` |
| Move down | `j` |
| Move up | `k` |
| Move right | `l` |
| Forward one word | `w` |
| Backward one word | `b` |

### Search
| Description | Shortcut |
|-------------|----------|
| Search forward | `/` |
| Search backward | `?` |
| Next match | `n` |
| Previous match | `N` |

### Selection & Copy
| Description | Shortcut |
|-------------|----------|
| Start selection | `Space` |
| Clear selection | `Esc` |
| Copy selection | `Enter` |
| Paste buffer | `Ctrl+b ]` |

### Buffer Commands
| Description | Tmux Command |
|-------------|--------------|
| Display buffer contents | `show-buffer` |
| Capture pane to buffer | `capture-pane` |
| List all buffers | `list-buffers` |
| Choose and paste buffer | `choose-buffer` |
| Save buffer to file | `save-buffer buf.txt` |
| Delete buffer | `delete-buffer -b 1` |

## Misc

| Description | Tmux Command | Shortcut |
|-------------|--------------|----------|
| Enter command mode | - | `Ctrl+b :` |
| Set option globally | `set -g OPTION` | - |
| Set window option | `setw -g OPTION` | - |
| Enable mouse mode | `set mouse on` | - |

## Help

| Description | Shell Command | Tmux Command | Shortcut |
|-------------|---------------|--------------|----------|
| List key bindings | `tmux list-keys` | `list-keys` | `Ctrl+b ?` |
| Show all info | `tmux info` | - | - |
```

## File: .gitignore
```
*~
*.diff
*.patch
```

## File: Advanced-Use.md
```markdown
## Advanced use

### About this document

This document gives a brief description of some of tmux's more advanced
features and some examples. It is split into three sections covering:

* features most useful when using tmux interactively;

* those for scripting with tmux;

* and advanced configuration.

However, many of the features discussed are useful both interactively and when
scripting.

### Using tmux

#### Socket and multiple servers

tmux creates a directory for the user in `/tmp` and the server then creates a
socket in that directory. The default socket is called `default`, for example:

~~~~
$ ls -l /tmp/tmux-1000/default
srw-rw----  1 nicholas  wheel     0B Mar  9 09:05 /tmp/tmux-1000/default=
~~~~

Sometimes it is convenient to create separate tmux servers, perhaps to ensure
an important process is completely isolated or to test a tmux configuration.
This can be done by using the `-L` flag which creates a socket in `/tmp` but
with a name other than `default`. To start a server with the name `test`:

~~~~
$ tmux -Ltest new
~~~~

Alternatively, tmux can be told to use a different socket file outside `/tmp`
with the `-S` flag:

~~~~
$ tmux -S/my/socket/file new
~~~~

The socket used by a running server can be seen with the `socket_path` format.
This can be printed using the `display-message` command with the `-p` flag:

~~~~
$ tmux display -p '#{socket_path}'
/tmp/tmux-1000/default
~~~~

If the socket is accidentally deleted, it can be recreated by sending the
`USR1` signal to the tmux server:

~~~~
$ pkill -USR1 tmux
~~~~

#### Alerts and monitoring

An alert is a way of notifying the user when something happens in a pane in a
window. tmux supports three kinds of alerts:

* Bell: when the program sends an ASCII `BEL` character. This is turned on or
  off with the `monitor-bell` option.

* Activity: when any output is received from the program. This is turned on or
  off with the `monitor-activity` option.

* Silence: when no output is received from the program. A time period in
  seconds during which there must be no output is set with the
  `monitor-silence` option. A period of zero disables this alert.

<img src="images/tmux_alert_flags.png" align="right" width=368 height=235>

An alert in a pane does two things for each session containing the pane's
window.

Firstly, it sets a flag on the window in the window list, but only if the window is not
the current window. While this flag is set:

* The window is drawn in the window list using the style in the
  `window-status-bell-style` (for bell) or `window-status-activity-style` (for
  activity and silence) options. The default is to use the reverse attribute.

* The window name is followed by a `!` for bell, a `#` for activity and a `~`
  for silence.

Alert flags on a window are cleared as soon as the window becomes the current
window. All flags in a session may be cleared by using `kill-session` with the
`-C` flag:

~~~~
:kill-session -C
~~~~

<img src="images/tmux_alert_message.png" align="right" width=368 height=235>

The `C-b M-n` and `C-b M-p` key bindings move to the next or previous window
with an alert, using the `-a` flag to the `next-window` and `previous-window`
commands.

Secondly, it may show a message in the status line, sound a bell in the outside
terminal, or both. Whether this is a bell or a message is controlled by the
`visual-bell`, `visual-activity` and `visual-silence` options. The choice of
when to take this action is controlled by the `bell-action`, `activity-action`
and `silence-action` options which may be:

Value|Meaning
---|---
`any`|An alert in any window in the session triggers an action
`none`|No action is triggered in the session
`current`|An alert is triggered for a bell, activity or silence in the current window but not other windows
`other`|An alert is triggered for a bell, activity or silence in any window except the current window

#### Working directories

Each tmux session has default working directory. This is the working directory
used for each new pane.

A session's working directory is set when it is first created:

* It may be given with the `-c` flag to `new-session`, for example:

~~~~
$ tmux new -c/tmp
~~~~

* If the session is created from a key binding or from the command prompt, it
  is the working directory of the attached session

* If the session is created from the shell prompt inside or outside tmux, it is
  the working directory of the shell.

A session's working directory may be changed with the `-c` flag to
`attach-session`, for example:

~~~~
:attach -c/tmp
~~~~

When a window or pane is created, a working directory may be given with `-c` to
`new-window` or `split-window`. This is used instead of the session's default
working directory:

~~~~
:neww -c/tmp
~~~~

Or:

~~~~
:splitw -c/tmp
~~~~

tmux can try to read the current working directory of a pane from outside the
pane. This is available in the `pane_current_path` format. This changes the
`C-b "` binding to create a new pane with the same working directory as the
active pane:

~~~~
bind '"' splitw -c '#{pane_current_path}'
~~~~

#### Linking windows

XXX

#### Respawning panes and windows

Respawning a pane or window is a way to start a different (or restart the same)
program without need to recreate the window, maintaining its size, position and
index.

The `respawn-pane` command respawns a pane and `respawn-window` a window. By
default, they run the same program as the pane or window as initially created
with `split-window` or `new-window`:

~~~~
:respawn-pane
~~~~

A different command may be given as arguments:

~~~~
:respawn-pane top
~~~~

If a program is still running in the pane or window, the commands will refuse
to work. The `-k` flag kills the program in the window before starting the new
one:

~~~~
:respawn-pane -k top
~~~~

Like `split-window`, `respawn-pane` and `respawn-window` have a `-c` flag to
set the working directory.

<img src="images/tmux_remain_on_exit.png" align="right" width=368 height=235>

`respawn-pane` and `respawn-window` are useful with the `remain-on-exit`
option. When this is on, panes are not automatically killed when the program
running in them exits. Instead, a message is shown and the pane remains as it
was. This is called a dead pane, and `respawn-pane` or `respawn-window` can be
used to start the same or a different program.

#### Window sizes

Every window has a size, its horizontal and vertical dimensions. A window's
size is determined from the size of the clients attached to sessions it is
linked to. How this is done is controlled by the `window-size` option which may
be:

Value|Meaning
---|---
`largest`|The window has the size of the largest attached client; only part of the window is shown on smaller clients
`smallest`|The window has the size of the smallest attached client; on larger clients any unused space is filled with the `·` character
`latest`|The window has the size of the client which has been most recently used, for example by typing into it
`manual`|The window size is fixed; new windows use the `default-size` option and may be resized with the `resize-window` command

A window's size is not changed when it not linked to sessions that are
attached.

If a window has never been linked to an attached session - for example when
created as part of `new-session` with `-d` - it gets its size from the
`default-size` option. This is a session option with a default of 80x24:

~~~~
$ tmux show -g default-size
80x24
~~~~

When a session is created, its `default-size` option may be set at the same
time with the `-x` and `-y` flags:

~~~~~
$ tmux new -smysession -d -x160 -y48
$ tmux show -tmysession default-size
default-size 160x48
$ tmux lsw -tmysession
0: ksh* (1 panes) [160x48] [layout cc01,160x48,0,0,4] @4 (active)
~~~~~

When a window is larger than the client showing it, the visible area tracks the
cursor position. These keys may be used to view different areas of the window.

Key|Function
---|---
`C-b S-Up`|Move the visible area up
`C-b S-Down`|Move the visible area down
`C-b S-Left`|Move the visible area left
`C-b S-Right`|Move the visible area right
`C-b DC` (`C-b Delete`)|Return to tracking the cursor position

The visible area is a property of the client, so detaching the client or
changing the current window will reset to the cursor position. These keys are
bound to the `refresh-client` command.

A window size for an existing window may be set using the `resize-window`
commmand. This sets the size and automatically sets the `window-size` option to
`manual` for that window. For example:

~~~~
:resizew -x200 -y100
~~~~

To adjust the size up (`-U`), down (`-D`), left (`-L`) or right (`-R`):

~~~~
:resizew -L 20
~~~~

Or return to working out the size from attached clients:

~~~~
:resizew -A
~~~~

#### Session groups

XXX

#### Piping pane changes

tmux allows any new changes to a pane to be piped to a command. This may be
used to, for example, make a log of a pane. The `pipe-pane` command does this:

~~~~
:pipe-pane 'cat >~/mypanelog'
~~~~

No arguments stops piping:

~~~~
:pipe-pane
~~~~

The `-I` flag to `pipe-pane` sends the output of a command to a pane. For
example this will send `foo` to the pane as if it had been typed:

~~~~
:pipe-pane -I 'echo foo'
~~~~

Used like this, `pipe-pane` with `-I` is similar to the `send-keys` command
covered in a later section.

The `-o` flag will toggle piping - starting if it is not already started,
otherwise stopping it. This is useful to start and stop from a single key
binding:

~~~~
bind P pipe-pane -o 'cat >~/mypanelog'
~~~~

#### Pane titles and the terminal title

Each pane in tmux has a title. A pane's title can be set by the program running
in the pane. If the program was running outside tmux it would set the outside
terminal title - normally shown in the *X(7)* window title. Because tmux can
have multiple programs running inside it, there is a pane title for each rather
than only one. The pane title is different from the window name which is used
only by tmux and is the same for all panes in a window.

Programs inside tmux can set the pane title using an escape sequence that looks
like this:

~~~~
$ printf '\033]2;title\007'
~~~~

tmux shows the pane title for the active pane in quotes on the right of the
status line.

The pane title for a pane can be changed from tmux using the `-T` flag to the
`select-pane` command:

~~~~
:selectp -Tmytitle
~~~~

However there is nothing to stop the program inside tmux changing the title
again after this.

tmux can set the outside terminal title itself, this is controlled by the
`set-titles` option:

~~~~
set -g set-titles on
~~~~

The default title includes the names of the attached session and current window
as well as the pane title for the active pane and the indexes of any windows
with alerts. This can be changed with the `set-titles-string` option. For
example, this uses the pane title alone:

~~~~
set -g set-titles-string '#{pane_title}'
~~~~

#### Mouse key bindings

tmux handles most mouse behaviour by mapping mouse events to key bindings.
Mouse keys have special names which are the event, followed by the button
number if any, then the area where the mouse event took place. For example:

- `MouseDown1Pane` for mouse button 1 pressed down with the mouse over a pane;

- `DoubleClick2Status` for mouse button 2 double-clicked on the status line;

- `MouseDrag1Pane` and `MouseDragEnd1Pane` for mouse drag start and end on a
  pane.

- `WheelUpStatusLeft` for mouse wheel up on the left of the status line

Terminals only support three buttons and the mouse wheel.

The possible mouse events are:

Event|Description
---|---
WheelUp|Mouse wheel up
WheelDown|Mouse wheel down
MouseDown|Mouse button down
MouseUp|Mouse button up
MouseDrag|Mouse drag start
MouseDragEnd|Mouse drag end
DoubleClick|Double click
TripleClick|Triple click

The possible areas where a mouse event may take place are:

Area|Description
---|---
Pane|The contents of a pane
Border|A pane border
Status|The status line window list
StatusLeft|The left part of the status line
StatusRight|The right part of the status line
StatusDefault|Any other part of the status line

Commands bound to a mouse key binding can use `-t` with the mouse target (`=`
or `{mouse}`) to tell tmux they want to use the pane or window where the mouse
event took place. For example this binds a double-click on the status line
window list to zoom the active pane of a window:

~~~~
bind -Troot DoubleClick1Status resizep -Zt=
~~~~

When the program running in a pane can itself handle the mouse, `send-keys` can
be used with the `-M` flag to pass the mouse event through to that program. The
`mouse_any_flag` format variable is true if the program has turned the mouse
on. For example, this binding makes button 2 paste, unless used over a pane
which is in a mode or where the program has enabled the mouse for itself:

~~~~
bind -Troot MouseDown2Pane selectp -t= \; if -F "#{||:#{pane_in_mode},#{mouse_any_flag}}" "send -M" "paste -p"
~~~~

#### The environment

XXX

### Scripting tmux

#### Basics of scripting

tmux is designed to be easy to script. Almost all commands work the same way
when run using the `tmux` binary as when run from a key binding or the command
prompt inside tmux.

tmux is normally scripted using shell script but of course other languages can
be used. All examples in this document are intended for a shell based on the
Bourne shell.

Formats are an important part of scripting tmux and it is useful to be familiar
with them, see [this document](https://github.com/tmux/tmux/wiki/Formats) and
[the manual page section](https://man.openbsd.org/tmux#FORMATS).

Scripts can vary widely in intended use and that can affect how they are
written. A script that is only run interactively from a key binding may be able
to assume the current window or active pane won't change while the script is
running, so have no need to worry about targets. A script designed to set up a
new session, or run from another program, may have to be more careful.

#### Unique identifiers

Every pane, window and session in tmux has a unique identifier (ID) set by the
server. Different tmux servers can use the same IDs but within a running server
each is never changed or reused.

Pane IDs are prefixed with `%` (for example `%0` or `%123`), window by `@` (for
example `@1` or `@99`) and session by `$` (for example `$3` or `$42`).

IDs allow scripts to target a pane, window or session and be guaranteed they
are always the same even if they are killed, moved or renamed.

The IDs are available with the `pane_id`, `window_id` and `session_id` format
variables:

~~~~
$ tmux lsp -F '#{session_id} #{window_id} #{pane_id}'
$0 @8 %8
$0 @8 %11
~~~~

#### Special environment variables

tmux sets two environment variables in each pane, `TMUX` and `TMUX_PANE`:

- `TMUX` is used by tmux to work out the server socket path for commands run
  inside a pane. This is commonly used to see if a script is running inside
  tmux at all:

  ~~~~
  $ [ -n "$TMUX" ] && echo inside tmux
  ~~~~
  
  The contents up to the first comma (`,`) is the socket path, the remainder is
  for internal use. One way to get the socket path:

  ~~~~
  $ echo $TMUX|awk -F, '{ print $1 }'
  ~~~~

  Note that is not necessary to do this to give the socket path to tmux with
  `-S` - tmux can work it out itself.

- `TMUX_PANE` is the pane ID:

  ~~~~
  $ echo $TMUX_PANE
  %11
  ~~~~

#### The default target

When many tmux commands are run, they have to work out which session, window or
pane they should affect. This is known as the target and is made up of a
session, a window and a pane. Not all of these components are used by every
command, for example `split-window` needs to know which window to target, but
doesn't care about the session or pane.

The target can be specified to most commands using the `-t` flag - this is
described in the next section. If `-t` is not given, the default target is
used.

How tmux works out the default target depends on where the command is run from.
There are three typical cases:

1) Commands run interatively from tmux itself, such as from a key binding or
the command prompt.

    This is the simplest: tmux knows the client where the command was run because
the user had to trigger a key binding or press `Enter` at the command prompt.
From the client, it knows the attached session and from that it knows the
current window and active pane. That is the default target.

2) Commands run from a program running inside tmux, for example typed at a
shell prompt in a pane.

   In this case, tmux doesn't know which client the command was typed into,
because it could have been run from a script, or delayed by *sleep(1)*, or
several other things.

   However, tmux may know the name of the *tty(4)* or *pty(4)* where the command
was run. If it does, it can use that to work out the pane, because each
*tty(4)* or *pty(4)* belongs to exactly one pane. Even if the *tty(4)* or
*pty(4)* isn't available, the pane ID may be in the `TMUX_PANE` environment
variable.

   If tmux can find the pane, then it has the window as well, because each pane
belongs to one window. If that window belongs to only one session, that gives
the session and window for the default target (tmux will always use the active
pane in the window it finds).

   If the window belongs to multiple sessions, then tmux picks the most recently
used session. If the window is linked into the session multiple times (so it
has multiple window indexes), then the current window is used if the window is
the current window in the session, otherwise the lowest window index is used.

3) Commands run from a program running outside tmux, like a shell prompt in a
different *xterm(1)* that isn't running tmux.

   For this case, tmux has no information about the target from the environment at
all. So it picks the most recently used session and uses its current window and
active pane.

If a command sequence is used, the default target is worked out for the first
command in the sequence and the same target used for following commands, unless
those commands explicitly change the target - for example `split-window`
without `-d` changes the target for subsequent commands in the same command
sequence to the newly created pane.

#### Command targets

Most commands accept a `-t` argument to give the target session, window or pane
instead of relying on the default target. Commands typically want either a
session, a window or a pane. The usage of a command shows which; they can be
seen with `list-commands` or in the manual page. For example `send-prefix`
wants a pane so it says `-t target-pane`:

~~~~
$ tmux lscm send-prefix
send-prefix [-2] [-t target-pane]
~~~~

A target is made up of three parts: the session, window and pane. The session
and window are separated by a colon (`:`) and the window and pane by a period
(`.`):

~~~~
session:window.pane
~~~~

Any of these three components may be omitted, in which case if it is needed
tmux will work out what is most appropriate, similarly to how it works out the
default target.

If neither `:` nor `.` appears in the target, tmux interprets it differently
depending what the command needs. If the command wants `target-pane` then `-t1`
would be tried first as a pane and only as a window if there is no pane 1
found; if the command wants `target-window` then `-t1` will only look for the
window at index 1. For example note how the window changes from `@1` to `@8`
after pane 1 is created:

~~~~
$ tmux display -pt1 -F '#{window_id} #{pane_id}'
@1 %1
$ tmux splitw -d
$ tmux display -pt1 -F '#{window_id} #{pane_id}'
@8 %15
~~~~

This behaviour is effective when tmux is used interactively but for scripting
care must be taken that targets are correct. This is best done by noting
whether a command wants a session, a window or a pane and by using IDs and the
full target the command needs.

In a target, each of `session`, `window` and `pane` can have several different
forms. `session` can be given in several ways. The most useful are:

1) A session ID, such as `$1`, which will always match one session.

2) The exact name of a session prefixed with an `=`, for example `=mysession`.
This will only match the session named `mysession`.

3) The start of a session name. For example, `my` will match `mysession` or
`myothersession`.

4) A pattern to match against the session name. This can have `*` and `?`
wildcards: `f*` will match `foo` but not `bar`.

The most useful forms of `window` are:

1) A window ID, such as `@42`.

2) A window index, for example `1` for window 1, `99` for window `99`.

3) `{start}` (or `^`) for the lowest window index or `{end}` (or `$`) for the
highest.

4) `{last}` (or `!`) for the last window, `{next}` (or `+`) for the next and
`{previous}` (or `-`) for the previous.

`pane` can be given as:

1) A pane ID, such as `%0`.

2) A pane index, such as `3`.

3) One of the following special tokens:

    Token|Meaning
    ---|---
    `{last}` (or `!`)|The last (previously active) pane
    `{next}` (or `+`)|The next pane by number
    `{previous}` (or `-`)|previous pane by number
    `{top}`|The top pane
    `{bottom}`|The bottom pane
    `{left}`|The leftmost pane
    `{right}`|The rightmost pane
    `{top-left}`|The top-left pane
    `{top-right}`|The top-right pane
    `{bottom-left}`|The bottom-left pane
    `{bottom-right}`|The bottom-right pane
    `{up-of}`|The pane above the active pane
    `{down-of}`|The pane below the active pane
    `{left-of}`|The pane to the left of the active pane
    `{right-of}`|The pane to the right of the active pane
     
Some examples of targets are:

Example|Description
---|---
`-t1`|Session, window or pane 1 depending on what the command needs
`-t%1`|The pane with ID `%1`; the session and window will be chosen by tmux if needed
`-t:6.%1`|The pane with ID `%1` if it exists in window 6; the session will be chosen by tmux if needed
`-t:.3`|Pane 3; the session and window will be chosen by tmux if needed
`-t=mysession:5`|Window 5 in session `mysession`; the active pane will be used if a pane is needed
`-t=mysession:5.2`|Pane 2 in window 5 in session `mysession`
`-t{last}`|The last window or last pane, depending if the command wants a window or pane
`-t:{last}`|The last window; the session and pane will be chosen by tmux if needed

#### Targets for new panes, windows and sessions

The `split-window`, `new-window` and `new-session` commands all have a `-P`
flag which prints the target of the new pane, window or session to `stdout`.
This allows scripts to reliably target it with subsequent commands.

By default the output is a full or partial target, for example:

~~~~
$ tmux new -dP
2:
~~~~

But it is more useful to use the `-F` flag to get the ID:

~~~~
$ S=$(tmux new -dPF '#{session_id}')
$6
$ tmux neww -dPF '#{window_id}' -t$S
@16
~~~~

#### Getting information

There are three main ways to get information from the tmux server: list
commands, `display-message` and `show-options`.

The list commands are `list-panes`, `list-windows` and `list-sessions`.

`list-sessions` lists all sessions in the server.

`list-windows` can be used in these ways:

- Without arguments, lists all windows in a single session.

- With `-a` lists all windows in the server.

And `list-panes` can in these ways:

- Without arguments, lists all panes in a single window.

- With `-s` lists all panes in all windows in a single session.

- With `-a` lists all panes in the entire server.

Each of these commands has a `-F` flag which gives the format each line of
output. For example, to list each window in the server and its name:

~~~~
$ tmux lsw -aF '#{window_id} #{window_name}'
@0 top
@1 emacs
@2 mywindow
@3 ksh
@4 abc🤔def
@5 ksh
~~~~

Or each pane in a single window and its size:

~~~~
$ tmux lsp -t@7 -F '#{pane_id} #{pane_width} #{pane_height}'
%7 107 43
%12 53 42
%14 53 42
~~~~

These can be combined with *sh(1)* to loop over panes:

~~~~
$ tmux lsp -F'#{pane_id}'|while read i; do echo pane $i; done
~~~~

The `display-message` command is used to print individual formats. The `-p`
flag sends output to `stdout`. For example:

~~~~
$ tmux display -p '#{pane_id}'
%8
~~~~

Or:

~~~~
$ tmux display -pt@0 '#{window_name}'
top
~~~~

Options are shown using the `show-options` command. The basics are covered [in
this section](https://github.com/tmux/tmux/wiki/Getting-Started#showing-options).
In addition, the `-v` option only shows the value:

~~~~
$ tmux show -g history-limit
history-limit 2000
$ tmux show -vg history-limit
2000
~~~~

`-q` does not show an error for unknown options:

~~~~
$ tmux show -g no-such-option
invalid option: no-such-option
$ tmux show -gq no-such-option
$
~~~~

#### Sending keys

The `send-keys` command can be used to send key presses to a pane as if they
had been pressed. It takes multiple arguments. tmux checks if each argument is
the name of a key and if so the appropriate escape sequence is sent for that
key; if the argument does not match a key, it is sent as it is. For example:

<img src="images/tmux_send_keys.png" align="right" width=368 height=235>

~~~~
send hello Enter
~~~~

Sends the five characters in `hello`, followed by an Enter key press (a
newline character). Or this:

~~~~
send F1 C-F2
~~~~

Sends the escape sequences for the `F1` and `C-F2` keys.

The `-l` flag tells tmux not to look for arguments as keys but instead send
every one literally, so this will send the literal text `Enter`:

~~~~
send -l Enter
~~~~

#### Capturing pane content

Existing pane content can be captured with the `capture-pane` command. This can
save its output to a paste buffer or, more usefully, write it to `stdout` by
giving the `-p` flag.

By default, `capture-pane` captures the entire visible pane content:

~~~~
$ tmux capturep -pt%0
~~~~

The `-S` and `-E` flags give the starting and ending line numbers. Zero is the
first visible line and negative lines go into the history. The special value
`-` means the start of the history or the end of the visible content. So to
capture the entire pane including the history:

~~~~
$ tmux capturep -p -S- -E-
~~~~

A few additional flags control the format of the output:

* `-e` includes escape sequences for colour and attributes;

* `-C` escapes nonprintable characters as octal sequences;

* `-N` preserves trailing spaces at the end of lines;

* `-J` both preserves trailing spaces and joins any wrapped lines.

#### Empty panes

tmux allows panes to be created without a running command. There are two ways
to create an empty pane using the `split-window` command:

1) Passing an empty command:

    ~~~~
    $ tmux splitw ''
    ~~~~

   A pane created like this starts completely empty.

<img src="images/tmux_empty_pane.png" align="right" width=376 height=243>

2) By using the `-I` flag and providing input on `stdin`:

    ~~~~
    $ echo hello|tmux splitw -I
    ~~~~

An existing empty pane may be written to with the `-I` flag to
`display-message`:

~~~~
P=$(tmux splitw -dPF '#{pane_id}' '')
echo hello again|tmux display -It$P
~~~~

They accept escape sequences the same as if a program running in the pane was
sending them:

~~~~
printf '\033[H\033[2J\033[31mred'|tmux display -It$P
~~~~

#### Waiting, signals and locks

XXX

### Advanced configuration

#### Checking configuration files

The `source-file` command has two flags to help working with configuration
files:

* `-n` parses the file but does not execute any of the commands.

* `-v` prints the parsed form of each command to `stdout`.

These can be useful to locate problems in a configuration file, for example by
starting tmux without `.tmux.conf` and then loading it manually:

~~~~
$ tmux -f/dev/null new -d
$ tmux source -v ~/.tmux.conf
/home/nicholas/.tmux.conf:1: set-option -g mouse on
/home/nicholas/.tmux.conf:8: unknown command: foobar
~~~~

#### Command parsing

When tmux reads a configuration file, it is processed in two broad steps:
parsing and execution. The parsing process is:

1) Configuration file directives are handled, for example `%if`. These are
   described in the next section.

2) The command is parsed and split into a set of arguments. For example take
   the command:
   ~~~~
   new -A -sfoo top
   ~~~~
   It is first split up into a list of four: `new`, `-A`, `-sfoo` and `top`.

3) This list is processed again and tmux looks up the command, so it knows it
   is `new-session` with arguments `-A`, `-s foo` and `top`.

4) The command is placed at the end of a command queue.

Once all of the configuration file is parsed, execution takes place: the
commands are executed from the command queue in order.

A similar process takes place for commands read from the command prompt or as
an argument to another command (such as `if-shell`). These are pretty much the
same as a configuration file with only one line.

For commands run from the shell, steps 1 and 2 are skipped - configuration file
directives are not supported, and the shell splits the command into arguments
before giving it to tmux.

This split into parsing and execution does not often have any visible effect
but occasionally it matters. The most obvious effect is on environment variable
expansion:

~~~~
setenv -g FOO bar
display $FOO
~~~~

This will not work as expected, because the `set-environment` command takes
place during execution and the expansion of `FOO` takes place during parsing.
However, this will work:

~~~~
FOO=bar
display $FOO
~~~~

Because both `FOO=bar` and expansion of `FOO` happen during parsing. Similarly
this will work:

~~~~
setenv -g FOO bar
display '#{FOO}'
~~~~

Although the `set-environment` happens during execution, `FOO` is not used
until `display-message` is executed and expands its argument as a format.

Care must be taken with commands that take another command as an argument,
because there may be multiple parsing stages.

#### Conditional directives

tmux supports some special syntax in the configuration file to allow more
flexible configuration. This is all processed when the configuration file is
parsed.

Conditional directives allow parts of the configuration file to be processed
only if a condition is true. A conditional directive looks like this:

~~~~
%if #{format}
commands
%endif
~~~~

If the given format is true (is not empty and not 0 after being expanded), then
commands are executed. Additional branches of the `%if` may be given with
`%elif` or a false branch with `%else`:

~~~~
%if #{format}
commands
%elif #{format}
more commands
%else
yet more commands
%endif
~~~~

Because these directives are processed when the configuration file is parsed,
they can't use the results of commands - the commands (whether outside the
conditional or in the true or false branch) are not executed until later when
the configuration file has been completely parsed.

For example, this runs a different configuration file on a different host:

~~~~
%if #{==:#{host_short},firsthost}
source ~/.tmux.conf.firsthost
%elif #{==:#{host_short},secondhost}
source ~/.tmux.conf.secondhost
%endif
~~~~

#### Running shell commands

The `run-shell` command runs a shell command:

~~~~
:run 'ls'
~~~~

If there is any output, the active pane is switched into view mode. Formats are
expanded in the `run-shell` argument:

~~~~
:run 'echo window name is #{window_name}'
~~~~

`run-shell` blocks execution of subsequent commands until the command is
finished. The `-b` flag disables this and runs the command in the background.

`run-shell` is most useful to invoke shell commands or shell scripts from a
configuration file or a key binding:

~~~~
bind O run '/path/to/my/script'
~~~~

#### Conditions with `if-shell`

`if-shell` is a versatile command that allows a choice between two tmux
commands to be made based on a shell command or (with `-F`) a format. The first
argument is a condition, the second the command to run when it is true and the
third the command to run when it is false. The third command may be left out.

If `-F` is given, the first condition argument is a format. A format is true if
it expands to a string that is not empty and not 0. Without `-F`, the first
argument is a shell command.

For example, a key binding to scroll to the top if a pane is in copy mode and
do nothing if it is not:

~~~~
bind T if -F '#{==:#{pane_mode},copy-mode}' 'send -X history-top'
~~~~

Or to rename a window based on the time:

~~~~
bind A if 'test `date +%H` -lt 12' 'renamew morning' 'renamew afternoon'
~~~~

Note that `if-shell` is different from the `%if` directive. `%if` is
interpreted when a configuration file is parsed; `if-shell` is a command that
is run with other commands and can be used in key bindings.

#### Quoting with `{}`

tmux allows sections of a configuration file to be quoted using `{` and `}`.
This is designed to allow complex commands and command sequences to be
expressed more clearly, particularly where a command takes another command as
an argument. Text between `{` and `}` is treated as a string without any
modification.

So for a simple example, the `bind-key` command can take a command as its
argument:

~~~~
bind K {
	lsk
}
~~~~

Or `if-shell` may be bound to a key:

~~~~
bind K {
	if -F '#{==:#{window_name},ksh}' {
		kill-window
	} {
		display 'not killing window'
	}
}
~~~~

This is equivalent to:

~~~~
bind K if -F '#{==:#{window_name},ksh}' 'kill-window' "display 'not killing window'"
~~~~

#### Array options

Some tmux options may be set to multiple values, these are called array
options. Each value has an index which is shown in `[` and `]` after the option
name. Array indexes can have gaps, so an array with just index 0 and 999 is
fine. The array options are `command-alias`, `terminal-features`,
`terminal-overrides`, `status-format`, `update-environment` and `user-keys`.
Every hook is also an array option.

An individual array index may be set or shown:

~~~~
$ tmux set -g update-environment[999] FOO
$ tmux show -g update-environment[999]
update-environment[999] FOO
$ tmux set -gu update-environment[999]
~~~~

Or all together by omitting the index. `-u` restores the entire array option to
the default:

~~~~
$ tmux show -g update-environment
update-environment[0] DISPLAY
update-environment[1] KRB5CCNAME
update-environment[2] SSH_ASKPASS
update-environment[3] SSH_AUTH_SOCK
update-environment[4] SSH_AGENT_PID
update-environment[5] SSH_CONNECTION
update-environment[6] WINDOWID
update-environment[7] XAUTHORITY
update-environment[999] FOO
$ tmux set -gu update-environment
$ tmux show -g update-environment
update-environment[0] DISPLAY
update-environment[1] KRB5CCNAME
update-environment[2] SSH_ASKPASS
update-environment[3] SSH_AUTH_SOCK
update-environment[4] SSH_AGENT_PID
update-environment[5] SSH_CONNECTION
update-environment[6] WINDOWID
update-environment[7] XAUTHORITY
~~~~

The `-a` flag to `set-option` appends to an array option using the next free index:

~~~~
$ tmux set -ag update-environment 'FOO'
$ tmux show -g update-environment
update-environment[0] DISPLAY
update-environment[1] KRB5CCNAME
update-environment[2] SSH_ASKPASS
update-environment[3] SSH_AUTH_SOCK
update-environment[4] SSH_AGENT_PID
update-environment[5] SSH_CONNECTION
update-environment[6] WINDOWID
update-environment[7] XAUTHORITY
update-environment[8] FOO
~~~~

`-a` can accept multiple values separated by commas. For backwards
compatibility with old tmux versions where arrays were kept as strings, a
leading comma can be given:

~~~~
$ tmux set -ag update-environment ',FOO,BAR'
~~~~

#### Command aliases

tmux allows custom commands by defining command aliases. Note this is different
from the short alias of each command (such as `lsw` for `list-windows`).
Command aliases are defined with the `command-alias` server option. This is an
array option where each entry has a number.

The default has a few settings for convenience and a few for backwards
compatibility:

~~~~
$ tmux show -s command-alias
command-alias[0] split-pane=split-window
command-alias[1] splitp=split-window
command-alias[2] "server-info=show-messages -JT"
command-alias[3] "info=show-messages -JT"
command-alias[4] "choose-window=choose-tree -w"
command-alias[5] "choose-session=choose-tree -s"
~~~~

Taking `command-alias[4]` as an example, this means that the `choose-window`
command is expanded to `choose-tree -w`.

A custom command alias is added by adding a new index to the array. Because the
defaults start at index 0, it is best to use higher numbers for additional
command aliases:

~~~~
:set -s command-alias[100] 'sv=splitw -v'
~~~~

This option makes `sv` the same as `splitw -v`:

~~~~
:sv
~~~~

Any subsequent flags or arguments given to the entered command are appended to
the replaced command. This is the same as `splitw -v -d`:

~~~~
:sv -d
~~~~

#### User options

tmux allows custom options to be set, these are called user options and can be
pane, window, session or server options. All user options are strings and the
names must be prefixed by `@`. There are no other restrictions on the value.

User options can be used to store a custom value from a script or key binding.
Because tmux doesn't already know about the option name, the `-w` flag must be
given for window options, or `-s` for server. For example to set an option on
window 2 with the window name:

~~~~
$ tmux set -Fwt:2 @myname '#{window_name}'
$ tmux show -wt:2 @myname
@mytime ksh
~~~~

Or a global session option:

~~~~
$ tmux set -g @myoption 'foo bar'
$ tmux show -g @myoption
foo bar
~~~~

User options are useful for scripting, see [this section as
well](Advanced-Use#getting-information).

#### User keys

tmux allows a set of custom key definitions. This is useful on the rare
occasion where terminals send (or can be configured to send) unusual keys
sequences that are not recognised by tmux by default.

User keys are added with the `user-keys` server option. This is an array option
where each item is a sequence that tmux matches to a `UserN` key. For example:

~~~~
set -s user-keys[0] '\033[foo'
~~~~

With this, when the sequence `\033[foo` is received from the terminal, tmux
will fire a `User0` key that can be bound as normal:

~~~~
bind -n User0 list-keys
~~~~

`user-keys[1]` maps to `User1`, `user-keys[2]` to `User2` and so on.

#### Custom key tables

A custom key table is one with a name other than the four default (`root`,
`prefix`, `copy-mode` and `copy-mode-vi`). Binding a key in a table creates
that table, for example this creates a key table called `mytable` with
`list-keys` bound to `x`:

~~~~
bind -Tmytable x list-keys
~~~~

Each client has a current key table, which may be set to no key table. The way
key processing works when a key is pressed is:

1) If the key matches the `prefix` or `prefix2` options, the client is switched
   into the `prefix` key table and tmux then waits for another key press.

2) If it doesn't match, the key is looked up in the client's key table. If the
   client has no key table, it is first switched into the key table given by
   the `key-table` option (or the `copy-mode` or `copy-mode-vi` key table if in
   copy mode).

3) If a key binding is found in the table, its command is executed. If no key
   binding is found, tmux looks for an `Any` key binding and if one is found
   executes its command instead.

4) If the key does not repeat, the client is reset to no key table and waits
   for the next key press. If it does repeat, the client is left with the key
   table where the key was found so the next key press will also try that table
   first.

The `switch-client` command's `-T` flag can be used to explicitly set the
client's key table, so when the next key is pressed, it is looked up in that
key table. This can be used to bind chains of commands or to have multiple
prefixes with different commands. For example, to make pressing `C-x` then `x`
execute `list-keys`, first create a key table with an `x` binding, then a root
binding for `C-x` to switch to that key table:

~~~~
bind -Tmytable x list-keys
bind -Troot C-x switch-client -Tmytable
~~~~

To entirely change the `root` key table for a single session, the `key-table`
option can be changed:

~~~~
set -tmysession: key-table mytable
~~~~

#### Automatic rename

XXX

#### *terminfo(5)* and `terminal-overrides`

XXX

#### The system clipboard

tmux can update the system clipboard when text is copied, for information see
[this document](https://github.com/tmux/tmux/wiki/Clipboard).

#### Running with no sessions

XXX

#### Hooks

XXX
```

## File: Clipboard.md
```markdown
## The clipboard

It is common to want to have text copied from tmux's copy mode or with the
mouse in tmux synchronized with the system clipboard. The tools offered to tmux
by terminals to do this are quite blunt and not consistently supported. This
document gives an overview of how things work and some configuration examples.

There are two posible methods:

* OSC 52 and the `set-clipboard` option.

* Piping to an external tool like `xsel`.

Note that tmux should be restarted entirely (run `tmux kill-server`) after
making changes to `.tmux.conf`.

### The `set-clipboard` option

#### How it works

Some terminals offer an escape sequence to set the clipboard. This is one of
the operating system control sequences so it is known as OSC 52.

To skip the details and read quick step-by-step instructions on configuring
`set-clipboard`, skip to [this section](Clipboard#quick-summary).

The way it works is that when text is copied in tmux it is packaged up and sent
to the outside terminal in a similar way to how tmux draws the text and colours
and attributes. The outside terminal recognises the clipboard escape sequence
and sets the system clipboard.

tmux supports this through the `set-clipboard` option. The big advantage of
this is that it works over an *ssh(1)* connection even if X11 forwarding is not
configured. The disadvantages are that it is patchily supported and can be
tricky to configure.

For `set-clipboard` to work, three things must be in place:

1. The `set-clipboard` option must be set to `on` or `external`. The default is
   `external`.

2. The `Ms` capability must be available to tmux when it looks at the
   *terminfo(5)* entry specified by `TERM`. This is present by default for some
   terminals and if not is added with `terminal-overrides` or
   `terminal-features` (see the next section).

3. The feature must be enabled in the terminal itself. How this is done varies
   from terminal to terminal. Some have it enabled by default and some do not.

The following two sections show how to configure `set-clipboard` and `Ms`;
later sections cover support in different terminals.

#### Changing `set-clipboard`

The tmux `set-clipboard` option was added in tmux 1.5 with a default of `on`;
the default was changed to `external` when `external` was added in tmux 2.6.

The difference is that `on` both makes tmux set the clipboard for the outside
terminal, and allows applications inside tmux to set tmux's clipboard (adding a
paste buffer). `external` only makes tmux set the clipboard and forbids
applications inside from doing so.

Any of these commands in `.tmux.conf` or at the command prompt will set the
three states:

~~~~
set -s set-clipboard on
set -s set-clipboard external
set -s set-clipboard off
~~~~

#### Setting the `Ms` capability

By default, tmux adds the `Ms` capability for terminals where `TERM` matches
`xterm*`. `TERM` can be checked with this command run outside tmux:

~~~~
$ echo $TERM
~~~~

To see if `Ms` is already set, run this from *inside* tmux:

~~~~
$ tmux info|grep Ms:
 180: Ms: (string) \033]52;%p1%s;%p2%s\a
~~~~

If `Ms` is shown like this, it does not need to be added. If it shows
`[missing]`, then it must be added with `terminal-overrides` or
`terminal-features`. Check what `TERM` is outside tmux:

~~~~
$ echo TERM
rxvt-unicode-256color
~~~~

Then add an appropriate `.tmux.conf` line. For tmux 3.2 or later, this looks
like this (change `rxvt-unicode-256color` to the appropriate name from `TERM`):

~~~~
set -as terminal-features ',rxvt-unicode-256color:clipboard'
~~~~

Or for older tmux versions:

~~~~
set -as terminal-overrides ',rxvt-unicode-256color:Ms=\E]52;%p1%s;%p2%s\007'
~~~~

Multiple similar lines may be added to `.tmux.conf` for different values of
`TERM` (`-a` means to append to the option). It also supports wildcards, so
using `rxvt-unicode*` would apply to both `rxvt-unicode` and
`rxvt-unicode-256color`.

#### Security concerns

If `set-clipboard` is set to `external`, only tmux can set the clipboard. If
set to `on` and tmux is version 2.6 or newer, any application running inside
tmux can create a tmux paste buffer and set the system clipboard. It doesn't
matter if the command is run with *su(1)* or *sudo(1)* - if a command can write
text to a tmux pane, it can set the clipboard.

This means that with `set-clipboard` set to `on`, great care must be taken with
untrusted commands run inside tmux.

The same applies to any commands run without tmux if OSC 52 is enabled in the
terminal.

#### Terminal support - tmux inside tmux

If tmux is run inside tmux, the inner tmux's outside terminal is tmux:

- `set-clipboard` and `Ms` must be configured for the inner tmux as for any
  other terminal. `TERM` will be `screen` or `screen-256color` or `tmux` or
  `tmux-256color`.

- The outer tmux must have `set-clipboard` set to `on` rather than `external`
  and it must be configured with `Ms` for its outside terminal, whatever that
  is.

- The outside terminal must have OSC 52 enabled.

#### Terminal support - xterm

xterm supports OSC 52 but it is disabled by default. It can be enabled by
putting this in `.Xresources` or `.Xdefaults`:

~~~~
XTerm*disallowedWindowOps: 20,21,SetXprop
~~~~

#### Terminal support - VTE terminals

VTE terminals (GNOME terminal, XFCE terminal, Terminator) do not support the
OSC 52 escape sequence.

Most will ignore it, but some versions will not and will instead print it to
the terminal - this appears as a large set of letters and numbers covering any
existing text. To fix this problem, turn `set-clipboard` off:

~~~~
set -s set-clipboard off
~~~~

#### Terminal support - Kitty

Kitty does support OSC 52, but it has a bug where it appends to the clipboard
each time text is copied rather than replacing it.

This bug can be worked around by modifying the `kitty.conf` file to add
`no-append`:

~~~~
clipboard_control write-primary write-clipboard no-append
~~~~

#### Terminal support - rxvt-unicode

rxvt-unicode does not support OSC 52 natively. There is an unofficial Perl
extension [here](http://anti.teamidiot.de/static/nei/*/Code/urxvt/).

#### Terminal support - st

st supports OSC 52 but versions before 0.8.3 have a length limit on the amount
of text that can be copied, so text may be truncated.

#### Terminal support - iTerm2

iTerm2 supports OSC 52 but it has be enabled from the preferences with this
option:

<img src="images/iterm2_clipboard.png" align="center" width=378 height=201>

#### Quick summary

In summary, to configure `set-clipboard`, follow these steps:

1. Make sure `set-clipboard` is set in tmux:

    ~~~~
    $ tmux show -s set-clipboard
    external
    ~~~~

    If it is not `on` or `external`, add this to `.tmux.conf` and restart tmux
    (use `on` rather than `external` before tmux 2.6):

    ~~~~
    set -s set-clipboard external
    ~~~~

2. Make sure `Ms` is set. Start tmux and run:

   ~~~~
   $ tmux info|grep Ms
   180: Ms: [missing]
   ~~~~

   If it is `[missing]`, get the value of `TERM` outside tmux:

   ~~~~
   $ echo $TERM
   rxvt-unicode-256color
   ~~~~

   Then add an appropriate `terminal-features` or `terminal-overrides` line to
   `.tmux.conf` and restart tmux. For tmux 3.2 or later:

   ~~~~
   set -as terminal-features ',rxvt-unicode-256color:clipboard'
   ~~~~

   Or for older tmux versions:
   
   ~~~~
   set -as terminal-overrides ',rxvt-unicode-256color:Ms=\E]52;%p1%s;%p2%s\007'
   ~~~~

   Then start tmux and check it has worked by running this inside tmux:

   ~~~~
   $ tmux info|grep Ms:
   180: Ms: (string) \033]52;%p1%s;%p2%s\a
   ~~~~

3. Enable support in the terminal options if necessary, or use a terminal where
   it is enabled by default.

### External tools

#### Available tools

An alternative to using `set-clipboard` is to use an external tool to set the
clipboard. tmux has a method to pipe copied text to a command rather than only
creating a paste buffer. The copy key bindings can be changed to do this.

The available tools are:

- On Linux and *BSD, there are the *xsel(1)* and *xclip(1)* tools, usually
  available as packages.

- macOS has a builtin tool called *pbcopy(1)*.

These tools talk to the *X(7)* server (or equivalent) directly so without
additional configuration they only work on the local computer.

#### How to configure - tmux 3.2 and later

tmux 3.2 introduced an option called `copy-command` to set a command to pipe to
for all key bindings. This is used when `copy-pipe` is called with no arguments
which is now the default. If the option is empty, the copied text is not piped.

To pipe to *xsel(1)*:

~~~~
set -s copy-command 'xsel -i'
~~~~

The more complex configuration in the next section also works with tmux 3.2 and
later versions.

#### How to configure - tmux 2.4 to 3.1

To use these tools with tmux before tmux 3.2, the copy key bindings must be
changed. The equivalent command to the default `copy-selection-and-cancel` is
`copy-pipe-and-cancel`; if using `copy-selection` instead use `copy-pipe`, or
for `copy-selection-no-clear`, `copy-pipe-no-clear`.

The copy key bindings are:

* `C-w` and `M-w` with *emacs(1)* keys (`mode-keys` set to `emacs`).

* `C-j` and `Enter` with *vi(1)* keys (`mode-keys` set to `vi`).

* `MouseDragEnd1Pane` for copying with the mouse.

These must be changed for the key table in use. For *emacs(1)* keys:

~~~~
bind -Tcopy-mode C-w               send -X copy-pipe-and-cancel 'xsel -i'
bind -Tcopy-mode M-w               send -X copy-pipe-and-cancel 'xsel -i'
bind -Tcopy-mode MouseDragEnd1Pane send -X copy-pipe-and-cancel 'xsel -i'
~~~~

Or for *vi(1)* keys:

~~~~
bind -Tcopy-mode-vi C-j               send -X copy-pipe-and-cancel 'xsel -i'
bind -Tcopy-mode-vi Enter             send -X copy-pipe-and-cancel 'xsel -i'
bind -Tcopy-mode-vi MouseDragEnd1Pane send -X copy-pipe-and-cancel 'xsel -i'
~~~~

#### How to configure - tmux 2.3 and earlier

In tmux 2.4, copy mode key bindings were completely changed so that tmux
commands could be bound in copy mode instead of a limited set of copy-mode-only
commands. The configuration for older versions for *emacs(1)* keys looks like
this:

~~~~
bind -temacs-copy C-w               copy-pipe 'xsel -i'
bind -temacs-copy M-w               copy-pipe 'xsel -i'
bind -temacs-copy MouseDragEnd1Pane copy-pipe 'xsel -i'
~~~~

Or for *vi(1)* keys:

~~~~
bind -tvi-copy C-j               copy-pipe 'xsel -i'
bind -tvi-copy Enter             copy-pipe 'xsel -i'
bind -tvi-copy MouseDragEnd1Pane copy-pipe 'xsel -i'
~~~~

#### `set-clipboard` and `copy-pipe`

If the `copy-pipe` method is used with a terminal that also supports
`set-clipboard`, the two can conflict. It is best to disable `set-clipboard` in
that case:

~~~~
set -s set-clipboard off
~~~~

#### Common issues - `DISPLAY`

Because the *xsel(1)* and *xclip(1)* tools need to talk to the *X(7)* server,
they need the `DISPLAY` environment variable to be set. This is not normally a
problem, but if it is missing (for example if tmux is started outside *X(7)*),
it can be set with something like:

~~~~
$ tmux setenv -g DISPLAY :0
~~~~

#### Common issues - *xclip(1)*

*xclip(1)* has a bug where it does not correctly close `stdout` so tmux doesn't
know it has finished and won't respond to any further key presses. The easiest
fix is to redirect `stdout` to `/dev/null`:

~~~~
xclip >/dev/null
~~~~

#### Common issues - wrong clipboard

*X(7)* has several clipboards. If copied text isn't available, look at:

* The `-p`, `-s` and `-b` flags for *xsel(1)*

* The `-selection` flag for *xclip(1)*.
```

## File: Contributing.md
```markdown
## Source code and development process

tmux is part of the OpenBSD base system and OpenBSD CVS is the primary source
repository:

https://cvsweb.openbsd.org/cgi-bin/cvsweb/src/usr.bin/tmux/

GitHub holds the portable tmux version. There are a few minor differences,
mostly for portability.

Code changes to the main tmux code are committed to OpenBSD and then a script
automatically applies any new commits to the GitHub repository every few hours.

It is fine to develop and submit code changes with a GitHub PR, but the final
form will be a patch file which is applied to OpenBSD CVS.

## Releases

tmux currently aims for a new release approximately once a year. This may
follow the same schedule as OpenBSD, around May and October, but not always.

## Code contributions

Code contributions to tmux are welcome. They may be submitted either by email
or by opening a PR on GitHub. Asking questions via email or GitHub issue, or
opening draft PRs is OK.

tmux is a volunteer project so please be patient if replies take time!

### Code style

tmux broadly follows the code style outlined in the OpenBSD
[style(9)](https://man.openbsd.org/style) manual page. Notably:

- Indentation is eight-column tabs.

- Keep lines to less than 80 columns in length. Use helper functions and
  temporary variables to help with this and improve readability.

- Space before `(` on language builtins (`if`, `switch`) but not on functions.
  Spaces around binary operators only before unary.

- `{` goes on the same line; omit `{` and `}` around single-line statements.

- Declarations go together at the head of the function. Avoid declarations in
  blocks unless they materially improve readability.

- Avoid C++-style comments.

- Prefer no brackets on `sizeof` operator unless it is required.

- Prefer OpenBSD-style secure string functions such as `strlcpy` over
  `strncpy`; never use `strcpy`.

### Licensing

tmux is licensed under the ISC license. The license text appears at the top of
each source file and is also
[here](https://raw.githubusercontent.com/tmux/tmux/refs/heads/master/COPYING).

By contributing code to tmux it is implicit that the author hold the copyright
(if the code change is copyrightable) and agree to it being licensed under the
ISC license.

### Use of AI

Code written by or with the assistance of AI can be acceptable. However, the
question of ownership and copyright of AI-produced work is not yet well-defined
in law.

Given this, in order for code produced with AI to be accepted, it must either
be trivial enough to be not copyrightable (basic refactoring, one line bug
fixes), or there must be a public statement available from the AI publisher
showing they do not assert copyright over the work.

#### GitHub Copilot

[This link](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#github-copilot) states:

>The code, functions, and other output returned to you by GitHub Copilot are called "Suggestions." GitHub does not own Suggestions. You retain ownership of Your Code and you retain responsibility for Suggestions you include in Your Code.

#### Anthropic Claude

<https://www.anthropic.com/terms> section 4:

>As between you and Anthropic, and to the extent permitted by applicable law, you retain any right, title, and interest that you have in the Inputs you submit. Subject to your compliance with our Terms, we assign to you all of our right, title, and interest—if any—in Outputs.

And <https://www.anthropic.com/legal/commercial-terms> section B:

>As between the parties and to the extent permitted by applicable law, Anthropic agrees that Customer (a) retains all rights to its Inputs, and (b) owns its Outputs. Anthropic disclaims any rights it receives to the Customer Content under these Terms. Subject to Customer’s compliance with these Terms, Anthropic hereby assigns to Customer its right, title and interest (if any) in and to Outputs.

#### OpenAI ChatGPT

<https://openai.com/en-GB/policies/row-terms-of-use/>:

>Ownership of content. As between you and OpenAI, and to the extent permitted by applicable law, you (a) retain your ownership rights in Input and (b) own the Output. We hereby assign to you all our right, title, and interest, if any, in and to Output.

And <https://openai.com/en-GB/policies/services-agreement/>:

>As between Customer and OpenAI, to the extent permitted by applicable law, Customer: (a) retains all ownership rights in Input; and (b) owns all Output. OpenAI hereby assigns to Customer all OpenAI’s right, title, and interest, if any, in and to Output.

## Todo list

This is a list of outstanding feature requests, ideas and notes for future
development. They are sorted into three sections approximately by complexity of
implementation. If there is a GitHub issue then its number is shown in
brackets.

It is worth getting in touch before starting work, particularly on larger
items, to avoid any duplication of effort.

### Documentation

- The getting started guide on the wiki need to be updated for 3.2 and later:

  * using marked panes with tree mode

- The advanced use guide is unfinished and also needs these added for 3.2 and
  later:

  * %local

  * terminal-features

- The modifier keys document on the wiki is out of date and needs to be updated
  for the new `extended-keys` behaviour.

- The format document needs newer features added.

### Small things

- ([#4689](https://github.com/tmux/tmux/issues/4689)) Add an emacs-style
  `recentre-top-bottom`
  (https://www.gnu.org/software/emacs/manual/html_node/emacs/Recentering.html)
  command to copy mode.

- ([#4782](https://github.com/tmux/tmux/issues/4782)) Add `-F` to `kill-pane`
  and `kill-window` to kill only panes or windows where a format returns true.

- ([#4357](https://github.com/tmux/tmux/issues/4357)) Make `?` or `h` display
  key bindings in choose modes.

- ([#4127](https://github.com/tmux/tmux/issues/4127)) Support requesting OSC 12
  from outside terminal like OSC 10 and 11.

- ([#3466](https://github.com/tmux/tmux/issues/3466)) Accept ANSI colour and
  attribute sequences for styles where appropriate.

- ([#2854](https://github.com/tmux/tmux/issues/2854)) Add a `monitor-input`
  option like `monitor-activity` but that only fires when the pane has not seen
  any user input, not all types of activity.

- ([#3061](https://github.com/tmux/tmux/issues/3061)) Format modifier to
  specify server, session, window, pane option to allow user options with the
  same name.

- ([#3047](https://github.com/tmux/tmux/issues/3047)) Expand targets as
  formats. Should this be done by default or require a prefix (maybe a leading
  `+` or just look for `#{`)?

- ([#3074](https://github.com/tmux/tmux/issues/3074)) Option to set the text
  shown with display-panes in the top right of the pane.

- It would be nice if a menu item could be prefixed by a + (like - for
  disabled) and this mean the menu should not be closed when it is selected,
  instead the item text (or all items) should be regenerated. This would mean
  toggle items could be implemented by having the item toggle an option which
  caused a change in its text.

- ([#2766](https://github.com/tmux/tmux/issues/2766)) A flag to select-window
  to create the window, or to new-window to select.

- ([#2601](https://github.com/tmux/tmux/issues/2601)) A way to handle duplicate
  window targets (choose MRU?). Note sure if should be default or optional.

- ([#2346](https://github.com/tmux/tmux/issues/2346)) Add a flag to
  kill-session to kill a session group, and perhaps rename-session to rename
  one.

- ([#2671](https://github.com/tmux/tmux/issues/2671)) Add a `window-size
  manual-or-smallest` which uses manual size only if there are no smaller
  clients.

- It is annoying that -t= is still needed for select-window on the status line
  when it is not needed for panes.

- "After" hooks are missing for many commands that do not use CMD_AFTERHOOK.

- A command in copy mode to toggle the selection.

- It would be nice to have some more preset layouts.

- In emacs cursor movement cancels incremental search, tmux should work the
  same way.

- ([#2205](https://github.com/tmux/tmux/issues/2205)) In copy mode, should add
  incremental search with regex (new commands).

- When queueing notifications for control mode, there is no need to queue
  session notifications for sessions other than the attached one. Similarly
  for some window notifications.

- A toggle in copy mode to automatically refresh, either when new output is
  added - with some sort of time limit, say at most once a second - or if that
  is tricky, just once a second.

### Medium things

- ([#4329](https://github.com/tmux/tmux/issues/4329)) &
  ([#4431](https://github.com/tmux/tmux/issues/4431)) Support SIXEL, bracket
  paste, etc in popups.

- ([#4381](https://github.com/tmux/tmux/issues/4381)) Allow middle splits to be
  resized by `resize-pane`.

- ([#3794](https://github.com/tmux/tmux/issues/3794)) Some way to access
  hyperlinks through commands.

- ([#4483](https://github.com/tmux/tmux/issues/4483)) Draw command prompt with
  `format_draw` so that styles (notably alignment) can work.

- (#[3342](https://github.com/tmux/tmux/issues/3242)) Ability to synchronize
  the scrolling of two panes in copy mode.

- (#[3258](https://github.com/tmux/tmux/issues/3258)) Server-wide list of last
  used panes (and windows?) and mode to choose.

- (#[3166](https://github.com/tmux/tmux/issues/3166)) A way to number matches
  in copy mode to easily select them, and default keys to number useful stuff.

- More use of commands as their own objects:

  - Pretty print commands from list-keys etc.

  - Store commands in options (so thay can be pretty printed as well). Options
    would be better if they were not tied to the table, so the options tree
    allows any option to be any type, and set-option did the validation. Also
    if array indexes could be strings.

- ([#3036](https://github.com/tmux/tmux/issues/3036)) Could choose mode show
  multiple columns?

- ([#2484](https://github.com/tmux/tmux/issues/2797)) Highlight incoming text.

- Allow focus to be put back to pane while leaving popup open, and back to
  popup later. Problem: what if a pane is completely obscured by popup?

- A key table timeout and a key binding fired when timeout happens with the
  previous key in a format or something, would allow binding C-b 1 0 to window
  10 while keeping C-b 1 for window 1.

- ([#2537](https://github.com/tmux/tmux/issues/2537)) Copy mode should try to
  let the terminal wrap naturally if possible when redrawing so that terminal
  line copy works better. This could only happen when the terminal is the same
  width as it was when copy mode was entered. Redrawing a region would be
  difficult - have to redraw lines before in case it wraps? Maybe writing the
  copy mode screen could use grid_reader?

- ([#2495](https://github.com/tmux/tmux/issues/2495)) Per-session window
  options.

- ([#2499](https://github.com/tmux/tmux/issues/2499)) &
  ([#2512](https://github.com/tmux/tmux/issues/2512)) Add a way for
  command-prompt, confirm-before and possibly choose-tree and similar to print
  choice to stdout. Options are 1) to add flags to do it (like display-message
  -p) or 2) permit display-message -p to work when used as the choice command.

- Per line grid time tracking and use of it in copy mode and elsewhere?

- ([#2354](https://github.com/tmux/tmux/issues/2354)) Copy mode styles for the
  word and line.

- Extend the active-pane flag to windows so a client can have an independent
  current window. This can be similar to how it works for panes but is probably
  more complicated. The idea would be to get rid of session groups.

- Customize mode:
  1) way to export option or tagged options to a file;
  2) `e` key like in buffer mode to edit option value or key command in an editor popup;
  3) way to add new user options;
  4) way to add new key bindings;
  5) 'd' on a header should restore entire key table to default.

- unbind -d flag to restore key bindings to default, with -a to restore all.

- In copy mode - should the bottom be the last used line? It can be annoying to
  have to move the cursor through a load of empty space. It might be better to
  draw a line at the bottom (already have code for this) and prevent the cursor
  moving below it.

- Completion at the command prompt could be more clever: it could recognise
  commands and have some way to describe their arguments so for example only
  complete options for set-option and layouts for select-layout; it could
  complete -t with a space after it as well as without; it could complete
  special targets like {left}; it could complete panes as well as windows.
  Probably lots more things.

- Support DECSLRM margins within tmux itself.

- Should remember the last layout before select-layout was used and
  select-layout without an argument should include it, so C-Space could cycle
  through it with the preset layouts. Also a separate flag or layout name to
  restore it directly. Or how about a layout history and a way to move back? A menu?

- Should last pane be a stack like windows?

- wait-for could do more, for example being able to wait for a pane to exit or
  close (could use the existing notify code in some way). Also a flag for a
  timeout or to stop waiting on a signal.

- ([#1784](https://github.com/tmux/tmux/issues/1784)) A way to disable line
  wrap but preserve any trimmed content (so it can be viewed if the pane is
  made bigger).

- Moving, joining and otherwise reorganizing panes, windows and session should
  be easier in tree mode. This should use the marked pane rather than mixing it
  up with tagging. Maybe keys to break/join/move without leaving tree mode?
  Also dragging would be nice.

- Make the command prompt able to take up multiple lines.

- ([#918](https://github.com/tmux/tmux/issues/918)) A way to specify how panes
  are merged when one is killed. Could be an option to kill-pane.

- Allow multiple targets either with multiple -t or by giving a pattern or both.

- It would be nice to be able to remember the position in copy mode and go back
  to the same place when entering it again. How would this work if the pane
  scrolls? What about entering with the mouse?

- It would be nice to have commands to build a paste buffer in copy mode by
  doing multiple copies. It would need to display the work in progress
  somewhere (bottom left?) and have a command to add a chunk of text and a
  command to remove the last chunk and a command to clear.

- ([#1868](https://github.com/tmux/tmux/issues/1868)) Vertical-only zoom.

- ([#1774](https://github.com/tmux/tmux/issues/1774)) Resizing panes should
  move to the parent cell and resize it if this would allow the pane to
  become closer to what is requested.

- ([#3753](https://github.com/tmux/tmux/issues/3753)) Improve SIXEL placeholders.

- ([#4236](https://github.com/tmux/tmux/issues/4236)) Option to turn off pane
  borders entirely.

### Large things

- More consistent command handling (at cost of breaking all configs);

  - Commands given to other commands are all parsed immediately at parse time,
    basically either they have to be {} or strings becomes treated like {}. So
    if-shell and friends never get string arguments, only commands arguments.

  - Parser tags string arguments as " or '.

  - Before a command is executed, a callback is fired to get a format tree,
    then each " argument has formats expanded (other stuff could be expanded at
    the same time like \n which would simplify the parser).

  - %% expansion would remain a second expansion step, it could also apply only to " arguments.

  - All -F flags and inline format expansion become no-ops or removed.

  - Options would need to support commands as native arguments for both user
    options and hooks. This could be done without breaking any backwards
    compatibility.

  - command-alias is replaced with something else where the name and commands
    are given separately so the commands can be parsed up front (more like a
    function). An equivalent to the shell's argument accessor stuff like $1 and
    "$@" would need to be expanded at execution time.

  - I think some way to do execution type parsing would need to remain, an
    equivalent of eval - maybe run -C stays like this.

- Better layouts. For example it would be good if they were driven by hints
  rather than fixed positions and could be automatically reapplied after
  resize/split/kill. Pane options can be used.

- ([#1269](https://github.com/tmux/tmux/issues/1269)) Store grids in
  blocks. Can be used to reflow on demand. Would be nice to revisit how
  history-limit works - would it be better as a global limit rather than per
  pane?

- ([#2449](https://github.com/tmux/tmux/issues/2449)) Link panes into multiple
  windows.
```

## File: Control-Mode.md
```markdown
## Control mode

Control mode is a special mode that allows a tmux client to be used to talk to
tmux using a simple text-only protocol. It was designed and written by George
Nachman and allows his [iTerm2](https://www.iterm2.com/) terminal to interface
with tmux and show tmux panes using the iTerm2 UI.

A control mode client is just like a normal tmux client except that instead of
drawing the terminal, tmux communicates using text. Because control mode is
text only, it can easily be parsed and used over *ssh(1)*.

Control mode clients accept standard tmux commands and return their output, and
additionally sends control mode only information (mostly asynchronous
notifications) prefixed by `%`. The idea is that users of control mode use tmux
commands (`new-window`, `list-sessions`, `show-options`, and so on) to control
tmux rather than duplicating a separate command set just for control mode.

### Entering control mode

The `-C` flag to tmux starts a client in control mode. This is only really
useful with the `attach-session` or `new-session` commands that attach the
client.

`-C` has two forms. A single `-C` doesn't change any terminal attributes -
leaving the terminal in canonical mode, so for example echo is still enabled.
This is intended for testing: typing will appear, control characters like
delete and kill still work.

Two `-C` (so `-CC`) disables canonical mode and most other terminal features
and is intended for applications (that, for example, don't need echo). In
addition, the `-CC` form sends a `\033P1000p` DSC sequence (similar to ReGIS)
that a listening terminal can use to detect control mode has been entered and
sends a `%exit` line and a corresponding `ST` (`\033\`) sequence when the
client exits.

With either form, entering an empty line (just pressing `Enter`) will detach
the client.

For example, this shows output from starting a new tmux server on a socket
called `test` with a new session (it runs `new-session`) and attaching a client
in control mode, then killing the server:

~~~~
$ tmux -Ltest -C new
%begin 1578920019 258 0
%end 1578920019 258 0
%window-add @1
%sessions-changed
%session-changed $1 1
%window-renamed @1 tmux
%output %1 nicholas@yelena:~$
%window-renamed @1 ksh
kill-server
%begin 1578920028 265 1
%end 1578920028 265 1
~~~~

In this example, `kill-server` is a command entered by the user and the
remaining lines starting with `%` are sent by the tmux server.

### Commands

tmux commands or command sequences may be sent to the control mode client, for
example creating a new window:

~~~~
new -n mywindow
%begin 1578920529 257 1
%end 1578920529 257 1
~~~~

Every command produces one block of output. This is wrapped in two guard lines:
either `%begin` and `%end` if the command succeeded, or `%begin` and `%error`
if it failed.

Every `%begin`, `%end` or `%error` has three arguments:

1. the time as seconds from epoch;

2. a unique command number;

3. flags, at the moment this is always one.

The time and command number for `%begin` will always match the corresponding
`%end` or `%error`, although tmux will never mix output for different commands
so there is no requirement to use these.

Output from commands is sent as it would be if the command was used from inside
tmux or from a shell prompt, for example:

~~~~
lsp -a
%begin 1578922740 269 1
0:0.0: [80x24] [history 0/2000, 0 bytes] %0 (active)
1:0.0: [80x24] [history 0/2000, 0 bytes] %1 (active)
1:1.0: [80x24] [history 0/2000, 0 bytes] %2 (active)
%end 1578922740 269 1
~~~~

Or:

~~~~
abcdef
%begin 1578923149 270 1
parse error: unknown command: abcdef
%error 1578923149 270 1
~~~~~

### Getting information

Most control mode users will want to get information from the tmux server. The
most useful commands to do this are `list-sessions`, `list-windows`,
`list-panes` and `show-options`.

The `-F` flag should be used where possible for output in a known format rather
than relying on the default. The `q` format modifier is useful for escaping.

For example listing all sessions with their ID and name:

~~~~
ls -F '#{session_id} "#{q:session_name}"'
%begin 1578925957 337 1
$4 "\"quoted\""
$2 "abc\ def"
$0 "bar"
$1 "foo"
$3 "😀"
%end 1578925957 337 1
~~~~

### Pane output

Like a normal tmux client, a control mode client may be attached to a single
session (which can be changed using commands like `switch-client`,
`attach-session` or `kill-session`). Any output in any pane in any window in
the attached session is sent to the control client. This takes the form of a
`%output` notification with two arguments:

1. The pane ID (*not* the pane number).

2. The output.

The output has any characters less than ASCII 32 and the `\` character replaced
with their octal equivalent, so `\` becomes `\134`. Otherwise, it is exactly
what the application running in the pane sent to tmux. It may not be valid
UTF-8 and may contain escape sequences which will be as expected by tmux (so
for `TERM=screen` or `TERM=tmux`).

For example, creating a new window and sending the *ls(1)* command:

~~~~
neww
%begin 1578923903 256 1
%end 1578923903 256 1
%output %1 nicholas@yelena:~$
send 'ls /' Enter
%begin 1578923910 261 1
%end 1578923910 261 1
%output %1 ls /\015\015\012
%output %1 altroot/     bsd.booted   dev/         obsd*        sys@\015\012bin/         bsd.rd       etc/         reboot*      tmp/\015\012
%output %1 boot         bsd.sp       home/        root/        usr/\015\012bsd          cvs@         mnt/         sbin/        var/\015\012
%output %1 nicholas@yelena:~$
~~~~~

Note that output generated by tmux itself (for example in copy or choose mode)
is not sent to control mode clients.

### Notifications

Notifications are sent to control mode clients when a change is made, either by
another client or by the tmux server itself.

The following notifications are supported:

Notification|Description
---|---
`%pane-mode-changed %pane`|A pane's mode was changed.
`%window-pane-changed @window %pane`|A window's active pane changed.
`%window-close @window`|A window was closed in the attached session.
`%unlinked-window-close @window`|A window was closed in another session.
`%window-add @window`|A window was added to the attached session.
`%unlinked-window-add @window`|A window was added to another session.
`%window-renamed @window new-name`|A window was renamed in the attached session.
`%unlinked-window-renamed @window new-name`|A window was renamed in another session.
`%session-changed $session session-name`|The attached session was changed.
`%client-session-changed client $session session-name`|Another client's attached session was changed.
`%session-renamed $session new-name`|A session was renamed.
`%sessions-changed`|A session was created or destroyed.
`%session-window-changed $session @window`|A session's current window was changed.

`$session`, `@window` and `%pane` are session, window and pane IDs.

### Special commands

tmux provides two special arguments to the `refresh-client` command for control
mode clients to perform actions not needed by normal clients. These are:

- `refresh-client -C` sets the size of a control mode client. If this is not
  used, control mode clients do not affect the size of other clients no matter
  the value of the `window-size` option. If this is used, then they are treated
  as any other client with the given size and may set the window size.

- `refresh-client -f` (`-F` is also accepted for backwards compatibility) sets
  flags for the control mode client. Some of the flags are general but several
  are only for control mode clients:
  - `no-output` does not send any `%output` notifications;
  - `wait-exit` waits for an empty line after `%exit` before actually exiting;
  - `pause-after` is used for flow control.

- `refresh-client -A` is used for flow control and `-B` for format
  subscriptions.

In addition, `send-keys` has a `-H` flag allowing Unicode keys to be entered in a
hexadecimal form.

A few commands like `suspend-client` have no effect when used with a control
mode client.

### Flow control

tmux provides a mechanism for flow control of control mode clients. Flow
control works by allowing tmux to pause output from a pane to the client once
it becomes too far behind. Once a pane is paused, the client can ask tmux to
continue sending output once it is ready. It is up to the client to update the
content of the pane if necessary, for example using `capture-pane`.

Flow control is enabled by setting the `pause-after` flag using `refresh-client
-f`. This takes a single argument which is the length of time in seconds before
a pane should be paused:

~~~~
refresh-client -f pause-after=30
~~~~

When a pane is paused, the `%pause` notification will be sent with the pane ID.
The pane can be continued with `refresh-client -A`:

~~~~
refresh-client -A '%0:continue'
~~~~

Once continued, the `%continue` notification is sent.

When flow control is enabled, the `%output` notification is not sent; instead
the `%extended-output` notification is used. This has additional arguments
terminated by a single `:` argument. Currently there are two arguments: the
pane ID and the number of milliseconds by which the pane is behind. For
example:

~~~~
%extended-output %0 1234 : abcdef
~~~~

`refresh-client -A` can also be used to manually pause a pane (`-A '%0:pause'`)
or to turn it on or off. Turning a pane off tells tmux that the client does not
require output from the pane to be sent and allows tmux to choose to stop
reading from the pane if possible.

### Format subscriptions

Control mode clients may subscribe to a format and be informed every time its
expanded value changes. A subscription is added or removed with the
`refresh-client -B` command. This takes a single argument which has three
pieces separated by colons:

1) A subscription name.

2) The type of item to subscribe to, one of:

   Type|Description
   ----|---
   Empty|The attached session.
   `%n`|A single pane ID.
   `%*`|All panes in the attached session.
   `@n`|A single window ID.
   `@*`|All windows in the attached session.

3) The format.

If the type and format are omitted and only the subscription name is given, the
subscription is removed.

tmux expands the format once for each matching item for the given type and if
the resulting value has changed sends a `%subscription-changed` notification.
This happens at most once a second.

### General notes

A few other notes:

- Using session, window and pane IDs rather than names or indexes is strongly
  recommended because they are unambiguous.

- User options  can be used  to store and retrieve  custom options in  the tmux
  server (they can be set to server, session, window or pane). `show-options -v
  @foo` shows only the option value for user option `@foo`.

- Formats are the primary method of inspecting properties of a session, window
  or pane or the tmux server itself. The `display-message -p` command is useful
  for this as well as the `-F` flag to the list commands.
```

## File: FAQ.md
```markdown
~~~~
PLEASE NOTE: most display problems are due to incorrect TERM! Before
reporting problems make SURE that TERM settings are correct inside and
outside tmux.

Inside tmux TERM must be "screen", "tmux" or similar (such as "tmux-256color").
Don't bother reporting problems where it isn't!

Outside, it should match your terminal: particularly, use "rxvt" for rxvt
and derivatives.
~~~~
### What is `TERM` and what does it do?

The environment variable `TERM` tells applications the name of a terminal
description to read from the *terminfo(5)* database. Each description consists
of a number of named capabilities which tell applications what to send to
control the terminal. For example, the `cup` capability contains the escape
sequence used to move the cursor up.

It is important that `TERM` points to the correct description for the terminal an
application is running in - if it doesn't, applications may misbehave.

The *infocmp(1)* command shows the contents of a terminal description and the
*tic(1)* command builds and installs a description from a file (the `-x` flag
is normally required with both).

### I found a bug in tmux! What do I do?

Check the latest version of tmux from Git to see if the problem is still
present.

Please send bug reports by email to *nicholas.marriott@gmail.com* or
*tmux-users@googlegroups.com* or by opening a GitHub issue. Please see the
[CONTRIBUTING](https://github.com/tmux/tmux/blob/master/.github/CONTRIBUTING.md)
file for information on what to include.

### Why doesn't tmux do $x?

Please send feature requests by email to *tmux-users@googlegroups.com* or open a GitHub issue.

### How often is tmux released? What is the version number scheme?

tmux releases are now made approximately every six months, around the same time
as OpenBSD releases (tmux is part of OpenBSD) but not necessarily on the same
day.

tmux version numbers (as reported by `tmux -V` and `display -p '#{version}'`)
match one of the following:

- Main releases have a version with one digit after the period, such as 2.9 or
  3.0. The number increases with each release, so 2.8, 2.9, 3.0, 3.1 and so on.

- Patch releases have a letter following the last digit, such as 2.9a or 3.0a.
  These contain a small number of changes to fix any bugs found shortly after
  release.

- The development source tree (master in Git) has a version prefixed by
  "next-", for example next-3.1 is the code that will eventually become the 3.1
  release.

- Release candidates have an "-rc" suffix, optionally with a number. So the
  first 3.1 release candidate is 3.1-rc, the second 3.1-rc2 and so on.

- tmux in OpenBSD does not have a version number. Until OpenBSD 6.6, it did not
  support the `-V` flag; in 6.6 and later it does and reports the OpenBSD
  version number prefixed by "openbsd-", for example openbsd-6.6.

Aside from the patch releases and release candidates mentioned above, tmux
version numbers have no special significance. tmux 3.0 is the release after
tmux 2.9, nothing more.

### Why do you use the screen terminal description inside tmux?

It is already widely available. `tmux` and `tmux-256color` entries are provided
by modern *ncurses(3)* and can be used instead by setting the `default-terminal`
option.

### tmux exited with `server exited unexpectedly` or `lost server`. What does this mean?

This message usually means the tmux server has crashed.

If the problem can be reproduced, please open a issue reporting this - there is
information in the [CONTRIBUTING](https://github.com/tmux/tmux/blob/master/.github/CONTRIBUTING.md)
file on what to include and how to get logs from tmux.

It can also be useful to enable core dumps to see why tmux crashed. On most
platforms this can be done by running `ulimit -c unlimited` before starting
tmux; if it crashes again it may generate a core file in the directory where it
is started. This may be called `tmux.core` or `core.*` or just `core`. It can
be loaded into `gdb` like this:

~~~~
$ gdb `which tmux` /path/to/core/file
...
(gdb) bt full
~~~~

If this works, include the output in the issue.

### tmux says `no sessions` when I try to attach but I definitely had sessions!

Check if tmux is still running with `pgrep` or `ps`. If not, then the server
probably crashed or was killed and the sessions are gone.

If tmux is still running, most likely something deleted the socket in `/tmp`.
The tmux server can be asked to recreate its socket by sending it the `USR1`
signal, for example: `pkill -USR1 tmux`

### I don't see any colour in my terminal! Help!

On a few platforms, common terminal descriptions such as `xterm` do not include
colour. screen ignores this, tmux does not. If the terminal emulator in use
supports colour, use a value for `TERM` which correctly lists this, such as
`xterm-color`.

### tmux freezes my terminal when I attach. I have to `kill -9` the shell it was started from to recover!

Some consoles don't like attempts to set the window title. Tell tmux not to do
this by turning off the `set-titles` option (you can do this in `.tmux.conf`:

~~~~
set -g set-titles off
~~~~

If this doesn't fix it, send a bug report.

### Why is C-b the prefix key? How do I change it?

The default key is C-b because the prototype of tmux was originally developed
inside screen and C-b was chosen not to clash with the screen meta key.

To change it, change the `prefix` option, and - if required - move the binding
of the `send-prefix` command from C-b (C-b C-b sends C-b by default) to the new
key. For example:

~~~~
set -g prefix C-a
unbind C-b
bind C-a send-prefix
~~~~

### How do I use UTF-8?

tmux requires a system that supports UTF-8 (that is, where the C library has a
UTF-8 locale) and will not start if support is missing.

tmux will attempt to detect if the terminal it is running in supports UTF-8 by
looking at the `LC_ALL`, `LC_CTYPE` and `LANG` environment variables.

If it believes the terminal is not compatible with UTF-8, any UTF-8 characters
will be replaced with underscores. The `-u` flag explicitly tells tmux that the
terminal supports UTF-8:

~~~~
$ tmux -u new
~~~~

### How do I use a 256 colour terminal?

Provided the underlying terminal supports 256 colours, it is usually sufficient
to add one of the following to `~/.tmux.conf`:

~~~~
set -g default-terminal "screen-256color"
~~~~

Or:

~~~~
set -g default-terminal "tmux-256color"
~~~~

And make sure that `TERM` outside tmux also shows 256 colours, or use the tmux
`-2` flag.

### How do I use RGB colour?

tmux must be told that the terminal outside supports RGB colour. This is done
by specifying the `RGB` or `Tc` *terminfo(5)* flags. `RGB` is the official
flag, `Tc` is a tmux extension.

With tmux 3.2 and later this can be added with the `terminal-features` option:

~~~~
set -as terminal-features ",gnome*:RGB"
~~~~

Or for any tmux version the `terminal-overrides` option:

~~~~
set -as terminal-overrides ",gnome*:Tc"
~~~~

For tmux itself, colours may be specified in hexadecimal, for example
`bg=#ff0000`.

### Why are tmux pane separators dashed rather than continuous lines?

Some terminals or certain fonts (particularly some Japanese fonts) do not
correctly handle UTF-8 line drawing characters.

The `U8` capability forces tmux to use ACS instead of UTF-8 line drawing:

~~~~
set -as terminal-overrides ",*:U8=0"
~~~~

### I want to use the mouse to select panes but the terminal to copy! How?

Terminals do not offer fine-grained mouse support - tmux can either turn on the
mouse and receive all mouse events (clicks, scrolling, everything) or it can
leave the mouse off and receive no events.

So it is not possible to configure tmux such that it handles some mouse
behaviours and the terminal others, it is all or nothing (`mouse` option `on`
or `off`).

However, when an application turns on the mouse, most terminals provide a way
to bypass it. On many Linux terminals this is holding down the `Shift` key; for
iTerm2 it is the `option` key.

Note that tmux makes no attempt to keep the terminal scrollback consistent (it
is impossible to do this with multiple windows or panes), so it is very likely
to be incomplete.

Disabling a mouse behaviour in tmux rather than having the terminal handle it
is done by unbinding the appropriate key bindings, for example to stop tmux
changing the current window when the status line is clicked on, unbind
`MouseDown1Status` in the root table:

~~~~
unbind -Troot MouseDown1Status
~~~~

### How do I translate `-fg`, `-bg` and `-attr` options into `-style` options?

Before tmux 1.9, styles (the colours and attributes of various things) were
each configured with three options - one for the foreground colour (such as
`mode-fg`), one for the background (such as `mode-bg`) and one for the attributes
(such as `mode-attr`).

In tmux 1.9 each set of three options were combined into a single option (so
`mode-fg`, `mode-bg` and `mode-attr` became `mode-style`) and in tmux 2.9 the
old options were removed. So for example:

~~~~
set -g mode-fg yellow
set -g mode-bg red
set -g mode-attr blink,underline
~~~~

Should be changed to:

~~~~
set -g mode-style fg=yellow,bg=red,blink,underline
~~~~

The format of style options is described [in the manual](https://man.openbsd.org/tmux.1#STYLES).

### What is the `escape-time` option? Is zero a good value?

Terminal applications like tmux receive key presses as a stream of bytes with
special keys marked by the ASCII ESC character (`\033`). The problem - and the
reason for escape-time - is that as well as marking special keys, the same
ASCII ESC is also used for the Escape key itself.

If tmux gets a `\033` byte followed a short time later by an x, has the user
pressed Escape followed by x, or have they pressed M-x? There is no guaranteed
way to know.

The solution to this problem used by tmux and most other terminal applications
is to introduce a delay. When tmux receives `\033`, it starts a timer - if the
timer expires without any following bytes, then the key is Escape. The downside
to this is that there is a delay before an Escape key press is recognised.

If tmux is running on the same computer as the terminal, or over a fast
network, then typically the bytes representing a key will all arrive together,
so an `escape-time` of zero is likely to be fine. Over a slower network, a larger
value would be better.

### How do I make modified function and arrow keys (like C-Up, M-PageUp) work inside tmux?

tmux sends modified function keys using *xterm(1)*-style escape sequences. This
can be verified using `cat`, for example pressing M-Left:

~~~~
$ cat
^[[1;3D
~~~~

If this is different, then `TERM` outside tmux is probably incorrect and tmux
can't recognise the keys coming from the outside terminal.

If it is correct, then some applications inside tmux do not recognise these
keys if `TERM` is set to `screen` or `screen-256color`, because these terminal
descriptions lack the capabilities. The `tmux` and `tmux-256color` descriptions
do have such capabilities, so using those instead may work. In `.tmux.conf`:

~~~~
set -g default-terminal tmux-256color
~~~~

### What is the proper way to escape characters with `#(command)`?

When using the `#(command)` construction to include the output from a command
in the status line, the command will be parsed twice. First, when it's read by
the configuration file or the command-prompt parser, and second when the status
line is being drawn and the command is passed to the shell. For example, to
echo the string "(test)" to the status line, either single or double quotes
could be used:

~~~~
set -g status-right "#(echo \\\\(test\\\\))"
set -g status-right '#(echo \\\(test\\\))'
~~~~

In both cases, the status-right option will be set to the string `#(echo
\\(test\\))` and the command executed will be `echo \(test\)`.

### tmux uses too much CPU. What do I do?

Automatic window renaming may use a lot of CPU, particularly on slow computers:
if this is a problem, turn it off with `setw -g automatic-rename off`. If this
doesn't fix it, please report the problem.

### What is the best way to display the load average? Why no `#L`?

It isn't possible to get the load average portably in code and it is preferable
not to add portability goop. The following works on at least Linux, *BSD and OS
X:

~~~~
uptime|awk '{split(substr($0, index($0, "load")), a, ":"); print a[2]}'
~~~~

### How do I attach the same session to multiple clients but with a different current window, like `screen -x`?

One or more of the windows can be linked into multiple sessions manually with
`link-window`, or a grouped session with all the windows can be created with
`new-session -t`.

### I don't see italics! Or italics and reverse are the wrong way round!

GNU screen does not support italics and the `screen` terminal description uses
the italics escape sequence incorrectly.

As of tmux 2.1, if `default-terminal` is set to `screen` or matches `screen-*`,
tmux will behave like screen and italics will be disabled.

To enable italics, make sure you are using the tmux terminal description:

~~~~
set -g default-terminal "tmux"
~~~~

### How do I see the default configuration?

Show the default session options by starting a new tmux server with no
configuration file:

~~~~
$ tmux -Lfoo -f/dev/null start\; show -g
~~~~

Or the default window options:

~~~~
$ tmux -Lfoo -f/dev/null start\; show -gw
~~~~

### How do I copy a selection from tmux to the system's clipboard?

See [this page](https://github.com/tmux/tmux/wiki/Clipboard).

### Why do I see dots around a session when I attach to it?

Until version 2.9, tmux limits the size of the window to the smallest attached
client. If it didn't do this then it would be impossible to see the entire
window. The dots mark the size of the window tmux can display.

To avoid this, detach all other clients when attaching:

~~~~
$ tmux attach -d
~~~~

Or from inside tmux by detaching individual clients with C-b D or all
using:

~~~~
C-b : attach -d
~~~~

With 2.9 or later, setting the `window-size` option to `largest` will use the
largest attached client rather than smallest.

### How do I use *ssh-agent(1)* with tmux?

*ssh-agent(1)* sets an environment variable (`SSH_AUTH_SOCK`) which needs to be
present in every shell process.

It is possible to make sure `SSH_AUTH_SOCK` is set before running tmux, then it
will be in the global environment and will be set for every pane created in
tmux. The `update-environment` option contains `SSH_AUTH_SOCK` by default so it
will update `SSH_AUTH_SOCK` in the session environment when a session is
attached or a new session is created. However, if `SSH_AUTH_SOCK` is *not* set
when a session attached, `update-environment` will cause `SSH_AUTH_SOCK` to be
*removed* from the environment and not set for new panes. See
[here](https://man.openbsd.org/OpenBSD-current/man1/tmux.1#GLOBAL_AND_SESSION_ENVIRONMENT)
and
[here](https://man.openbsd.org/OpenBSD-current/man1/tmux.1#update-environment__).

In practice, it is more reliable to set up *ssh-agent(1)* in a shell profile
that is run for every shell regardless of tmux. For a Bourne-style shell like
*ksh(1)* or *bash(1)*, something like this in `.profile`, `.kshrc`,
`.bash_profile` or `.bashrc`:

~~~~
[ ! -f ~/.ssh.agent ] && ssh-agent -s >~/.ssh.agent
eval `cat ~/.ssh.agent` >/dev/null
if ! kill -0 $SSH_AGENT_PID 2>/dev/null; then
        ssh-agent -s >~/.ssh.agent
        eval `cat ~/.ssh.agent` >/dev/null
fi
~~~~

### What is the passthrough escape sequence and how do I use it?

tmux takes care not to send escape sequences to a terminal that it isn't going
to understand because it can't predict how it will react.

However, it can be forced to pass an escape sequence through by wrapping it in
a special form of the DCS sequence with the content prefixed by `tmux;`. Any
`\033` characters in the wrapped sequence must be doubled, for example:

~~~~
\033Ptmux;\033\033]1337;SetProfile=NewProfileName\007\033\\
~~~~

Will pass this iTerm2 special escape sequence
`\033]1337;SetProfile=NewProfileName\007` through to the terminal without tmux
discarding it.

This feature should be used with care. Note that because tmux isn't aware of
any changes made to the terminal state by the passthrough escape sequence, it
is possible for it to undo them.

The passthrough escape sequence is no longer necessary for changing the cursor
colour or style as tmux now has its own support (see the `Cs`, `Cr`, `Ss` and
`Se` capabilities).

As of tmux 3.3, the `allow-passthrough` option must be set to `on` or `all` for
the passthrough sequence to work.

### How can I make .tmux.conf portable between tmux versions?

For `set-option`, the `-q` flag suppresses warnings about unknown options, for
example:

~~~~
set -gq mode-bg red
~~~~

Since tmux 2.3, the running server version is available in the `version` format
variable. This can be used with `if-shell`, `if-shell -F` (since tmux 2.0) or
`%if` (since tmux 2.4) to check for specific server versions.

The `m` (since tmux 2.6) and `m/r` (since tmux 3.0) modifiers are most useful
for this. For example to show a green status line if running a development
build, blue if version 3.1 or above and red otherwise:

~~~~
%if #{m/r:^next-,#{version}}
set -g status-style bg=green
%elif #{&&:#{m/r:^[0-9]+\.[0-9]+$,#{version}},#{e|>=|f:#{version},3.1}}
set -g status-style bg=blue
%else
set -g status-style bg=red
%endif
~~~~

For versions older than tmux 2.3, `if-shell` and `tmux -V` must be used.

Note that on OpenBSD version numbers the tmux version number tracks the OpenBSD
version, see [this FAQ
entry](https://github.com/tmux/tmux/wiki/FAQ#how-often-is-tmux-released-what-is-the-version-number-scheme)
for information on tmux version numbers.

### Why don't XMODEM, YMODEM and ZMODEM work inside tmux?

tmux is not a file transfer program and these protocols are more effort to
support than their remaining popularity deserves. Detach tmux before attempting
to use them.
```

## File: Formats.md
```markdown
## Working with formats

Formats are a powerful way to get information about a running tmux server and
control the output of various commands.

They are used widely, for example:

- Displaying information (`display-message`).

- The format of text on the status lines, the terminal title
  (`set-titles-string`), and automatic rename (`automatic-rename-format`).

- The output of list commands (`-F` flags to `list-clients`, `list-commands`,
  `list-sessions`, `list-windows`, `list-panes`, `list-buffers`).

- Targets printed by and arguments passed to new window and session (`-F` and
  `-c` flags to `new-session`, `break-pane`, `new-window`, `split-window`).

- Displayed text and filters in choose modes (`-F` and `-f` to `choose-client`,
  `choose-tree`, `choose-buffer`, as well as the `f` key).

- Setting option values (`-F` flag to `set-option`).

- Running commands (`-F` flag to `if-shell` and `run-shell`).

- Menu content (`display-menu`).

- Parse-time conditionals in the configuration file (`%if`).

This document gives a description of their syntax with examples.

Formats are also documented in the manual
[here](https://man.openbsd.org/tmux.1#FORMATS), together with a list of all the
variables.

Note that some of these features are only available in tmux 3.1 and later (most
notably: padding and multiple `s` modifiers).

### Basic use

A format is a string containing special directives contained in `#{}` which
tmux will expand (note that this is different from `#[]` which is used for
embedded styles). Each `#{}` can reference named variables with some
information about the server, session, client or similar. Not all variables are
always present - an unknown or missing variable is replaced with nothing.

The simplest use is to display some information, for example to get the tmux
server PID using `display-message` (the `-p` flag prints the result rather than
displaying it in the status line):

~~~~
$ tmux display -p '#{pid}'
98764
~~~~

Or to modify the `list-windows` output:

~~~~
$ tmux lsw -F '#{window_id} #{window_name}'
@0 irssi
@1 mutt
@3 emacs
@4 ksh
~~~~

`display-message` is a useful command for working with formats. The `-a` flag
lists the formats it knows about:

~~~~
$ tmux display -a|fgrep width=
client_width=143
pane_width=143
window_width=143
~~~~

`-v` prints verbose information on how the format is evaluated to help spot
mistakes:

~~~~
$ tmux display -vp '#{pid}'
# expanding format: #{pid}
# found #{}: pid
# format 'pid' found: 98764
# replaced 'pid' with '98764'
# result is: 98764
98764
~~~~

Because `#` is special in formats, it needs to be doubled (`##`) to include a
`#`:

~~~~
$ tmux display -p '##{pid}'
#{pid}
~~~~

Many formats have a single-character alias, such as `#S` for `#{session_name}`,
but these can't be used with modifiers and their use is not encouraged.

### Options and environment variables

As well as format variables, a `#{}` in a format can contain the name of a tmux
option, such as a user option:

~~~~
$ tmux set @foo 'hello'
$ tmux display -p 'hello #{@foo}'
hello hello
~~~~

Or the name of an environment variable in the global environment:

~~~~
$ tmux showenv -g USER
USER=nicholas
$ tmux display -p '#{USER}'
nicholas
~~~~

Most of the examples below use user options (such as `@v`) but any format
variable or option or environment variable may be used instead.

### Simple modifiers

The result of expanding a variable can be changed with modifiers.

There are a few different forms of modifier, but most consist of an operator
with zero or more arguments separated by a punctuation character (`|` or `/`
are most usual), followed by a colon and one or more additional arguments which
are the variables or formats the modifier is applied to.

The simplest modifiers take no arguments and a single variable to modify. The
`t` modifier displays a time variable as a human readable string:

~~~~
$ tmux lsw -F '#{t:window_activity}'
Fri Nov 29 13:52:35 2019
Fri Nov 29 13:37:53 2019
Fri Nov 29 12:06:46 2019
Thu Nov 28 15:51:20 2019
Thu Nov 28 07:41:05 2019
~~~~

`b` and `d` trim the file and directory name from a path:

~~~~
$ tmux set @p `pwd`
$ tmux display -p '#{d:@p}'
/usr/src/usr.bin
$ tmux display -p '#{b:@p}'
tmux
~~~~

### Trimming and padding

Format variables may be trimmed or padded. The `=` modifier trims and the `p`
modifier pads. They both take at least one argument, the width - a positive
width means to trim on the left or pad on the right and a negative the
opposite:

~~~~
$ tmux set @v "foobar"
$ tmux display -p '#{=3:@v}'
foo
$ tmux display -p '#{=-3:@v}'
bar
$ tmux display -p '#{p9:@v}baz'
foobar   baz
$ tmux display -p '#{p-9:@v}baz'
   foobarbaz
~~~~

Multiple modifiers can be applied together by separating them with a `;`, for
example:

~~~~
$ tmux set @v "foobar"
$ tmux display -p '#{=3;p-6:@v}'
   foo
~~~~

The `=` trim modifier accepts a second argument which is a string to append or
prepend to the result to show it has been trimmed. When giving more than one
argument to a modifier, they must be separated by a punctuation character,
including one right after the operator. `/` or `|` are most common separators:

~~~~
$ tmux set @v "foobar"
$ tmux display -p '#{=|6|...:@v}'  # nothing trimmed
foobar
$ tmux display -p '#{=|5|...:@v}'  # trimmed on the right
fooba...
$ tmux display -p '#{=|-5|...:@v}' # trimmed on the left
...oobar
~~~~

### Comparisons

For comparison purposes, tmux considers the result of a format to be either
true or false. The result is true if it is not empty and not a single zero
(`0`), otherwise it is false.

There are several comparison operators available. Rather than the single
variable given to `t` and `b`, these take two variables to compare, separated
by a comma. Both of these may be formats themselves rather than variables.

`==`, `!=`, `<`, `>`, `<=` and `>=` are string comparisons:

~~~~
$ tmux set @v foo
$ tmux display -p '#{==:#{@v}bar,foobar}'
1
$ tmux display -p '#{!=:#{@v}bar,foobar}'
0
$ tmux display -p '#{<:#{@v},bar}'
0
~~~~

`||` is true if either of its arguments are true and `&&` if both are:

~~~~
$ tmux set @v foo
$ tmux display -p '#{||:0,#{@v}}'
1
$ tmux display -p '#{&&:0,#{@v}}'
0
~~~~

A ternary choice operator `?` is also available. This is slightly different
from the other comparison modifiers (it was implemented earlier) and has no
colon between the operator and the condition to check. The condition is
followed by two result formats, the first is chosen if the condition is true
and the second if it is false. Either may be empty. For example:

~~~~
$ tmux set @v 0
$ tmux display -p '#{?@v,yes,no}'
no
$ tmux display -p '#{?#{==:#{@v},0},yes,no}'
yes
$ tmux display -p '#{?#{==:#{@v},0},#{@v} is true,#{@v} is false}'
0 is true
~~~~

Inside the results of the choice operator, a comma can be inserted by escaping
it as `#,`.

### Substitution

Formats support substitution through the `s` modifier. This is similar to
*sed(1)* substitution and takes two or three arguments - a regular expression
to search for, the string to replace it with and a set of flags. Both the
regular expression to search for and the string to replace with may be formats
themselves. Patterns in brackets are expanded in the replacement by number
(`\1`, `\2` and so on).

Like `t` and `b` and `d`, the variable being replaced cannot be a format but
must be a variable. Examples are:

~~~~
$ tmux set @v foobar
$ tmux display -p '#{s|foo|bar|:@v}'
barbar
$ tmux display -p '#{s|(foo)(bar)|\2\1|:@v}'
barfoo
$ tmux set @w foo
$ tmux display -p '#{s|#{@w}|xxx|:@v}'
xxxbar
~~~~

The third argument supports one flag, `i`, which means the regular expression
is case insensitive:

~~~~
$ tmux set @v foobar
$ tmux display -p '#{s|FOO|xxx|:@v}'
foobar
$ tmux display -p '#{s|FOO|xxx|i:@v}'
xxxbar
~~~~

Multiple substitutions may be done in series by separating them with `;`, like
so:

~~~~
$ tmux set @v foobar
$ tmux display -p '#{s|foo|xxx|;s|bar|yyy|:@v}'
xxxyyy
~~~~

### Expressions

In tmux 3.2 and later versions, some mathematical operations are available as
format modifiers. These are given using the `e` modifier. The first argument is
one of:

Argument|Operation
---|---
`+`|Add
`-`|Subtract
`*`|Multiply
`/`|Divide
`m`|Modulus

The second argument can be the flag `f` to use floating point numbers otherwise
integers are used. The third argument is the number of decimal places to show
in the result - the default is zero for integers and two for floating point
numbers.

For example:

~~~~
$ tmux display -p '#{e|+|:1,1}'
2
$ tmux display -p '#{e|/|f|4:10,3}'
3.3333
~~~~

### Matching and searching

The matching modifier `m` is similar to the comparison modifiers and compares
two formats - the first is a pattern matched against the second. By default
this expects an *fnmatch(3)* pattern, but the `r` flag specifies a regular
expression. The `i` flag means case insensitive.

~~~~
$ tmux set @v foobar
$ tmux display -p '#{m:*foo*,#{@v}}'
1
$ tmux display -p '#{m|ri:^FOO,#{@v}}'
1
~~~~

The `C` modifier searches for the given format in the pane content and returns
the line number or zero if not found. 

~~~~
$ # xyz
$ tmux display -p '#{C:x*z}'
4
$ tmux display -p '#{C|r:x.z}'
2
~~~~

### Loops

The `S`, `W` and `P` modifiers loop over every session, every window in the
current session and every pane in the current window and expand the given
format for each. `W` or `P` may be given a second format which is used for the
current window and active pane. For example:

~~~~
$ tmux display -p '#{W:#{window_name} }'
irssi mutt emacs ksh ksh ksh ksh ksh ksh emacs emacs ksh ksh ksh ksh ksh
$ tmux display -p '#{W:#{window_name} ,--- }'
irssi mutt emacs ksh ksh ksh ksh ksh --- emacs emacs ksh ksh ksh ksh ksh
~~~~

### Literals and quoting

The `l` modifier results in the literal string given to it, this can be used
for a literal as the first argument to the `?` choice modifier, for example:

~~~~
$ tmux display -p '#{?#{l:1},a,b}'
a
~~~~

The `q` modifier quotes any special characters, typically used if the result is
being passed as an argument to another command.

~~~~
$ tmux set @v '()'
$ tmux display -p '#{q:@v}'
\(\)
~~~~

### Multiple expansion

tmux has two modifiers which expand their result twice: `E` and `T`.
`#{E:status-left}` will expand the contents of the `status-left` option. `T` is
the same but also expands *strftime(3)* conversion specifiers (like `%H` and
`%M`).

~~~~
$ tmux display -p '#{status-left}'
[#{session_name}]
$ tmux display -p '#{T:status-left}'
[0]
~~~~

### Using formats together

Often formats are nested and used together in much more complicated ways than
the examples here. For example, here is part of the default `status-format[0]`:

~~~~
#{?#{&&:#{||:#{window_activity_flag},#{window_silence_flag}},#{!=:#{window-status-activity-style},default}}, #{window-status-activity-style},}
~~~~

This expands to the content of the `window-status-activity-style` option if
either of `window_activity_flag` or `window_silence_flag` is true and the
`window-status-activity-style` option is not `default`.

### Choose modes and formats

Formats are used for two purposes in the three choose modes: for the format of
each line and for filters.

The format of each line is specified with `-F` to `choose-buffer`,
`choose-tree` or `choose-client`. The default formats are themselves available
in formats:

~~~~
$ tmux display -p '#{client_mode_format}'
session #{session_name} (#{client_width}x#{client_height}, #{t:client_activity})
$ tmux lsc -F '#{E:client_mode_format}'
session 0 (143x44, Mon Dec  2 12:51:29 2019)
session 0 (81x24, Mon Dec  2 12:51:26 2019)
~~~~

`choose-tree` is the most complicated because it may be used for a line
containing a session, a window or a pane. The same format does all three by
using the `pane_format`, `window_format` and `session_format` variables. The
first is true for all three types of line; the second only for panes and
windows; and the third only for sessions.

All three modes support filters using the `-f` flag or by pressing the `f` key.
A filter is a format which is expanded for each line, if it is true then the
line is included in the list and if false it is not. For example to only show
sessions named `mysession`:

~~~~
$ tmux choose-tree -sf '#{==:#{session_name},mysession}'
~~~~

Or only windows with a pane containing the text `foo`:

~~~~
$ tmux choose-tree -wf '#{C:foo}'
~~~~

The `find-window` command works by automatically generating a filter like this.

### Summary of modifiers

The table below shows the syntax of the modifiers. The following fields are
used:

- `variable` means a variable name only, such as `session_name` or `@foo`. This
  is not expanded and can't contain `#{}`.

- `format` means a string fully expanded as a format, such as `abc` or
  `abc#{@foo}`. Variables must be included in `#{}` or they are not expanded:
  `session_name` is the literal string `session_name`, it must be
  `#{session_name}` to expand it.

- `single` means a single format or a variable, but not a string, so `#{session_name}`
  or `session_name` will both be expanded but `abc#{session_name}` will not.

- `string` means a string that is not expanded, such as `abc`.

- `flags` is an optional set of single character flags.

Format|Description
---|---
`#{t:variable}`|Time to human readable string
`#{b:variable}`|File name of path
`#{d:variable}`|Directory name of path
`#{=N:variable}`|Trim to width N
`#{=/N/format:variable}`|Trim to width N with a marker if trimmed
`#{pN:variable}`|Pad to width N
`#{==:format,format}`|Compare two formats (also `!=` `<` `>` `<=` `>=`)
`#{?single,format,format}`|Choose from two formats
`#{s/format/format/flags:variable}`|Substitute pattern with a string, flag `i`
`#{m/flags:format,format}`|Match a pattern against a format, flags `r` and `i`
`#{C/flags:format}`|Search for a format, flags `r` and `i`
`#{P:format,format}`|Loop over each pane (also `S`, `W`)
`#{l:string}`|Literal string
`#{E:variable}`|Expand variable content
`#{T:variable}`|Expand variable content with time conversion specifiers
`#{q:variable}`|Quote special characters
```

## File: Getting-Started.md
```markdown
## Getting started

### About tmux

tmux is a program which runs in a terminal and allows multiple other terminal
programs to be run inside it. Each program inside tmux gets its own terminal
managed by tmux, which can be accessed from the single terminal where tmux is
running - this called multiplexing and tmux is a terminal multiplexer.

tmux - and any programs running inside it - may be detached from the terminal
where it is running (the outside terminal) and later reattached to the same or
another terminal.

Programs run inside tmux may be full screen interactive programs like *vi(1)*
or *top(1)*, shells like *bash(1)* or *ksh(1)*, or any other program that can
be run in a Unix terminal.

There is a powerful feature set to access, manage and organize programs inside
tmux, both interactively and from scripts.

The main uses of tmux are to:

* Protect running programs on a remote server from connection drops by running
  them inside tmux.

* Allow programs running on a remote server to be accessed from multiple
  different local computers.

* Work with multiple programs and shells together in one terminal, a bit like a
  window manager.

For example:

* A user connects to a remote server using *ssh(1)* from an *xterm(1)* on their
  work computer and run several programs. perhaps an editor, a compiler and a
  few shells.

* They work with these programs interactively, perhaps start compiling, then
  close the *xterm(1)* with tmux and go home for the day.

* They are then able to connect to the same remote server from home, attach to
  tmux, and continue from where they were previously.

Here is a screenshot of tmux in an *xterm(1)* showing the shell:

<p align="center"><img src="images/tmux_default.png" width=368 height=235></p>

### About this document

This document gives an overview of some of tmux's key concepts, a description
of how to use the main features interactively and some information on basic
customization and configuration.

Note that this document may mention features only available in the latest tmux
release. Only the latest tmux release is supported. Releases are made
approximately every six months.

tmux may be installed from package management systems on most major platforms.
See [this document](Installing) for instructions on how to install tmux or
how to build it from source.

### Other documentation and help

Here are several places to find documentation and help about tmux:

- <img src="images/man_tmux.png" align="right" width=376 height=243>[The manual
  page](https://man.openbsd.org/tmux) has detailed reference documentation on
  tmux and a description of every command, flag and option. Once tmux is
  installed it is also available in section 1:

  ~~~~
  $ man 1 tmux
  ~~~~

- [The FAQ](FAQ) has solutions to commonly asked questions, mostly about
  specific configuration issues.

- The [tmux-users@googlegroups.com mailing list](mailto:tmux-users@googlegroups.com).

### Basic concepts

tmux has a set of basic concepts and terms it is important to be familiar with.
This section gives a description of how the terminals inside tmux are grouped
together and the various terms tmux uses.

#### The tmux server and clients

tmux keeps all its state in a single main process, called the tmux server. This
runs in the background and manages all the programs running inside tmux and
keeps track of their output. The tmux server is started automatically when the
user runs a tmux command and by default exits when there are no running
programs.

Users attach to the tmux server by starting a client. This takes over the
terminal where it is run and talks to the server using a socket file in `/tmp`.
Each client runs in one terminal, which may be an *X(7)* terminal such as
*xterm(1)*, the system console, or a terminal inside another program (such as
tmux itself). Each client is identified by the name of the outside terminal
where it is started, for example `/dev/ttypf`.

#### Sessions, windows and panes

<p><img src="images/tmux_with_panes.png" align="right" width=376 height=243>
Every terminal inside tmux belongs to one pane, this is a rectangular area
which shows the content of the terminal inside tmux. Because each terminal
inside tmux is shown in only one pane, the term pane can be used to mean all of
the pane, the terminal and the program running inside it. The screenshot to the
right shows tmux with panes.</p>

Each pane appears in one window. A window is made up of one or more panes which
together cover its entire area - so multiple panes may be visible at the same
time. A window normally takes up the whole of the terminal where tmux is
attached, but it can be bigger or smaller. The sizes and positions of all the
panes in a window is called the window layout.

Every window has a name - by default tmux will choose one but it can be changed
by the user. Window names do not have to be unique, windows are usually
identified by the session and the window index rather than their name.

<p><img src="images/tmux_pane_diagram.png" align="right" width=418 height=285>
Each pane is separated from the panes around it by a line, this is called the
pane border. There is one pane in each window called the active pane, this is
where any text typed is sent and is the default pane used for commands that
target the window. The pane border of the active pane is marked in green, or if
there are only two panes then the top, bottom, left or right half of the border
is green.</p>

Multiple windows are grouped together into sessions. If a window is part of a
session, it is said to be linked to that session. Windows may be linked to
multiple sessions at the same time, although mostly they are only in one. Each
window in a session has a number, called the window index - the same window may
be linked at different indexes in different sessions. A session's window list
is all the windows linked to that session in order of their indexes.

Each session has one current window, this is the window displayed when the
session is attached and is the default window for any commands that target the
session. If the current window is changed, the previous current window becomes
known as the last window.

A session may be attached to one or more clients, which means it is shown on
the outside terminal where that client is running. Any text typed into that
outside terminal is sent to the active pane in the current window of the
attached session. Sessions do not have an index but they do have a name, which
must be unique.

In summary:

* Programs run in terminals in panes, which each belong to one window.
* Each window has a name and one active pane.
* Windows are linked to one or more sessions.
* Each session has a list of windows, each with an index.
* One of the windows in a session is the current window.
* Sessions are attached to one or more clients, or are detached (attached to no
  clients).
* Each client is attached to one session.

#### Summary of terms

Term|Description
---|---
Client|Attaches a tmux session from an outside terminal such as *xterm(1)*
Session|Groups one or more windows together
Window|Groups one or more panes together, linked to one or more sessions
Pane|Contains a terminal and running program, appears in one window
Active pane|The pane in the current window where typing is sent; one per window
Current window|The window in the attached session where typing is sent; one per session
Last window|The previous current window
Session name|The name of a session, defaults to a number starting from zero
Window list|The list of windows in a session in order by number
Window name|The name of a window, defaults to the name of the running program in the active pane
Window index|The number of a window in a session's window list
Window layout|The size and position of the panes in a window

### Using tmux interactively

#### Creating sessions

To create the first tmux session, tmux is run from the shell. A new session is
created using the `new-session` command - `new` for short:

~~~~
$ tmux new
~~~~

Without arguments, `new-session` creates a new session and attaches it. Because
this is the first session, the tmux server is started and the tmux run from the
shell becomes the first client and attaches to it.

The new session will have one window (at index 0) with a single pane containing
a shell. The shell prompt should appear at the top of the terminal and the
green status line at the bottom (more on the status line is below).

By default, the first session will be called `0`, the second `1` and so on.
`new-session` allows a name to be specified for the session with the `-s` flag:

~~~~
$ tmux new -smysession
~~~~

This creates a new session called `mysession`. A command may be given instead
of running a shell by passing additional arguments. If one argument is given,
tmux will pass it to the shell, if more than one it runs the command directly.
For example these run *emacs(1)*:

~~~~
$ tmux new 'emacs ~/.tmux.conf'
~~~~

Or:

~~~~
$ tmux new -- emacs ~/.tmux.conf
~~~~

By default, tmux calls the first window in the session after whatever is
running in it. The `-n` flag gives a name to use instead, in this case a window
`mytopwindow` running *top(1)*:

~~~~
$ tmux new -nmytopwindow top
~~~~

`new-session` has other flags - some are covered below. A full list is [in the
tmux manual](https://man.openbsd.org/tmux#new-session).

#### The status line

When a tmux client is attached, it shows a status line on the bottom line of
the screen. By default this is green and shows:

* On the left, the name of the attached session: `[0]`.

* In the middle, a list of the windows in the session, with their index, for
  example with one window called `ksh` at index 0: `0:ksh`.

* On the right, the pane title in quotes (this defaults to the name of the host
  running tmux) and the time and the date.

<p align="center"><img src="images/tmux_status_line_diagram.png" width=613 height=204></p>

As new windows are opened, the window list grows - if there are too many
windows to fit on the width of the terminal, a `<` or `>` will be added at the
left or right or both to show there are hidden windows.

In the window list, the current window is marked with a `*` after the name, and
the last window with a `-`.

#### The prefix key

Once a tmux client is attached, any keys entered are forwarded to the program
running in the active pane of the current window. For keys that control tmux
itself, a special key must be pressed first - this is called the prefix key.

The default prefix key is `C-b`, which means the `Ctrl` key and `b`. In tmux,
modifier keys are shown by prefixing a key with `C-` for the control key, `M-`
for the meta key (normally `Alt` on modern computers) and `S-` for the shift
key. These may be combined together, so `C-M-x` means pressing the control key,
meta key and `x` together.

When the prefix key is pressed, tmux waits for another key press and that
determines what tmux command is executed. Keys like this are shown here with a
space between them: `C-b c` means first the prefix key `C-b` is pressed, then
it is released and then the `c` key is pressed. Care must be taken to release
the `Ctrl` key after pressing `C-b` if necessary - `C-b c` is different from
`C-b C-c`.

Pressing `C-b` twice sends the `C-b` key to the program running in the active
pane.

#### Help keys

Every default tmux key binding has a short description to help remember what
the key does. A list of all the keys and their corresponding description texts
can be seen by pressing `C-b ?`.

<img src="images/tmux_list_keys.png" align="right" width=376 height=243>

`C-b ?` enters view mode to show text. A pane in view mode has its own key
bindings which do not need the prefix key. These broadly follow *emacs(1)*. The
most important are `Up`, `Down`, `C-Up`, `C-Down` to scroll up and down, and
`q` to exit the mode. The line number of the top visible line together with the
total number of lines is shown in the top right.

Alternatively, the same list can be seen from the shell by running:

~~~~
$ tmux lsk -N|more
~~~~

`C-b /` shows the description of a single key - a prompt at the bottom of the
terminal appears. Pressing a key will show its description in the same place.
For example, pressing `C-b /` then `?` shows:

~~~~
C-b ? List key bindings
~~~~

#### Commands and flags

tmux has a large set of commands. These all have a name like `new-window` or
`new-session` or `list-keys` and many also have a shorter alias like `neww` or
`new` or `lsk`.

Any time a key binding is used, it runs one or more tmux commands. For example,
`C-b c` runs the `new-window` command.

Commands can also be used from the shell, as with `new-session` and `list-keys`
above.

Each command has zero or more flags, in the same way as standard Unix commands.
Flags may or may not take a single argument themselves. In addition, commands
may take additional arguments after the flags. Flags are passed after the
command, for example to run the `new-session` command (alias `new`) with flags
`-d` and `-n`:

~~~~
$ tmux new-session -d -nmysession
~~~~

All commands and their flags are documented in the tmux manual page.

This document focuses on the available key bindings, but commands are mentioned
for information or where there is a useful flag. They can be entered from the
shell or from the command prompt, described in the next section.

#### The command prompt

<img src="images/tmux_command_prompt.png" align="right" width=376 height=243>

tmux has an interactive command prompt. This can be opened by pressing `C-b :`
and appears instead of the status line, as shown in this screenshot.

At the prompt, commands can be entered similarly to how they are at the shell.
Output will either be shown for a short period in the status line, or switch
the active pane into view mode.

By default, the command prompt uses keys similar to *emacs(1)*; however, if the
`VISUAL` or `EDITOR` environment variables are set to something containing `vi`
(such as `vi` or `vim` or `nvi`), then *vi(1)*-style keys are used instead.

Multiple commands may be entered together at the command prompt by separating
them with a semicolon (`;`). This is called a command sequence.

#### Attaching and detaching

Detaching from tmux means that the client exits and detaches from the outside
terminal, returning to the shell and leaving the tmux session and any programs
inside it running in the background. To detach tmux, the `C-b d` key binding is
used. When tmux detaches, it will print a message with the session name:

~~~~
[detached (from session mysession)]
~~~~

The `attach-session` command attaches to an existing session. Without
arguments, it will attach to the most recently used session that is not already
attached:

~~~~
$ tmux attach
~~~~

Or `-t` gives the name of a session to attach to:

~~~~
$ tmux attach -tmysession
~~~~

By default, attaching to a session does not detach any other clients attached
to the same session. The `-d` flag does this:

~~~~
$ tmux attach -dtmysession
~~~~

The `new-session` command has a `-A` flag to attach to an existing session if
it exists, or create a new one if it does not. For a session named `mysession`:

~~~~
$ tmux new -Asmysession
~~~~

The `-D` flag may be added to make `new-session` also behave like
`attach-session` with `-d` and detach any other clients attached to the
session.

#### Listing sessions

The `list-sessions` command (alias `ls`) shows a list of available sessions that
can be attached. This shows four sessions called `1`, `2`, `myothersession` and
`mysession`:

~~~~
$ tmux ls
1: 3 windows (created Sat Feb 22 11:44:51 2020)
2: 1 windows (created Sat Feb 22 11:44:51 2020)
myothersession: 2 windows (created Sat Feb 22 11:44:51 2020)
mysession: 1 windows (created Sat Feb 22 11:44:51 2020)
~~~~

#### Killing tmux entirely

If there are no sessions, windows or panes inside tmux, the server will exit.
It can also be entirely killed using the `kill-server` command. For example, at
the command prompt:

~~~~
:kill-server
~~~~

#### Creating new windows

<img src="images/tmux_new_windows.png" align="right" width=376 height=243>

A new window can be created in an attached session with the `C-b c` key
binding which runs the `new-window` command. The new window is created at the
first available index - so the second window will have index 1. The new window
becomes the current window of the session.

If there are any gaps in the window list, they are filled by new windows. So if
there are windows with indexes 0 and 2, the next new window will be created as
index 1.

The `new-window` command has some useful flags which can be used with the
command prompt:

* The `-d` flag creates the window, but does not make it the current window.

* `-n` allows a name for the new window to be given. For example using the
  command prompt to create a window called `mynewwindow` without making it the
  current window:

  ~~~~
  :neww -dnmynewwindow
  ~~~~

* The `-t` flag specifies a target for the window. Command targets have a
  special syntax, but for simple use with `new-window` it is enough just to
  give a window index. This creates a window at index 999:

  ~~~~
  :neww -t999
  ~~~~

A command to be run in the new window may be given to `new-window` in the same
way as `new-session`. For example to create a new window running *top(1)*:

~~~~
:neww top
~~~~

#### Splitting the window

<img src="images/tmux_split_h.png" align="right" width=376 height=243>

A pane is created by splitting a window. This is done with the `split-window`
command which is bound to two keys by default:

* `C-b %` splits the current pane into two horizontally, producing two panes
  next to each other, one on the left and one on the right.

* `C-b "` splits the current pane into two vertically, producing two panes one
  above the other.

Each time a pane is split into two, each of those panes may be split again
using the same key bindings, until the pane becomes too small.

<img src="images/tmux_split_v.png" align="right" width=376 height=243>

`split-window` has several useful flags:

* `-h` does a horizontal split and `-v` a vertical split.

* `-d` does not change the active pane to the newly created pane.

* `-f` makes a new pane spanning the whole width or height of the window
  instead of being constrained to the size of the pane being split.

* `-b` puts the new pane to the left or above of the pane being split instead
  of to the right or below.

A command to be run in the new pane may be given to `split-window` in the same
way as `new-session` and `new-window`.

#### Changing the current window

There are several key bindings to change the current window of a session:

* `C-b 0` changes to window 0, `C-b 1` to window 1, up to window `C-b 9` for
  window 9.

* `C-b '` prompts for a window index and changes to that window.

* `C-b n` changes to the next window in the window list by number. So pressing
  `C-b n` when in window 1 will change to window 2 if it exists.

* `C-b p` changes to the previous window in the window list by number.

* `C-b l` changes to the last window, which is the window that was the current
  window before the window that is now.

These are all variations of the `select-window` command.

#### Changing the active pane

The active pane can be changed between the panes in a window with these key
bindings:

* `C-b Up`, `C-b Down`, `C-b Left` and `C-b Right` change to the pane above,
  below, left or right of the active pane. These keys wrap around the window,
  so pressing `C-b Down` on a pane at the bottom will change to a pane at the
  top.

<img src="images/tmux_display_panes.png" align="right" width=368 height=235>

* `C-b q` prints the pane numbers and their sizes on top of the panes for a
  short time. Pressing one of the number keys before they disappear changes the
  active pane to the chosen pane, so `C-b q 1` will change to pane number 1.

* `C-b o` moves to the next pane by pane number and `C-b C-o` swaps that pane
  with the active pane, so they exchange positions and sizes in the window.

These use the `select-pane` and `display-panes` commands.

Pane numbers are not fixed, instead panes are numbered by their position in the
window, so if the pane with number 0 is swapped with the pane with number 1,
the numbers are swapped as well as the panes themselves.

#### Choosing sessions, windows and panes

<p><img src="images/tmux_choose_tree1.png" align="right" width=376 height=243>
tmux includes a mode where sessions, windows or panes can be chosen from a
tree, this is called tree mode. It can be used to browse sessions, windows and
panes; to change the attached session, the current window or active pane; to
kill sessions, windows and panes; or apply a command to several at once by
tagging them.</p>

There are two key bindings to enter tree mode: `C-b s` starts showing only
sessions and with the attached session selected; `C-b w` starts with sessions
expanded so windows are shown and with the current window in the attached
session selected.

Tree mode splits the window into two sections: the top half has a tree of
sessions, windows and panes and the bottom half has a preview of the area
around the cursor in each pane. For sessions the preview shows the active panes
in as many windows will fit; for windows as many panes as will fit; and for
panes only the selected pane.

<img src="images/tmux_choose_tree2.png" align="right" width=376 height=243>

Keys to control tree mode do not require the prefix. The list may be navigated
with the `Up` and `Down` keys. `Enter` changes to the selected item (it becomes
the attached session, current window or active pane) and exits the mode.
`Right` expands the item if possible - sessions expand to show their windows
and windows to show their panes. `Left` collapses the item to hide any windows
or panes. `O` changes the order of the items and `q` exits tree mode.

Items in the tree are tagged by pressing `t` and untagged by pressing `t`
again. Tagged items are shown in bold and with `*` after their name. All tagged
items may be untagged by pressing `T`. Tagged items may be killed together by
pressing `X`, or a command applied to them all by pressing `:` for a prompt.

Each item in the tree has as shortcut key in brackets at the start of the line.
Pressing this key will immediately choose that item (as if it had been selected
and `Enter` pressed). The first ten items are keys `0` to `9` and after that
keys `M-a` to `M-z` are used.

This is a list of the keys available in tree mode without pressing the prefix
key:

Key|Function
---|---
`Enter`|Change the attached session, current window or active pane
`Up`|Select previous item
`Down`|Select next item
`Right`|Expand item
`Left`|Collapse item
`x`|Kill selected item
`X`|Kill tagged items
`<`|Scroll preview left
`>`|Scroll preview right
`C-s`|Search by name
`n`|Repeat last search
`t`|Toggle if item is tagged
`T`|Tag no items
`C-t`|Tag all items
`:`|Prompt for a command to run for the selected item or each tagged item
`O`|Change sort field
`r`|Reverse sort order
`v`|Toggle preview
`q`|Exit tree mode

Tree mode is activated with the `choose-tree` command.

#### Detaching other clients

<img src="images/tmux_choose_client.png" align="right" width=376 height=243>

A list of clients is available by pressing `C-b D` (that is, `C-b S-d`). This
is similar to tree mode and is called client mode.

Each client is shown in the list in the top half with its name, attached
session, size and the time and date when it was last used; the bottom half has
a preview of the selected client with as much of its status line as will fit.

The movement and tag keys are the same as tree mode, but others are different,
for example the `Enter` key detaches the selected client.

This is a list of the keys in client mode without the movement and tagging keys
that are the same as tree mode:

Key|Function
---|---
`Enter`|Detach selected client
`d`|Detach selected client, same as `Enter`
`D`|Detach tagged clients
`x`|Detach selected client and try to kill the shell it was started from
`X`|Detach tagged clients and try to kill the shells they were started from

Other than using client mode, the `detach-client` command has a `-a` flag to
detach all clients other than the attached client.

#### Killing a session, window or pane

Pressing `C-b &` prompts for confirmation then kills (closes) the current
window. All panes in the window are killed at the same time. `C-b x` kills only
the active pane. These are bound to the `kill-window` and `kill-pane` commands.

The `kill-session` command kills the attached session and all its windows and
detaches the client. There is no key binding for `kill-session` but it can be
used from the command prompt or the `:` prompt in tree mode.

#### Renaming sessions and windows

<img src="images/tmux_rename_session.png" align="right" width=368 height=235>

`C-b $` will prompt for a new name for the attached session. This uses the
`rename-session` command. Likewise, `C-b ,` prompts for a new name for the
current window, using the `rename-window` command.

#### Swapping and moving

tmux allows panes and windows to be swapped with the `swap-pane` and
`swap-window` commands.

To make swapping easy, a single pane can be marked. There is one marked pane
across all sessions. The `C-b m` key binding toggles whether the active pane in
the current window in the attached session is the marked pane. `C-b M` clears
the marked pane entirely so that no pane is marked. The marked pane is shown by
a green background to its border and the window containing the marked pane has
an `M` flag in the status line.

<img src="images/tmux_marked_pane.png" align="right" width=368 height=235>

Once a pane is marked, it can be swapped with the active pane in the current
window with the `swap-pane` command, or the window containing the marked pane
can be swapped with the current window using the `swap-window` command. For
example, using the command prompt:

~~~~
:swap-pane
~~~~

Panes can additionally be swapped with the pane above or below using the `C-b
{` and `C-b }` key bindings.

Moving windows uses the `move-window` command or the `C-b .` key binding.
Pressing `C-b .` will prompt for a new index for the current window. If a
window already exists at the given index, an error will be shown. An existing
window can be replaced by using the `-k` flag - to move a window to index 999:

~~~~
:move-window -kt999
~~~~

If there are gaps in the window list, the indexes can be renumbered with the
`-r` flag to `move-window`. For example, this will change a window list of 0,
1, 3, 999 into 0, 1, 2, 3:

~~~~
:movew -r
~~~~

#### Resizing and zooming panes

Panes may be resized in small steps with `C-b C-Left`, `C-b C-Right`, `C-b
C-Up` and `C-b C-Down` and in larger steps with `C-b M-Left`, `C-b M-Right`,
`C-b M-Up` and `C-b M-Down`. These use the `resize-pane` command.

A single pane may be temporarily made to take up the whole window with `C-b z`,
hiding any other panes. Pressing `C-b z` again puts the pane and window layout
back to how it was. This is called zooming and unzooming. A window where a pane
has been zoomed is marked with a `Z` in the status line. Commands that change
the size or position of panes in a window automatically unzoom the window.

#### Window layouts

<img src="images/tmux_tiled.png" align="right" width=368 height=235>

The panes in a window may be automatically arranged into one of several named
layouts, these may be rotated between with the `C-b Space` key binding or
chosen directly with `C-b M-1`, `C-b M-2` and so on.

The available layouts are:

Name|Key|Description
---|---|---
even-horizontal|`C-b M-1`|Spread out evenly across
even-vertical|`C-b M-2`|Spread out evenly up and down
main-horizontal|`C-b M-3`|One large pane at the top, the rest spread out evenly across
main-vertical|`C-b M-4`|One large pane on the left, the rest spread out evenly up and down
tiled|`C-b M-5`|Tiled in the same number of rows as columns

#### Copy and paste

tmux has its own copy and paste system. A piece of copied text is called a
paste buffer. Text is copied using copy mode, entered with `C-b [`, and the most
recently copied text is pasted into the active pane with `C-b ]`.

<img src="images/tmux_copy_mode.png" align="right" width=368 height=235>

Paste buffers can be given names but by default they are assigned a name by
tmux, such as `buffer0` or `buffer1`. Buffers like this are called automatic
buffers and at most 50 are kept - once there are 50 buffers, the oldest is
removed when another is added. If a buffer is given a name, it is called a
named buffer; named buffers are not deleted no matter how many there are.

It is possible to configure tmux to send any copied text to the system
clipboard: [this document](Clipboard) explains the different ways to configure
this.

Copy mode freezes any output in a pane and allows text to be copied. View mode
(described earlier) is a read-only form of copy mode.

Like the command prompt, copy mode uses keys similar to *emacs(1)*; however, if
the `VISUAL` or `EDITOR` environment variables are set to something containing
`vi`, then *vi(1)*-style keys are used instead. The following keys are some of
those available in copy mode with *emacs(1)* keys:

Key|Action
---|---
`Up`, `Down`, `Left`, `Right`|Move the cursor
`C-Space`|Start a selection
`C-w`|Copy the selection and exit copy mode
`q`|Exit copy mode
`C-g`|Stop selecting without copying, or stop searching
`C-a`|Move the cursor to the start of the line
`C-e`|Move the cursor to the end of the line
`C-r`|Search interactively backwards
`M-f`|Move the cursor to the next word
`M-b`|Move the cursor to the previous word

A full list of keys for both *vi(1)* and *emacs(1)* is [available in the manual
page](https://man.openbsd.org/tmux#WINDOWS_AND_PANES).

<img src="images/tmux_buffer_mode.png" align="right" width=368 height=235>

Once some text is copied, the most recent may be pasted with `C-b ]` or an
older buffer pasted by using buffer mode, entered with `C-b =`. Buffer mode is
similar to client mode and tree mode and offers a list of buffers together with
a preview of their contents. As well as the navigation and tagging keys used in
tree mode and client mode, buffer mode supports the following keys:

Key|Function
---|---
`Enter`|Paste selected buffer
`p`|Paste selected buffer, same as `Enter`
`P`|Paste tagged buffers
`d`|Delete selected buffer
`D`|Delete tagged buffers

A buffer may be renamed using the `set-buffer` command. The `-b` flag gives the
existing buffer name and `-n` the new name. This converts it into a named
buffer. For example, to rename `buffer0` to `mybuffer` from the command prompt:

~~~~
:setb -bbuffer0 -nmybuffer
~~~~

`set-buffer` can also be used to create buffers. To create a buffer called
`foo` with text `bar`:

~~~~
:setb -bfoo bar
~~~~

`load-buffer` will load a buffer from a file:

~~~~
:loadb -bbuffername ~/a/file
~~~~

`set-buffer` or `load-buffer` without `-b` creates an automatic buffer.

An existing buffer can be saved to a file with `save-buffer`:

~~~~
:saveb -bbuffer0 ~/saved_buffer
~~~~

#### Finding windows and panes

<img src="images/tmux_find_window.png" align="right" width=368 height=235>

`C-b f` prompts for some text and then enters tree mode with a filter to show
only panes where that text appears in the visible content or title of the pane
or in the window name. If panes are found, only those panes appear in the tree,
and the text `filter: active` is shown above the preview. If no panes are
found, all panes are shown in the tree and the text `filter: no matches`
appears above the preview.

#### Using the mouse

tmux has rich support for the mouse. It can be used to change the active pane
or window, to resize panes, to copy text, or to choose items from menus.

Support for the mouse is enabled with the `mouse` option; options and the
configuration file are described in detail in the next section. To turn the
mouse on from the command prompt, use the `set-option` command:

~~~~
:set -g mouse on
~~~~

Once the mouse is enabled:

<img src="images/tmux_pane_menu.png" align="right" width=376 height=243>

* Pressing the left button on a pane will make that pane the active pane.

* Pressing the left button on a window name on the status line will make that
  the current window.

* Dragging with the left button on a pane border resizes the pane.

* Dragging with the left button inside a pane selects text; the selected text
  is copied when the mouse is released.

* Pressing the right button on a pane opens a menu with various commands. When
  the mouse button is released, the selected command is run with the pane as
  target. Each menu item also has a key shortcut shown in brackets.

* Pressing the right button on a window or on the session name on the status
  line opens a similar menu for the window or session.

### Configuring tmux

#### The configuration file

When the tmux server is started, tmux runs a file called `.tmux.conf` in the
user's home directory. This file contains a list of tmux commands which are
executed in order. It is important to note that `.tmux.conf` is *only* run when
the server is started, not when a new session is created.

A different configuration file may be run from `.tmux.conf` or from a running
tmux server using the `source-file` command, for example to run `.tmux.conf`
again from a running server using the command prompt:

~~~~
:source ~/.tmux.conf
~~~~

Commands in a configuration file appear one per line. Any lines starting with
`#` are comments and are ignored:

~~~~
# This is a comment - the command below turns the status line off
set -g status off
~~~~

Lines in the configuration file are processed similar to the shell, for example:

- Arguments may be enclosed in `'` or `"` to include spaces, or spaces may be
  escaped. These four lines do the same thing:
  ~~~~
  set -g status-left "hello word"
  set -g status-left "hello\ word"
  set -g status-left 'hello word'
  set -g status-left hello\ word
  ~~~~

- But escaping doesn't happen inside `'`s. The string here is `hello\ world`
  not `hello world`:
  ~~~~
  set -g status-left 'hello\ word'
  ~~~~

- `~` is expanded to the home directory (except inside `'`s):
  ~~~~
  source ~/myfile
  ~~~~

- Environment variables can be set and are also expanded (but not inside `'`s):
  ~~~~
  MYFILE=myfile
  source "~/$MYFILE"
  ~~~~
  Any variables set in the configuration file will be passed on to new panes
  created inside tmux.

- A few special characters like `\n` (newline) and `\t` (tab) are replaced. A
  literal `\` must be given as `\\`.

Although tmux configuration files have some features similar to the shell, they
are not shell scripts and cannot use shell constructs like `$()`.

#### Key bindings

tmux key bindings are changed using the `bind-key` and `unbind-key` commands.
Each key binding in tmux belongs to a named key table. There are four default
key tables:

* The `root` table contains key bindings for keys pressed without the prefix key.

* The `prefix` table contains key bindings for keys pressed after the prefix
  key, like those mentioned so far in this document.

* The `copy-mode` table contains key bindings for keys used in copy mode with
  *emacs(1)*-style keys.

* The `copy-mode-vi` table contains key bindings for keys used in copy mode
  with *vi(1)*-style keys.

All the key bindings or those for a single table can be listed with the
`list-keys` command. By default, this shows the keys as a series of `bind-key`
commands. The `-T` flag gives the key table to show and the `-N` flag shows the
key help, like the `C-b ?` key binding.

For example to list only keys in the `prefix` table:

~~~~
$ tmux lsk -Tprefix
bind-key    -T prefix C-b     send-prefix
bind-key    -T prefix C-o     rotate-window
...
~~~~

Or:

~~~~
$ tmux lsk -Tprefix -N
C-b     Send the prefix key
C-o     Rotate through the panes
...
~~~~

`bind-key` commands can be used to set a key binding, either interactively or
most commonly from the configuration file. Like `list-keys`, `bind-key` has a
`-T` flag for the key table to use. If `-T` is not given, the key is put in the
`prefix` table; the `-n` flag is a shorthand for `-Troot` to use the `root`
table.

For example, the `list-keys` command shows that `C-b 9` changes to window 9
using the `select-window` command:

~~~~
$ tmux lsk -Tprefix 9
bind-key -T prefix 9 select-window -t :=9
~~~~

A similar key binding to make `C-b M-0` change to window 10 can be added like this:

~~~~
bind M-0 selectw -t:=10
~~~~

The `-t` flag to `select-window` specifies the target window. In this example,
the `:` means the target is a window and `=` means the name must match `10`
exactly. Targets are documented further in the [COMMANDS section of the manual
page](https://man.openbsd.org/tmux#COMMANDS).

The `unbind-key` command removes a key binding. Like `bind-key` it has `-T` and
`-n` flags for the key table. It is not necessary to remove a key binding
before binding it again, `bind-key` will replace any existing key binding.
`unbind-key` is necessary only to completely remove a key binding:

~~~~
unbind M-0
~~~~

#### Copy mode key bindings

Copy mode key bindings are set in the `copy-mode` and `copy-mode-vi` key
tables. Copy mode has a separate set of commands which are passed using the
`-X` flag to the `send-keys` command, for example the copy mode `start-of-line`
command moves the cursor to the start of the line and is bound to `C-a` in the
`copy-mode` key table:

~~~~
$ tmux lsk -Tcopy-mode C-a
bind-key -T copy-mode C-a send-keys -X start-of-line
~~~~

A full list of copy mode commands is [available in the manual
page](https://man.openbsd.org/tmux#WINDOWS_AND_PANES). Here is a selection:

Command|*emacs(1)*|*vi(1)*|Description
---|---|---|---
begin-selection|C-Space|Space|Start selection
cancel|q|q|Exit copy mode
clear-selection|C-g|Escape|Clear selection
copy-pipe|||Copy and pipe to the command in the first argument
copy-selection-and-cancel|M-w|Enter|Copy the selection and exit copy mode
cursor-down|Down|j|Move the cursor down
cursor-left|Left|h|Move the cursot left
cursor-right|Right|l|Move the cursor right
cursor-up|Up|k|Move the cursor up
end-of-line|C-e|$|Move the cursor to the end of the line
history-bottom|M->|G|Move to the bottom of the history
history-top|M-<|g|Move to the top of the history
middle-line|M-r|M|Move to middle line
next-word-end|M-f|e|Move to the end of the next word
page-down|PageDown|C-f|Page down
page-up|PageUp|C-b|Page up
previous-word|M-b|b|Move to the previous word
rectangle-toggle|R|v|Toggle rectangle selection
search-again|n|n|Repeat the last search
search-backward||?|Search backwards, the first argument is the search term
search-backward-incremental|C-r||Search backwards incrementally, usually used with the `-i` flag to `command-prompt`
search-forward||/|Search forwards, the first argument is the search term
search-forward-incremental|C-s||Search forwards incrementally
search-reverse|N|N|Repeat the last search but reverse the direction
start-of-line|C-a|0|Move to the start of the line

#### Types of option

tmux is configured by setting options. There are several types of options:

* Server options which affect the entire server.

* Session options which affect one or all sessions.

* Window options which affect one or all windows.

* Pane options which affect one or all panes.

* User options which are not used by tmux but are reserved for the user.

Session and window options have both a global set of options and a set for each
session or window. If the option is not present in the session or window set,
the global option is used. Pane options are similar except the window options
are also checked.

When configuring tmux, it is most common to set server options and global
session or window options. This document only covers these.

#### Showing options

Options are displayed using the `show-options` command. The `-g` flag shows
global options. It can show server, session or window options:

* `-s` shows server options:

~~~~
$ tmux show -s
backspace C-?
buffer-limit 50
...
~~~~

* `-g` with no other flags shows global session options:

~~~~
$ tmux show -g
activity-action other
assume-paste-time 1
...
~~~~

* `-g` and `-w` together show global window options:

~~~~
$ tmux show -wg
aggressive-resize off
allow-rename off
...
~~~~

An individual option value may be shown by giving its name to `show-option`.
When an option name is given, it is not necessary to give `-s` or `-w` because
tmux can work it out from the option name. For example, to show the `status`
option:

~~~~
$ tmux show -g status
status on
~~~~

#### Changing options

Options are set or unset using the `set-option` command. Like `show-option`, it
is not necessary to give `-s` or `-w` because tmux can work out it out from the
option name. `-g` is necessary to set global session or window options; for
server options it does nothing.

To set the `status` option:

~~~~
set -g status off
~~~~

Or the `default-terminal` option:

~~~~
set -s default-terminal 'tmux-256color'
~~~~

The `-u` flag unsets an option. Unsetting a global option restores it to its
default value, for example:

~~~~
set -gu status
~~~~

#### Formats

Many options make use of formats. Formats provide a powerful syntax to
configure how text appears, based on various attributes of the tmux server, a
session, window or pane. Formats are enclosed in `#{}` in string options or as
a single uppercase letter like `#F`. This is the default `status-right` with
several formats:

~~~~
$ tmux show -s status-right
status-right "#{?window_bigger,[#{window_offset_x}#,#{window_offset_y}] ,}\"#{=21:pane_title}\" %H:%M %d-%b-%y"
~~~~

Formats are described [in this
document](https://github.com/tmux/tmux/wiki/Formats) and [in the manual
page](https://man.openbsd.org/tmux#FORMATS).

#### Embedded commands

Some options may contain embedded shell commands. This is limited to the status
line options such as `status-left`. Embedded shell commands are enclosed in
`#()`. They can either:

1) Print a line and exit, in which case the line will be shown in the status
   line and the command run at intervals to update it. For example:

   ~~~~
   set -g status-left '#(uptime)'
   ~~~~

   The maximum interval is set by the `status-interval` option but commands may
   also be run sooner if tmux needs. Commands will not be run more than once a
   second.

2) Stay running and print a line whenever needed, for example:

   ~~~~
   set -g status-left '#(while :; do uptime; sleep 1; done)'
   ~~~~

Note that is it not usually necessary to use an embedded command for the date
and time since tmux will expand the date formats like `%H` and `%S` itself in
the status line options. If a command like *date(1)* is used, any `%`s must be
doubled as `%%`.

#### Colours and styles

tmux allows the colour and attribute of text to be configured with a simple
syntax, this is known as the style. There are two places styles appear:

* In options, such as `status-style`.

* Enclosed in `#[]` in an option value, this is called an embedded style (see
  the next section).

A style has a number of terms separated by spaces or commas, the most
useful are:

* `default` uses the default colour; this must appear on its own. The default
  colour is often set by another option, for example for embedded styles in the
  `status-left` option, it is `status-style`.

* `bg` sets the background colour. The colour is also given, for example
  `bg=red`.

* `fg` sets the foreground colour. Like `bg`, the colour is given: `fg=green`.

* `bright` or `bold`, `underscore`, `reverse`, `italics` set the attributes.
  These appear alone, such as: `bright,reverse`.

Colours may be one of `black`, `red`, `green`, `yellow`, `blue`, `magenta`,
`cyan`, `white` for the standard terminal colours; `brightred`, `brightyellow`
and so on for the bright variants; `colour0` to `colour255` for the colours
from the 256-colour palette; `default` for the default colour; or a hexadecimal
RGB colour such as `#882244`.

The remaining style terms are described [in the manual
page](https://man.openbsd.org/tmux#STYLES).

For example, to set the status line background to blue using the `status-style` option:

~~~~
set -g status-style 'bg=blue'
~~~~

#### Embedded styles

Embedded styles are included inside another option in between `#[` and `]`.
Each changes the style of following text until the next embedded style or the
end of the text.

For example, to put some text in red and blue in `status-left`:

~~~~
set -g status-left 'default #[fg=red] red #[fg=blue] blue'
~~~~

Because this is long it is also necessary to also increase the
`status-left-length` option:

~~~~
set -g status-left-length 100
~~~~

Or embedded styles can be used conditionally, for example to show `P` in red if
the prefix has been pressed or in the default style if not:

~~~~
set -g status-left '#{?client_prefix,#[bg=red],}P#[default] [#{session_name}] '
~~~~

#### List of useful options

This is a short list of the most commonly used tmux options, apart from style
options:

Option|Type|Description
---|---|---
`base-index`|session|If set, then windows indexes start from this instead of from 0
`buffer-limit`|server|The maximum number of automatic buffers to keep, the default is 50
`default-terminal`|server|The default value of the `TERM` environment variable inside tmux
`display-panes-time`|window|The time in milliseconds the pane numbers are shown for `C-b q`
`display-time`|session|The time in milliseconds for which messages on the status line are shown
`escape-time`|server|The time tmux waits after receiving an `Escape` key to see if it is part of a longer key sequence
`focus-events`|server|Whether focus key sequences are sent by tmux when the active pane changes and when received from the outside terminal if it supports them
`history-limit`|session|The maximum number of lines kept in the history for each pane
`mode-keys`|window|Whether *emacs(1)* or *vi(1)* key bindings are used in copy mode
`mouse`|session|If the mouse is enabled
`pane-border-status`|window|Whether a status line appears in every pane border: `top` or `bottom`
`prefix`|session|The prefix key, the default is `C-b`
`remain-on-exit`|window|Whether panes are automatically killed when the program running in the exits
`renumber-windows`|session|If `on`, windows are automatically renumbered to close any gaps in the window list
`set-clipboard`|server|Whether tmux should attempt to set the external *X(7)* clipboard when text is copied and if the outside terminal supports it
`set-titles`|session|If `on`, tmux will set the title of the outside terminal
`status`|session|Whether the status line if visible
`status-keys`|session|Whether *emacs(1)* or *vi(1)* key bindings are used at the command prompt
`status-interval`|session|The maximum time in seconds before the status line is redrawn
`status-position`|session|The position of the status line: `top` or `bottom`
`synchronize-panes`|window|If `on`, typing in any pane in the window is sent to all panes in the window - care should be taken with this option!
`terminal-overrides`|server|Any capabilities tmux should override from the `TERM` given for the outside terminal

#### List of style and format options

This is a list of the most commonly used tmux style and format options:

Option|Type|Description
---|---|---
`display-panes-active-colour`|session|The style of the active pane number for `C-b q`
`display-panes-colour`|session|The style of the pane numbers, apart from the active pane for`C-b q`
`message-style`|session|The style of messages shown on the status line and of the command prompt
`mode-style`|window|The style of the selection in copy mode
`pane-active-border-style`|window|The style of the active pane border
`pane-border-format`|window|The format of text that appears in the pane border status line if `pane-border-status` is set
`pane-border-style`|window|The style of the pane borders, apart from the active pane
`status-left-length`|session|The maximum length of the status line left 
`status-left-style`|session|The style of the status line left
`status-left`|session|The format of the text in the status line left
`status-right-length`|session|The maximum length of the status line right 
`status-right-style`|session|The style of the status line right
`status-right`|session|The format of the text in the status line right
`status-style`|session|The style of the status line as a whole, parts may be overridden by more specific options like `status-left-style`
`window-active-style`|window|The style of the default colour in the active pane in the window
`window-status-current-format`|window|The format of the current window in the window list
`window-status-current-style`|window|The style of the current window in the window list
`window-status-format`|window|The format of windows in the window list, apart from the current window
`window-status-separator`|window|The separator between windows in the window list
`window-status-style`|window|The style of windows in the window list, apart from the current window
`window-style`|window|The style of the default colour of panes in the window, apart from the active pane

### Common configuration changes

This section shows examples of some common configuration changes for
`.tmux.conf`.

#### Changing the prefix key

The prefix key is set by the `prefix` option. The `C-b` key is also bound to
the `send-prefix` command in the prefix key table so pressing `C-b` twice sends
it through to the active pane. To change to `C-a`:

~~~~
set -g prefix C-a
unbind C-b
bind C-a send-prefix
~~~~

#### Customizing the status line

There are many options for customizing the status line. The simplest options are:

* Turn the status line off: `set -g status off`

* Move it to the top: `set -g status-position top`

* Set the background colour to red: `set -g status-style bg=red`

* Change the text on the right to the time only: `set -g status-right '%H:%M'`

* Underline the current window: `set -g window-status-current-style 'underscore'`

#### Configuring the pane border

The pane border colours may be set:

~~~~
set -g pane-border-style fg=red
set -g pane-active-border-style 'fg=red,bg=yellow'
~~~~

Each pane may be given a status line with the `pane-border-status` option, for
example to show the pane title in bold:

~~~~
set -g pane-border-status top
set -g pane-border-format '#[bold]#{pane_title}#[default]'
~~~~

#### *vi(1)* key bindings

tmux supports key bindings based on *vi(1)* for copy mode and the command
prompt. There are two options that set the key bindings:

1) `mode-keys` sets the key bindings for copy mode. If this is set to `vi`,
then the `copy-mode-vi` key table is used in copy mode; otherwise the
`copy-mode` key table is used.

2) `status-keys` sets the key bindings for the command prompt.

If either of the `VISUAL` or `EDITOR` environment variables are set to
something containing `vi` (such as `vi`, `vim`, `nvi`) when the tmux server is
first started, both of these options are set to `vi`.

To set both to use *vi(1)* keys:

~~~~
set -g mode-keys vi
set -g status-keys vi
~~~~

#### Mouse copying behaviour

When dragging the mouse to copy text, tmux copies and exits copy mode when the
mouse button is released. Alternative behaviours are configured by changing the
`MouseDragEnd1Pane` key binding. The three most useful are:

1) Do not copy or clear the selection or exit copy mode when the mouse is
released. The keyboard must be used to copy the selection:

~~~~
unbind -Tcopy-mode MouseDragEnd1Pane
~~~~

2) Copy and clear the selection but do not exit copy mode:

~~~~
bind -Tcopy-mode MouseDragEnd1Pane send -X copy-selection
~~~~

3) Copy but do not clear the selection:

~~~~
bind -Tcopy-mode MouseDragEnd1Pane send -X copy-selection-no-clear
~~~~

### Other features

tmux has a large set of features and commands not mentioned in this document,
many allowing powerful scripting. Here is a list of some that may be worth
further reading:

* Alerts: `monitor-activity`, `monitor-bell`, `monitor-silence`,
  `activity-action`, `bell-action` and other options.

* Options for individual session, windows and panes.

* Moving panes with `join-pane` and `break-pane`.

* Sending keys to panes with `send-keys`.

* The command prompt `history-file` option.

* Saved layout strings with `select-layout`.

* Command sequences (separated by `;`): `select-window; kill-window`.

* Configuration file syntax: `{}`, `%if` and so on.

* Mouse key bindings: `MouseDown1Pane` and so on.

* Locking: `lock-command`, `lock-after-time` and other options.

* Capturing pane content with `capture-pane` and piping with `pipe-pane`.

* Linking windows: the `link-window` command.

* Session groups: the `-t` flag to `new-session`.

* Respawing window and panes with `respawn-window` and `respawn-pane`.

* Custom menus with the `display-menu` command and custom prompts with
  `command-prompt` and `confirm-before`.

* Different key tables: `bind-key` and the `-T` flag to `switch-client`.

* Empty panes: the `split-window` with an empty command and `-I` to
  `display-message`.

* Hooks: `set-hook` and `show-hooks`.

* Synchronization for scripts with `wait-for`.
```

## File: Home.md
```markdown
![](https://github.com/tmux/tmux/blob/master/logo/tmux-logo-medium.png?raw=true)

### Welcome to tmux!

tmux is a terminal multiplexer. It lets you switch easily between several
programs in one terminal, detach them (they keep running in the background) and
reattach them to a different terminal.

**Download [tmux 3.6a here](https://github.com/tmux/tmux/releases/download/3.6a/tmux-3.6a.tar.gz)**
([changes in this version](https://raw.githubusercontent.com/tmux/tmux/3.6a/CHANGES)).

See:

* the [getting started guide](Getting-Started);

* [how to install tmux](Installing);

* the [tmux(1) manual page](http://man.openbsd.org/OpenBSD-current/man1/tmux.1);

* and the [README](https://github.com/tmux/tmux/blob/master/.github/README.md).

For support:

* the [FAQ](FAQ);

* the [tmux-users@googlegroups.com mailing list](mailto:tmux-users@googlegroups.com).

Some notes on tmux development and ideas for contributions are [here](Contributing).
```

## File: Installing.md
```markdown
## Installing tmux

### Binary packages

Many platforms provide prebuilt packages of tmux, although these are often out
of date. Details of the commands to discover and install these can be found in
the documentation for the platform package management tools, for example:

Platform|Install Command
---|---
Arch Linux|`pacman -S tmux`
Debian or Ubuntu|`apt install tmux`
Fedora|`dnf install tmux`
RHEL or CentOS|`yum install tmux`
macOS (using Homebrew)|`brew install tmux`
macOS (using MacPorts)|`port install tmux`
openSUSE|`zypper install tmux`

Some thirdparty binary packages are available: [AppImage](Installing#appimage-package) and
[RPMs](Installing#red-hat-enterprise-linux--centos-rpms).

### Prebuilt static binaries

Prebuilt tmux binaries are available from the [tmux-builds](https://github.com/tmux/tmux-builds) repository.
The binaries are built for common Linux and macOS platforms and do not require
additional runtime dependencies.
Refer to the repository for more details and installation instructions.





### From source tarball

tmux requires two libraries to be available:

1. [libevent](https://libevent.org/)

2. [ncurses](https://invisible-island.net/ncurses/ncurses.html)

In addition, tmux requires a C compiler, make, yacc (or bison) and pkg-config.

On most platforms, these are available as packages. This table lists the
packages needed to run or to buld tmux:

Platform|Command|Run Packages|Build Packages
---|---|---|---
Debian|`apt-get install`|`libevent ncurses`|`libevent-dev ncurses-dev build-essential bison pkg-config`
RHEL or CentOS|`yum install`|`libevent ncurses`|`libevent-devel ncurses-devel gcc make bison pkg-config`

If libevent and ncurses are not available as packages, they can be built from
source, see [this section](#building-dependencies).

tmux uses autoconf so it provides a configure script. To build and install
into `/usr/local` using sudo, run:

~~~~
tar -zxf tmux-*.tar.gz
cd tmux-*/
./configure
make && sudo make install
~~~~

To install elsewhere add `--prefix` to configure, for example for `/usr` add
`--prefix=/usr`.

### Building dependencies

If the dependencies are not available, they can be built from source and
installed locally. This is not recommended if the dependencies can be installed
from system packages.

Building requires a C compiler, make, automake, autoconf and pkg-config to be
installed. It is more common to need to build libevent than ncurses.

Full instructions can be found on the project sites but this is a summary of
how to install libevent and ncurses into `~/local` for a single user. To
install system-wide into directories under `/opt` or into `/usr/local`,
substitute the required path for for `$HOME/local` in each case and run `make
install` as root (for example with sudo: `make && sudo make install`).

For libevent:

~~~~
tar -zxf libevent-*.tar.gz
cd libevent-*/
./configure --prefix=$HOME/local --enable-shared
make && make install
~~~~

For ncurses:

~~~~
tar -zxf ncurses-*.tar.gz
cd ncurses-*/
./configure --prefix=$HOME/local --with-shared --with-termlib --enable-pc-files --with-pkg-config-libdir=$HOME/local/lib/pkgconfig
make && make install
~~~~

Then the tmux configure script needs to be pointed to the local libraries
using `PKG_CONFIG_PATH`:

~~~~
tar -zxf tmux-*.tar.gz
cd tmux-*/
PKG_CONFIG_PATH=$HOME/local/lib/pkgconfig ./configure --prefix=$HOME/local
make && make install
~~~~

If ncurses and libevent were installed in different directories rather than all
together in `~/local`, both their `lib/pkgconfig` directories will need to be
in `PKG_CONFIG_PATH`, for example:

~~~~
PKG_CONFIG_PATH=/opt/libevent/lib/pkgconfig:/opt/ncurses/lib/pkgconfig ./configure --prefix=$HOME/local
~~~~

The newly built tmux can be found in `~/local/bin/tmux`.

When tmux is installed locally on Linux, the runtime linker may need to be told
where to find the libraries using the `LD_LIBRARY_PATH` environment variable,
for example:

~~~~
LD_LIBRARY_PATH=$HOME/local/lib $HOME/local/bin/tmux -V
~~~~

And to view the manual page, `MANPATH` must be set:

~~~~
MANPATH=$HOME/local/share/man man tmux
~~~~

Most users will want to configure these in a shell profile, for example in
`.profile` for ksh or `.bash_profile` for bash:

~~~~
export PATH=$HOME/local/bin:$PATH
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
export MANPATH=$HOME/local/share/man:$MANPATH
~~~~

### From version control

Building tmux from Git has the same dependencies as building from tarball plus
also autoconf and automake. Building is the same as from a tarball except first
the configure script must be generated. To install into `/usr/local`:

~~~~
git clone https://github.com/tmux/tmux.git
cd tmux
sh autogen.sh
./configure
make && sudo make install
~~~~

### Configure options

tmux provides a few configure options:

Option|Description
---|---
`--enable-debug`|Build with debug symbols
`--enable-static`|Create a static build
`--enable-utempter`|Use the utempter library if it is installed
`--enable-utf8proc`|Use the utf8proc library if it is installed

Note that `--enable-static` may require static libraries to be installed, for
example on RHEL or CentOS the `glibc-static` package is required.

### Common problems

#### configure says: `libevent not found` or `ncurses not found`

The libevent library or its headers are not installed. Make sure the
appropriate packages are installed (some platforms split libraries from headers
into a `-dev` or `-devel` package).

#### configure says: `must give --enable-utf8proc or --disable-utf8proc`

macOS's builtin UTF-8 support is very poor, so it is best to use the
[utf8proc](https://juliastrings.github.io/utf8proc/) library if possible. Once
it is installed, pass `--enable-utf8proc` to configure.

To force tmux to build without utf8proc, use `--disable-utf8proc`.

#### tmux won't run from `~/local`

On Linux, make sure `LD_LIBRARY_PATH` is set, or try a static build instead
(give `--enable-static` to configure).

#### `autogen.sh` complains about `AM_BLAH` or `PKG_MODULES`

Make sure pkg-config is installed.

#### configure says: `C compiler cannot create executables`

Either no C compiler (gcc, clang) is installed, or it doesn't work - check
there is nothing stupid in `CFLAGS` or `CPPFLAGS`.

#### The build fails with an error about "conflicting type for `forkpty`"

For static builds, make sure a static libc is available. On RHEL or CentOS the
`glibc-static` package is required.

### AppImage package

Instructions and scripts on building an AppImage package for tmux are available
[from Nelson Enzo here](https://github.com/nelsonenzo/tmux-appimage). Prebuilt
AppImage packages are also available
[here](https://github.com/nelsonenzo/tmux-appimage/releases).

### Docker script

A [Docker](https://www.docker.com/) install script is available
[here](https://github.com/ferryman0608/Dockerfile-tmux).

### Red Hat Enterprise Linux / CentOS RPMs

The tmux packages available from the main repositories are often quite out of
date, especially for long-term support distributions. RPMs for newer tmux
versions can be obtained [from here](http://galaxy4.net/repo/).

For example to set up a repository and install on RHEL8:

~~~~
sudo yum install http://galaxy4.net/repo/galaxy4-release-8-current.noarch.rpm
sudo yum install tmux
~~~~

Or to install an RPM directly on RHEL6:

~~~~
sudo rpm -ivh http://galaxy4.net/repo/RHEL/6/x86_64/tmux-3.1b-2.el6.x86_64.rpm
~~~~

The repository method is recommended to automatically receive future package
updates. See [this page](https://anni.galaxy4.net/?page_id=39) for more
details.
```

## File: Modifier-Keys.md
```markdown
## Modifier keys

**As of tmux 3.5, this document is out of date; tmux now defaults to supporting
`extended-keys` in a way similar to xterm.**

Terminals support three modifier keys: `Ctrl`, `Meta` (usually `Alt` on modern
keyboards) and `Shift`, but which keys support which modifiers and how they are
represented to tmux varies between terminals. This document gives an overview
of how these keys work and some help on how to troubleshoot them.

### What terminal keys look like

Keys are sent to tmux by terminals in three forms:

- Normal ASCII or UTF-8 keys are sent as themselves (`a` is `a`).

- `Ctrl` with ASCII keys are sent using the ASCII control characters (`C-a` is
  ASCII 1).

- `Meta` prefixes a key with a single ASCII `ESC` character (ASCII 27,
  sometimes written `^[`, `\033`, `\e` or `\E`). So `M-a` is `^[a`.

- Function keys are sent as a special sequence prefixed by ASCII `ESC`. The
  exact sequences for different keys varies.

It is important to note:

- The keys available to terminal applications like tmux are not necessarily the
  same as those available to the terminal itself, for example *X(7)* programs
  have a much larger range of keys available than can be passed to terminal
  applications.

- Terminal key sequences are not related to *X(7)* key symbols (used by
  *xmodmap(1)* or *xev(1)*) or those used by the Linux console.

### How tmux describes keys with modifiers

tmux describes keys with modifiers with one of three prefixes:

- `C-` for `Ctrl` keys;

- `M-` for `Meta` keys;

- `S-` for `Shift` keys.

These may be combined, so `Ctrl` and `Meta` and `Left` is `C-M-Left`.

Many keys with `Shift` have an alternative name, tmux uses this if it exists.
So there is no `S-a` - it is just in uppercase: `A`. Similarly, `S-Tab` is
`BTab`. The `S-` prefix is used for some function keys which have only one
form, for example `S-Left` and `S-Right`.

### Limitations of `Ctrl` keys

There are only 32 ASCII control characters, so in most terminals there are only
32 `Ctrl` keys:

- `C-@` is ASCII 0;

- `C-a` to `C-z` are ASCII 1 to ASCII 26;

- `C-[`, `C-\`, `C-]`, `C-^` and `C--` are ASCII 27 to 31.

Some of these are used for multiple keys, including:

- `C-@` is also `C-Space`;

- `C-[` is also `Escape`;

- `C-i` is also `Tab`;

- `C-m` is also `Enter`;

- `C--` is also `C-_`;

- `C-^` is also `C-/`.

This means that it is not possible to bind `C-@` and `C-Space` to different
things and on most terminals it is not possible to bind some keys like `C-!` or
`C-1` at all.

A few terminals have a feature that allows these keys to be used, see [this
section](Modifier-Keys#extended-keys).

### Limitations of `Shift` keys

Most ASCII keys have a `Shift` form marked on the keyboard which is sent when
the key is pressed with `Shift`. For example on a UK QWERTY keyboard, pressing
`S-1` will send `!`. tmux doesn't know the keyboard layout, so it treats `!` as
`!` not `S-1`. There is no way to express the key `S-1` - `!` is used instead.

`Shift` modifiers and the `S-` prefix are mostly reserved for function keys
such as `S-F1` or `S-Left`.

### Limitations of UTF-8 keys

UTF-8 keys do not have a `Ctrl` or `Shift` form, so they will not work with
those modifiers. Because `Meta` works by sending a `^[` prefix, UTF-8
characters can work with a `Meta` modifier.

### The escape key

Because the `Escape` key is `^[` which is also the prefix used for `Meta` and
for function keys, tmux needs to work out whether a single `^[` is an `Escape`
key or part of a longer sequence. It does this using a timer:

- When the `^[` byte is seen, tmux starts the timer;

- If more data comes in before the timer runs out, tmux can work out whether
  the `^[` is part of a longer sequence;

- Or if the timer expires, the key is `Escape`.

This is why there can be a delay between pressing `Escape` and tmux passing the
key on to an application inside. The length of the timer is controlled by the
`escape-time` option, the default is 500 milliseconds (half a second).

### Common function keys

The sequences that terminals send to tmux for function keys can vary, but for
common keys tmux can get the sequences from *terminfo(5)*.

This means that although they may differ between terminals, they usually work.
For example `Home` is in the `khom` capability which differs between tmux and
*xterm(1)*. The `tput` or `infocmp` commands can be used to inspect
*terminfo(5)* capabilities.

~~~~
$ tput -Ttmux khom|cat -v; echo
^[[1~
$ tput -Txterm khom|cat -v; echo
^[OH
~~~~

Because tmux can read `khom`, it can correctly recognise the sequences for this
key. In addition, tmux has builtin support for a few common sequences.

### Modifiers and function keys

Support for modifiers and function keys, such as `C-F1` or `C-S-Left`, is not
always present and these are often the keys that cause most trouble.

*xterm(1)* offers a descriptive sequence for these keys which many other
terminals also use, this includes a number in the key sequence for the
modifier, so `C-Left` is `^[[1;5D` where 5 means `Ctrl` and:

- 2 is `Shift`;
- 3 is `Meta`;
- 4 is `Shift` and `Meta`;
- 6 is `Shift` and `Ctrl`;
- 7 is `Meta` and `Ctrl`;
- 8 is `Shift` and `Meta` and `Ctrl`.

These forms are only used for function keys supported by modern terminals -
keys which were offered on traditional hardware terminals typically still use
their original sequences.

All tmux versions recognise this form of key, and tmux has sent it to
application running inside by default since tmux 2.4. In older versions, the
`xterm-keys` option must be enabled:

~~~~
set -g xterm-keys on
~~~~

### Extended keys

A few terminals have support for extended key sequences, this allows tmux to
recognise some keys that are not previously available, such as `C-1` and the
other control keys mentioned in [this
section](Modifier-Keys#limitations-of-ctrl-keys)). See [this
document](http://www.leonerd.org.uk/hacks/fixterms/) for a technical
description of the key encoding.

tmux has support for this beginning with tmux 3.2.

For this to work, three things must be in place:

1) The terminal must support it: *xterm(1)*,
   [mintty](https://mintty.github.io/) and [iTerm2](https://www.iterm2.com/)
   currently support this. iTerm2 requires this option to be set in the
   profile:

   <img src="images/iterm2_csi_u.png" align="center" width=292 height=132>

2) tmux must be told to turn it on:

   ~~~~
   set -s extended-keys on
   ~~~~

3) tmux must recognise that the terminal supports it. tmux will automatically
   detect newer versions of these three terminals, but if it does not then the
   `terminal-features` option can also be modified to enable it manually:

   ~~~~
   set -as terminal-features 'xterm*:extkeys'
   ~~~~

Once this feature is enabled, tmux will both recognise extended keys for its
own key bindings and forward them to applications inside if they ask for them.
For example, sending the escape sequnce to turn it on then running *cat(1)* and
pressing `C-1` will show:

~~~~
$ printf '\033[>4;1m'
$ cat
^[[49;5u
~~~~

### Why a key might not work

In order for a key to work, two things must be true:

1) tmux and the terminal it is running in must agree on the sequence sent for
   the key; and

2) tmux and the application running inside must agree on the sequence sent for
   the key.

The sequence the terminal sends to tmux and the sequence tmux sends to the
application inside don't have to be the same - it is tmux's job to translate.
But if either tmux and the terminal or tmux and the application do not agree,
the key will not be recognised.

### Seeing what is sent for a key

The easiest way to see what is being sent for a key is to use *cat(1)* at the
shell prompt. For example, running *cat(1)* and pressing `C-Left` in tmux shows:

~~~~
$ cat
^[[1;5D
~~~~

### Troubleshooting steps

If a key is not working, the first thing to do is work out if tmux itself is
recognizing the key. The easiest way to do this is to try to bind it, for
example by running tmux then:

~~~~
$ tmux bind -n TheKey lsk
~~~~

Then if pressing the key shows the `list-keys` output, tmux is recognizing the
key. Steps if it does not recognise it are in the next section; and if it does
are in the following.

#### tmux is not recognizing the key

If a tmux key binding doesn't work then:

1) Check something is being sent for the key outside tmux. If nothing appears
   in *cat(1)* when the key is pressed, the terminal is not sending the key.
   Perhaps the terminal is using it itself or a window manager is using it
   instead.

2) For keys with modifiers, make sure the sequence sent for a key outside tmux
   is different with and without the modifier. If `C-TheKey` and `TheKey` show
   the same thing with *cat(1)*, tmux can't tell the difference - either the
   terminal doesn't support the key, or needs additional configuration.

3) Make sure `TERM` is correct. tmux gets some information on keys from `TERM`.
   Check the terminal documentation to see what `TERM` should be set to outside
   tmux.

4) If none of these work, open an issue
[here](https://github.com/tmux/tmux/issues)

#### tmux is recognizing the key

If a tmux key binding works, but applications inside tmux are not recognizing
the key:

1) Check something is shown for the key inside tmux with *cat(1)*. If nothing
   is shown, make sure there are no bindings for the key in the root table.

2) If *cat(1)* shows some output, make sure `TERM` is correct inside tmux. If
   it is `screen` or `screen-256color`, try changing to `tmux` or
   `tmux-256color` if available. Check if they are available with *infocmp(1)*:

   ~~~~
   $ infocmp -x tmux-256color
   #       Reconstructed via infocmp from file: /usr/share/terminfo/t/tmux-256color
   tmux-256color|tmux with 256 colors,
   ...
   ~~~~

   And if so, set `default-terminal` in `.tmux.conf`:

   ~~~~
   set -g default-terminal tmux-256color
   ~~~~

3) If `TERM` is correct and *cat(1)* is showing output when the key is pressed,
   the problem is probably with the application. Check if its documentation has
   any information on how to configure key bindings.

### The number keypad

In most terminals, the number keypad sends either numbers (`1`, `2` and so on)
or function keys (`Home`, `Up` and so on). With either of these, tmux cannot
tell that the keys are any different from the normal number keys or function
keys.

Some terminals additionally allow tmux to put the keypad into "application
mode", which allows it to recognise the keys separately so they can be used as
key bindings. To check if a terminal supports this, send the `smkx` capability
with *tput(1)* then look at the `1` key on the keypad with *cat(1)*:

~~~~
$ tput smkx
$ cat
^[Oq
~~~~

If this shows `^[Oq` then this mode is supported. If it shows something else,
it is not supported or the terminal needs additional configuration to enable
it.
```

## File: Recipes.md
```markdown
## Configuration file recipes

This file lists some useful configuration file snippets to control tmux
behaviour.

### Create new panes in the same working directory

This changes the default key bindings to add the `-c` flag to specify the
working directory:

~~~~
bind '"' split-window -c "#{pane_current_path}"
bind % split-window -hc "#{pane_current_path}"
bind c new-window -c "#{pane_current_path}"
~~~~

### Prevent pane movement wrapping

This stops the pane movement keys wrapping around at the top, bottom, left and
right.

Requires tmux 2.6 or later.

~~~~
bind -r Up if -F '#{pane_at_top}' '' 'selectp -U'
bind -r Down if -F '#{pane_at_bottom}' '' 'selectp -D'
bind -r Left if -F '#{pane_at_left}' '' 'selectp -L'
bind -r Right if -F '#{pane_at_right}' '' 'selectp -R'
~~~~

### Send `Up` and `Down` keys for the mouse wheel

Some terminals do this by default when an application has not enabled the mouse
itself. This does the same in tmux (the `mouse` option must also be `on`):

~~~~
bind -n WheelUpPane if -Ft= "#{mouse_any_flag}" "send -M" "send Up"
bind -n WheelDownPane if -Ft= "#{mouse_any_flag}" "send -M" "send Down"
~~~~

An alternative is to only send the keys when in the alternate screen:

~~~~
bind -n WheelUpPane {
	if -F '#{||:#{pane_in_mode},#{mouse_any_flag}}' {
		send -M
	} {
		if -F '#{alternate_on}' { send-keys -N 3 Up } { copy-mode -e }
	}
}
bind -n WheelDownPane {
	if -F '#{||:#{pane_in_mode},#{mouse_any_flag}}' {
		send -M
	} {
		if -F '#{alternate_on}' { send-keys -N 3 Down }
	}
}
~~~~

### Make `C-b w` binding only show the one session

This makes the `C-b w` tree mode binding only show windows in the attached
session.

~~~~
bind w run 'tmux choose-tree -Nwf"##{==:##{session_name},#{session_name}}"'
~~~~

### Create a new pane to copy

This opens a new pane with the history of the active pane - useful to copy
multiple items from the history to the shell prompt.

Requires tmux 3.2 or later.

~~~~
bind C {
	splitw -f -l30% ''
	set-hook -p pane-mode-changed 'if -F "#{!=:#{pane_mode},copy-mode}" "kill-pane"'
	copy-mode -s'{last}'
}
~~~~

### C-DoubleClick to open *emacs(1)*

C-DoubleClick on a word to open *emacs(1)* in a popup (handles `file:line`).

Requires tmux 3.2 or later.

~~~~
set -g word-separators ""
bind -n C-DoubleClick1Pane if -F '#{m/r:^[^:]*:[0-9]+:,#{mouse_word}}' {
	run -C 'popup -w90% -h90% -E -d "#{pane_current_path}" "
		x=\$(echo "#{mouse_word}"|awk -F: \"{print \\\"+\\\"\\$2,\\$1}\")
		emacs "\$x"
	"'
} {
	run -C 'popup -w90% -h90% -E -d "#{pane_current_path}" "
		emacs "#{mouse_word}"
	"'
}
~~~~

### Change shortcut keys in tree mode

This assigns the shortcut keys by the window index for the current session
rather than by line number and uses `a` to `z` for higher numbers rather than
`M-a` to `M-z`. Note that this replaces the existing uses for the `a` to `z`
keys.

~~~~
bind w run -C { choose-tree -ZwK "##{?##{!=:#{session_name},##{session_name}},,##{?window_format,##{?##{e|<:##{window_index},10},##{window_index},##{?##{e|<:##{window_index},36},##{a:##{e|+:##{e|-:##{window_index},10},97}},}},}}" }
~~~~
```