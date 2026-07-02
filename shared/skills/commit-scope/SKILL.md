---
name: commit-scope
description: Isolate and commit a safe logical change. Use when the user asks to commit current work, split commit scope, or safely stage only the relevant files before delegating to the git-commit-specialist workflow.
---

# Commit scope

Use this skill when the user asks to commit changes and the correct scope needs to be isolated deliberately.

Treat any extra user guidance as the primary scope filter.

## Workflow

1. Inspect `git status --short`, staged diff, and unstaged diff.
2. Commit only the changes that match the requested scope.
3. Stage or unstage intentionally so unrelated or risky changes stay out.
4. Do not force a commit if the requested scope is mixed with partial or ambiguous work.
5. If a dedicated `git-commit-specialist` agent is available, delegate the commit workflow to it.
6. Otherwise create the commit directly with a concise message focused on the why.

## Output

- If a safe commit was made, return the commit hash and a short summary.
- If nothing should be committed yet, explain why and what must be separated first.
