---
name: agy-advisor
description: Ask the local agy CLI (pinned Gemini flash model) for a second opinion on demand. Use when the user explicitly wants an agy or Gemini review, sanity check, or outside take on a diff, plan, or question.
---

# agy advisor

Pipe a prompt through the local `agy` CLI and return its answer.

Use only when the user explicitly asks for an `agy`, Gemini, or second-opinion review of a diff, plan, design, or question. Never run it automatically, speculatively, from hooks, or as an unrequested step.

1. Build one lean prompt. Inline all reviewed content: the advisor runs in an empty directory with no file access. Batch questions; never loop, poll, or fan out.
2. Run `scripts/agy-review.sh [prompt-file]` from this skill's directory, or pipe the prompt on stdin with no arguments.
3. Exit 0: the answer is on stdout. Otherwise report stderr verbatim and don't retry.

| Code | Meaning |
|------|---------|
| 0 | Answer on stdout |
| 1 | Advisor failure: `agy` non-zero exit, non-SUCCESS status, denial (`denied_actions` non-empty), empty, truncated, or unparseable output. Detail on stderr |
| 64 | Usage error: multiple arguments, unreadable or directory prompt file, empty prompt, or no piped input on a terminal |

Calls share the interactive Gemini quota. Content persists in agy history, so never send secrets.
