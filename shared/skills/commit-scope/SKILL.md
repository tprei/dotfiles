---
name: commit-scope
description: Isolate and commit a safe logical change. Use when the user asks to commit current work, split commit scope, or safely stage only the relevant files before delegating to the git-commit-specialist workflow.
---

# Commit scope

User guidance is the primary scope filter.

1. Inspect `git status --short`, the staged diff, and the unstaged diff.
2. Stage only changes in scope; keep unrelated or risky changes out.
3. If the scope is tangled with partial or ambiguous work, don't force a commit.
4. Delegate to `git-commit-specialist` when available; otherwise commit with a concise why-focused message.

Output: the commit hash and a one-line summary, or why nothing was committed and what must be separated first.
