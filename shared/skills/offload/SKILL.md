---
name: offload
description: Run a repo's declared tasks through the off CLI on Sprite workers. Use when a repo has an offload.toml, or before running heavy tests, builds, typechecks, or soak runs. Also use when the user says "offload X".
---

# Offload

`off` runs a repo's declared tasks on locked-down Sprite workers. For heavy work, run a declared task with `off run` instead of its command.

Use when the repo's git top level has `offload.toml`, or before heavy tests, builds, typechecks, or soak runs in that repo.

## Workflow

1. Run `off plan` once, from inside the repo. It makes no network calls. It lists each task with its `where`, `shards`, `timeout`, and `run` command. A parallel task shows its step labels in the run column instead.
2. For any listed task, run `off run <task>` instead of its command. Tasks with `where = "local"` also go through `off run`. They run on this machine in the repo root and return the command's exit code.
3. Pass extra arguments after `--`: `off run <task> -- <args>`. They are shell-quoted and appended to the task command. A parallel task takes none; `off` rejects them.
4. Shards are automatic. Sprite tasks with `shards` above 1 run in parallel on that many workers, and output lines get an `[i/n]` prefix. The exit code is that of the first failing shard, in shard order. Do not start shards yourself. A parallel task runs its steps at once; each output line gets a `[label]` prefix, and each step ends with a `[label] exited N` line. Its exit code is that of the first failing step, in declared order.
5. Before a Sprite run, `off` syncs the files `git ls-files -co --exclude-standard` lists to the worker, so uncommitted edits and new files are tested. Anything git ignores, and `.git` itself, is not synced. During a run, network access is limited to the `egress` domains in `offload.toml`.
6. A worker is built from `[setup]` the first time it is used, and again after a change to `[setup]` or to its `inputs` files. Setup sees only the `inputs` files. Expect that run to be slow.
7. Sprite tasks pull their `artifacts` paths back after the run to `~/.local/state/off/artifacts/<repo>/<run_id>/<shard>/` (under `$XDG_STATE_HOME/off` when that is set). A missing path is a warning, not a failure.
8. The user can follow the live log: `off watch RUN_ID [--shard N]` follows a shard's log in any terminal, and `off run` opens a Tern session per Sprite shard only from an interactive terminal, so agent shells never get one.
9. `off exec -- <command>` runs a test, build, lint or typecheck command no task declares, on a Sprite worker, with `--timeout` (default 30m). Use it only when the user asks to offload something no task covers. It refuses anything else with exit 64, before running it: run it locally.

## Exit codes

- `64` with `off: refusing to offload`: `off exec` refused the command before starting a worker. Run it locally.
- Any other non-zero code not listed below is the task's own exit code. Read the log at the path `off run` prints, then fix the cause or report it. Do not rerun it unchanged. For a parallel task, the `[label] exited N` lines name the failing step.
- `124`: the task timed out. Read the log to see where it stopped. Do not rerun it unchanged. Changing `timeout` means editing `offload.toml`, which needs the user.
- `125`: an off or infrastructure error. Read the `off: error: <msg>` line on stderr. Retry once only if the message says the worker was busy or unreachable. A `lost the task` message means off already retried, so report it instead of retrying. Otherwise stop and report the message.
- `130`: the run was interrupted, and off stopped the remote task. Don't retry unless the user asks.

## Rules

- Never call `sprite` directly. `off` owns worker creation, network and privilege policy, and sync.
- Never edit `offload.toml` without the user. If no task covers a test, build, lint or typecheck command the user wants offloaded, use `off exec`. Quick commands (versions, file reads, git) always run locally.
