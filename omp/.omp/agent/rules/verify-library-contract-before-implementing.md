---
name: verify-library-contract-before-implementing
description: "Verify @xyflow/react / elkjs behavior via context7 or docs before building a load-bearing fix on assumptions"
globs: ["**/*.ts", "**/*.tsx"]
condition: ["@xyflow/react", "useNodesInitialized", "considerModelOrder", "elkjs"]
scope: "tool:edit, tool:write"
---

Stop — you are diagnosing library behavior (React Flow `@xyflow/react` v12 / elkjs) by assumption and are about to build a load-bearing effect rewrite on it. Proceeding here is exactly the autonomous, unverified change that gets sent back for reassessment.

This repo's CLAUDE.md is explicit: **NEVER guess usage or implementation details of libraries, APIs, or SDKs — verify with `context7` first.** `docs/app-design.md` says the same: prop names and semantics "should still be checked against the installed versions at build time."

Before writing the fix, ground every behavior you rely on:
1. Query `context7` for the exact v12 contract: `useNodesInitialized` toggle semantics, `node.measured`, whether `setNodes` with fresh objects preserves measured dimensions, and ELK layered cycle-breaking (`considerModelOrder`, which edge gets reversed).
2. No `context7` hit → read the installed source under `node_modules/@xyflow/react` (and elkjs) or the official docs, then web search.
3. Still nothing → STOP and state the missing reference; do not ship a guess.

Browser/console verification confirms the *result* but does NOT replace knowing the *contract*. Establish the documented behavior, then implement — don't reverse-engineer it from a zoom-2.0 symptom and call it robust.
