---
name: create-pr-after-changes
description: "Always push the branch and open a PR with `gh pr create` after completing code changes"
condition: "\\b(?:Changes committed to branch|Amended into commit)\\b"
scope: "text"
---

Do not stop after committing changes to a branch. When implementation and verification are complete, push the branch to origin (`git push -u origin <branch>`) and open a pull request using `gh pr create` with a concise title and summary of the changes before concluding.