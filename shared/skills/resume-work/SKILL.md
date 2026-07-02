---
name: resume-work
description: Resume an ongoing workstream by surfacing recent repo state and next steps. Use when picking up where work left off, onboarding to active repo work, or summarizing what was just done before continuing.
---

# Resume work

Use this skill when the user wants to continue an in-progress effort and first needs a crisp summary of recent state and next steps.

## Workflow

1. Inspect recent repo history.
   - Check recent `git log` entries.
   - Check any changelog files the repo actually uses.
2. Inspect active planning artifacts.
   - Read relevant `docs/` plans or other current planning notes when they exist.
3. Inspect current repo state.
   - Look for pending diffs or other obvious in-flight work that changes the next-step picture.
4. Summarize before acting.

## Output

Return a compact TODO list covering:
- what was recently done
- what is next
- any blockers, assumptions, or missing context

Then confirm the next-step goal before making further changes when the direction is not already explicit.
