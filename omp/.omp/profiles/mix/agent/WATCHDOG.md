# Watchdog notes (mix profile)

The implementer is a fast, small-context model (GLM-5.2) executing a plan from a stronger planner. A cheap reviewer is valuable precisely because cross-model review catches what the implementer misses. Especially watch for:

- Edits that miss callsites — the implementer may not have re-searched after a rename. Flag any symbol rename that did not update every reference.
- Invented APIs or imports — small-context models sometimes hallucinate package or symbol names. Verify unfamiliar imports resolve against the real codebase.
- Half-applied edits — when the implementer was near its context limit it may have truncated a change. Check that each edit landed completely and the file still parses.
- Dropped scope — confirm every todo item was actually addressed, not just the early ones before context pressure built.
- Missed edge cases in error, IO, and concurrency paths the planner called out.
- Work that should have been delegated to a subagent but was done inline, bloating the main context.
