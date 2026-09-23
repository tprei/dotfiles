---
name: write-handoff
description: Produce a detailed implementation brief from the current discussion. Use when handing work to another pass, thread, or agent and you need a direct, actionable technical brief without process narration.
---

# Write handoff

Return the brief in chat. Don't write files, narrate process, or mention which agent or model produced it. Separate confirmed facts from assumptions and open questions.

The reader is a smaller model that must not choose architecture, interfaces, or file placement. Include:
- goal and exact end state
- the domain concepts and bounded contexts involved, in the domain's language
- exact paths to create, modify, or remove
- full types, schemas, and typed signatures
- step-by-step code changes with imports and replacement snippets
- every affected call site and re-export
- decisions already made that must hold
- error handling, validation, and edge cases
- constraints and non-goals: no fallbacks, compatibility shims, or lint suppressions
- ordered, testable slices
- verification commands with expected output
- real blockers and open questions

Write prescriptive instructions an implementer can execute directly.
