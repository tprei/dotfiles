---
allowed-tools: Bash(git add:*), Bash(git commit:*), Bash(git ls-files:*), Bash(rg:*), Bash(git:*), Glob, Grep, Read, Edit, MultiEdit, Write, WebFetch, TodoWrite, WebSearch, mcp__repomix__pack_codebase, mcp__repomix__pack_remote_repository, mcp__repomix__attach_packed_output, mcp__repomix__read_repomix_output, mcp__repomix__grep_repomix_output, mcp__repomix__file_system_read_file, mcp__repomix__file_system_read_directory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: Commit only the changes I ask for; if they are not a clean logical commit, explain why and do not force it
argument-hint: "[what-to-commit]"
---

Review the current git changes and decide what, if anything, should be committed.

Additional guidance about what to commit: $@

Requirements:
- Treat the extra guidance above as the primary scope filter.
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
