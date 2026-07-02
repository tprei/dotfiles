---
name: prepare-context
description: Build focused repo context before planning or implementation. Use when starting exploration or planning for a change and you need to map the smallest relevant set of files from git state, repo search, and targeted reads.
---

# Prepare context

Use this skill before planning or implementation when the relevant code surface is not already clear.

If recent conversation already includes the key files, excerpts, or confirmed entry points, skip the workflow and continue with that existing context.

## Workflow

1. Determine the scope.
   - Treat any extra user guidance as the scope.
   - If the scope is still unclear, ask for a short focus description.
2. Discover entry points.
   - Start with `git diff --name-only` and `git diff --cached --name-only`.
   - If there are no relevant changes, ask for a file or directory entry point.
3. Expand to nearby files.
   - Use `rg --files` in the same directory.
   - Use `rg -n` to find callers, references, imports, exports, and nearby types.
   - Include config, schema, and docs files only when they shape the behavior under investigation.
4. Prune aggressively.
   - Exclude generated files, build outputs, vendored code, and broad unrelated directories.
   - Include tests only when they define behavior, cover the change directly, or the user asked for them.
5. Read focused context.
   - Prefer targeted sections for very large files.
   - Capture why each file matters, what symbols or flows matter, and any open questions.

## Output

Return a compact context brief with:
- scope
- selected files
- why each file matters
- missing neighbors or open questions

End with a short line stating that context is prepared and how many files were included.
