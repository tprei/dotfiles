---
name: push-branches-and-open-prs-not-local-only
description: "When a stacked branch set is complete and verified, push to origin and open the PRs (draft is fine) instead of leaving them local-only — CI checks are part of verification"
condition: ["did not push", "not yet push", "did not open PRs", "without pushing", "local[- ]only", "I did not push", "not push", "haven't pushed", "kept.*local"]
scope: "text"
---

Completed, verified work belongs on GitHub, not stranded in a local worktree. Once a stacked branch set passes local verification (build, tests, lint), push every branch and open the PRs (`gh pr create` or `gt submit`) so GitHub CI runs the same checks in the real environment and a human can review. Leaving branches local-only skips CI entirely and blocks review — that's not a stopping point, it's an incomplete deliverable. If a genuine conflict (e.g., a competing concurrent PR stack) makes pushing risky, say so explicitly and ask, but default to pushing once verification is green; don't quietly stop at 'ready for your review' while sitting on unpushed commits.