---
name: verify-library-contract-before-implementing
description: "Verify @xyflow/react / elkjs behavior via context7 or docs before building a load-bearing fix on assumptions"
condition: ["appears to race node measurement", "reliably toggle between levels"]
scope: "text"
---

Stop. You're about to build a load-bearing effect rewrite on assumed behavior of React Flow (`@xyflow/react` v12) or elkjs. The repo's CLAUDE.md forbids guessing library behavior (verify with `context7`), and `docs/app-design.md` says prop semantics must be checked against installed versions.

Before the fix:
1. Query `context7` for the v12 contract: `useNodesInitialized` toggling, `node.measured`, whether `setNodes` with fresh objects keeps measured dimensions, and ELK layered cycle-breaking (`considerModelOrder`, which edge reverses).
2. No hit: read the installed source in `node_modules/@xyflow/react` (and elkjs) or official docs, then web search.
3. Still nothing: stop and name the missing reference. Don't ship a guess.

Browser checks confirm the result, not the contract. Establish documented behavior first.
