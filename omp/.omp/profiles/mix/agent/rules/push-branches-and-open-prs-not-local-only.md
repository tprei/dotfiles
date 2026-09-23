---
name: push-branches-and-open-prs-not-local-only
description: "When a stacked branch set is complete and verified, push to origin and open the PRs (draft is fine) instead of leaving them local-only — CI checks are part of verification"
condition: ["did not push", "not yet push", "did not open PRs", "without pushing", "local[- ]only", "I did not push", "not push", "haven't pushed", "kept.*local"]
scope: "text"
---

Verified work belongs on GitHub. Once a stacked branch set passes local build, tests, and lint, push every branch and open the PRs (`gh pr create` or `gt submit`; drafts are fine) so CI runs in the real environment and humans can review. Local-only branches are an incomplete deliverable. If pushing is genuinely risky (for example, a competing concurrent stack), say so and ask; otherwise push.
