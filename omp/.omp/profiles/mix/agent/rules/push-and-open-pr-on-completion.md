---
name: push-and-open-pr-on-completion
description: "Never end a feature-branch change at the commit — push and open the PR (or a stack) before yielding"
condition: ["[Cc]ommitted as [`'\\\"]?[0-9a-f]{7,40}", "[Ss]ingle commit on branch [`'\\\"]?feat/"]
scope: "text"
---

A finished change on a feature branch is not done until a PR exists. When you verify work on a non-default branch (e.g. `feat/smart-pick-subtitles`) and report the commit, the same turn must continue: push the branch with `git push -u origin <branch>`, then open the PR with `gh pr create` (or a stack of PRs when slices belong in separate reviews). Follow the repo's PR body conventions (Why / What / Verification, real screenshots via secret gists when the change is visual, no agent attribution or co-authored-by trailers). Never stop at "Committed as <sha>" and wait for the user to say "make pr" — the PR is part of the deliverable.