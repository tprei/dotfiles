---
name: agy-advisor
description: Ask the local agy CLI (pinned Gemini flash model) for a second opinion on demand. Use when the user explicitly wants an agy or Gemini review, sanity check, or outside take on a diff, plan, or question.
---

# agy advisor

Pipe a prompt through the local `agy` CLI and return the advisor's answer as plain text.

## When to use

- The user explicitly asks for an `agy`, Gemini, or second-opinion review or sanity check.
- The user wants an outside-model take on a diff, plan, design, or question.
- The user wants to cross-check finished work with another model before proceeding.

## Instructions

1. Invoke on demand only, when the user asks for it; never run this skill automatically, speculatively, from hooks, or as an unrequested step in another workflow.
2. Write the prompt to a temporary file or prepare it on stdin; keep it lean because every call draws from the same pool as the interactive Gemini session. Inline all reviewed content into the prompt text itself: the advisor runs in an empty directory with no access to your files.
3. Call the runner: `scripts/agy-review.sh [prompt-file]` from this skill's directory, passing the prompt file path as the only argument, or pipe the prompt text on stdin with no arguments.
4. Read the advisor's answer from stdout when the exit code is 0.
5. On a non-zero exit, read the status, denial, or error text on stderr and report it verbatim to the user; do not retry automatically.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success: the advisor response is on stdout |
| 1 | Advisor failure: `agy` exited non-zero, returned a non-SUCCESS status, hit a denial (`denied_actions` non-empty), returned an empty or truncated response, or produced unparseable output; detail is on stderr |
| 64 | Usage error: more than one argument, unreadable prompt file, directory as prompt file, empty prompt, or no piped input on a terminal |

## Quota

Script calls share the interactive Gemini quota pool, so batch questions into a single lean prompt and never loop, poll, or fan out repeated calls. Reviewed content persists in agy conversation history, so do not send secrets.
