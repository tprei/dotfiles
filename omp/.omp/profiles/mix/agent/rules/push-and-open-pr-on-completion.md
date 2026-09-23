---
name: push-and-open-pr-on-completion
description: "Never end a feature-branch change at the commit — push and open the PR (or a stack) before yielding"
condition: ["[Cc]ommitted as [`'\\\"]?[0-9a-f]{7,40}", "[Ss]ingle commit on branch [`'\\\"]?feat/"]
scope: "text"
---

A finished change on a feature branch isn't done until a PR exists. In the same turn that you report the commit, `git push -u origin <branch>` and `gh pr create`, or open a stack when slices need separate reviews. Follow the repo's PR body conventions (Why, What, Verification; real screenshots via secret gists for visual changes; no agent attribution or co-authored-by). Don't stop at "Committed as <sha>" and wait to be asked.
