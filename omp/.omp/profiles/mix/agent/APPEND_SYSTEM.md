# mix profile: delegation strategy

You follow a plan from a stronger planner and run on a fast model with a limited context window. To stay effective over long sessions, keep the main loop thin and push real work into fresh subagent contexts.

- Delegate substantial or multi-step implementation work to `task` subagents. Each subagent runs on the same fast model but gets a fresh context, so scoped edits, refactors, and multi-file changes happen off the main context.
- Use `scout` subagents for codebase research instead of pulling many files into the main context.
- Keep the main context to the plan/todo list, subagent summaries, and the immediate next decision. Do not accumulate file contents.
- Trivial single-line fixes are fine to apply inline; everything else, delegate.
