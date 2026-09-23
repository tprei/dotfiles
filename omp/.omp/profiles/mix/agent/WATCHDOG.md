# Watchdog notes (mix profile)

The implementer is a small-context model (GLM-5.3) executing a stronger planner's plan. Cross-model review catches what it misses. Watch for:

- Renames that missed call sites.
- Hallucinated imports or APIs. Check that unfamiliar ones resolve in the codebase.
- Edits truncated near the context limit. Check each landed fully and the file parses.
- Dropped todos, especially later ones.
- Missed edge cases in error, IO, and concurrency paths the planner named.
- Work done inline that should have gone to a subagent.
