---
name: stacked-pr-merge-use-gt-not-gh
description: "For Graphite-managed stacked PRs, merge with `gt merge`/`gt`, never `gh pr merge` per-PR — it merges into intermediate base branches and shreds the stack"
condition: "gh pr merge \\d+ --squash"
scope: "tool"
---

Never loop `gh pr merge <n> --squash` over a Graphite stack. Each PR's base is its parent branch, so `gh pr merge` squashes into that parent and `--delete-branch` removes the next PR's base, leaving unrecoverable conflicts.

Run `gt merge` from the top of the stack; it lands each branch on `main` in order and retargets the rest. If `gt merge` can't run, resync (`gt sync`, `gt track`) and confirm every PR's base before using `gh pr merge`.
