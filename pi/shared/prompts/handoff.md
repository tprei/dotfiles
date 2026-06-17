---
description: Produce a detailed implementation brief from the current discussion
argument-hint: [FOCUS="<optional focus or extra constraints>"]
---

Use everything established in this conversation, including conclusions already reached and any files, diffs, docs, plans, or references already examined, to produce a detailed implementation brief for the next coding pass.

Requirements:

- Return the brief directly in chat. Do not write, save, or update any file.
- Output only the brief itself. No preamble, no explanation of what you are doing, and no markdown code fence around the whole response.
- Do not mention that this came from a handoff, another agent, a prior assistant, a model, or an LLM.
- Do not narrate process. Write as direct technical instructions that can be acted on immediately.
- Be concrete and specific. Prefer exact files, modules, functions, commands, and validation steps when they are known.
- If something is still uncertain, separate confirmed facts from assumptions instead of blurring them together.

Include, when relevant:

- The goal and expected end state
- Relevant background from the discussion
- Decisions already made and conclusions that should be preserved
- The current state of the code or repo as it matters for the task
- Exact areas to inspect or modify
- An ordered implementation plan
- Constraints, invariants, and non-goals
- Edge cases, risks, and failure modes to watch for
- Validation steps, tests, and commands to run
- Any unresolved questions that genuinely block confident execution

Keep the brief detailed in terms of what to do, but avoid filler.

Additional focus or constraints from the slash command invocation:

$FOCUS
