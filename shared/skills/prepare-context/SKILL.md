---
name: prepare-context
description: Build focused repo context before planning or implementation. Use when starting exploration or planning for a change and you need to map the smallest relevant set of files from git state, repo search, and targeted reads.
---

# Prepare context

Skip this if the conversation already has the key files and entry points.

1. Scope: user guidance defines it. If unclear, ask for a one-line focus.
2. Entry points: `git diff --name-only` and `git diff --cached --name-only`. With no relevant changes, ask for a file or directory.
3. Expand: `rg --files` in the same directory; `rg -n` for callers, references, imports, exports, and nearby types. Add config, schema, and docs only when they shape the behavior.
4. Prune: drop generated, build, vendored, and unrelated code. Keep tests only when they define or directly cover the behavior, or the user asked.
5. Read targeted sections. Record why each file matters, the domain concepts and boundary it belongs to, and exact types, signatures, and call sites planners will need.

Output a compact brief: scope, files and why each matters, key types, signatures, and symbols, affected callers, and missing neighbors or open questions. End with "Context prepared: N files."
