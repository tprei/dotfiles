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

## Include in the brief

Downstream implementers run on smaller, faster models that need concrete code specifications. Never leave architecture, interface design, or file placement open to interpretation.

- Goal and exact expected end state.
- Exact file paths to create, modify, or remove.
- Concrete types, interfaces, schemas, and function signatures with typed parameters and return types.
- Step-by-step code changes showing exact logic, imports, and replacement snippets.
- Full enumeration of affected call sites, re-exports, and caller updates.
- Decisions already made that must be preserved.
- Explicit error handling, validation checks, and edge cases.
- Constraints, invariants, and non-goals (no fallbacks, no backwards-compatibility shims, no lint suppressions).
- Ordered, testable implementation slices.
- Concrete verification commands and expected outputs.
- Real blockers or unresolved questions.

## Output style

Write prescriptive technical instructions that an implementer can execute directly. Be concrete and specific. Provide the exact code changes, types, and file targets needed for the change.
