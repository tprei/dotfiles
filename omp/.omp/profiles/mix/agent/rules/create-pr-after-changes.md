---
name: create-pr-after-changes
description: "Always push the branch and open a PR with `gh pr create` after completing code changes"
condition: "\\b(?:Changes committed to branch|Amended into commit)\\b"
scope: "text"
---

Committing isn't the end. Once implementation and verification pass, `git push -u origin <branch>` and `gh pr create` with a concise title and summary.
