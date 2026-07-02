---
name: write-handoff
description: Produce a detailed implementation brief from the current discussion. Use when handing work to another pass, thread, or agent and you need a direct, actionable technical brief without process narration.
---

# Write handoff

Use this skill when the user wants a handoff brief, implementation brief, or a direct continuation note for the next coding pass.

## Requirements

- Return the brief directly in chat.
- Do not write or update files.
- Do not narrate process.
- Do not mention that the brief came from another agent, prior assistant, or model.
- Keep confirmed facts separate from assumptions or open questions.

## Include when relevant

- goal and expected end state
- repo or code state that matters
- files, modules, functions, or commands to inspect
- decisions already made that must be preserved
- ordered implementation steps
- constraints, invariants, and non-goals
- edge cases, risks, and failure modes
- validation steps
- real blockers or unresolved questions

## Output style

Write direct technical instructions that can be acted on immediately. Be concrete, specific, and terse.
