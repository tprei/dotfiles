---
name: stacked-pr-merge-use-gt-not-gh
description: "For Graphite-managed stacked PRs, merge with `gt merge`/`gt`, never `gh pr merge` per-PR — it merges into intermediate base branches and shreds the stack"
condition: "gh pr merge \\d+ --squash"
scope: "tool"
---

When merging a Graphite-tracked PR stack, NEVER loop `gh pr merge <n> --squash` over individual PR numbers. Each stacked PR's base is its parent branch, not `main`; `gh pr merge` squashes into that base branch and `--delete-branch` yanks the base out from under the next PR, breaking the rest of the stack with unrecoverable conflicts.

Use Graphite's own merge flow (`gt merge`, invoked from the top of the stack) so it walks the stack top-to-bottom, retargets/rebases each branch against the previous merge, and lands everything on `main` correctly. If `gt merge` truly cannot be used, resync tracking first (`gt sync`/`gt track`) and confirm each PR's base before ever touching `gh pr merge`.