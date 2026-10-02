---
name: no-branch-deletion-during-pr-merge
description: "Prevent merge commands from deleting branches that stacked PRs may still target."
condition: "\\bgh\\s+pr\\s+merge\\b[^;\\r\\n&|]*\\s(?:--delete-branch\\b|-d\\b)"
scope: "tool"
---

Do not run `gh pr merge` with `--delete-branch` or `-d`. Deleting a parent branch can close an unmerged child PR that still targets it.

Prefer Graphite's stack merge for stacked PRs. If merging manually, merge without branch deletion, restack and submit the remaining branches, and verify their remote base branches before considering cleanup. Before deleting any branch, query GitHub for open PRs targeting it; do not delete it if any exist or the query fails.

If Graphite reports an untracked branch or invalid parent, stop merging and repair the tracking relationships. Do not replace that repair with branch resets, cherry-picks, or force-pushes.