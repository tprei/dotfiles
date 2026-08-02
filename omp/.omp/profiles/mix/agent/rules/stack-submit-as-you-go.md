---
name: stack-submit-as-you-go
description: "Submit each stacked PR via gt submit when its branch is implemented and green — never ask whether to submit"
condition: "(?i)want me to submit|submit the stack|leave that to you|defer.*submission|submit.*or leave"
scope: "text"
---

When you implement a stacked-diff branch (`gt create` + commit + focused tests green), the PR is not done until it is submitted. Run `gt submit --cli --edit` (or `gh pr create` against the parent branch) for each slice as it completes — submission IS the work, not a follow-up. Do not end a stack-implementation turn by asking the user whether to submit, and do not bundle all PRs for a single delayed handoff at the end. Submit per-slice so the GitHub-visible stack exists as you go. Only the slow gates that need the user's live environment (Compose secrets, running Dockerized API) justify leaving a branch unsubmitted, and even then you submit first and note the pending gate on the PR.