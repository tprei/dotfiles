---
description: Review pending git changes, isolate a safe commit scope, and delegate commit work to the git-commit-specialist agent when available.
argument-hint: "[what-to-commit]"
---

Treat any slash-command arguments or extra user guidance as the primary scope filter.

If a dedicated `git-commit-specialist` agent or subagent is available, delegate this workflow to exactly one of them and wait for the result. If the current product requires an explicit launch syntax or agent name, use the local equivalent.

Whether delegated or done directly, follow this workflow:

- Inspect `git status --short`, staged diff, and unstaged diff.
- Commit only the changes that match the requested scope.
- If needed, stage or unstage files intentionally so the commit contains only the desired logical change.
- Do not blindly commit everything together.
- If the requested scope is mixed with unrelated, risky, partial, or ambiguous changes, do not force a commit; explain what should be split out first.
- If there is a clearly self-contained, safe commit matching the requested scope, make it.
- Write a concise, contextual commit message.
- Update changelog/release notes only if this repo actually uses them and the current change warrants it.
- After committing, show the commit hash and summary.
- If nothing should be committed yet, do nothing except explain why.
