---
name: stack-submit-as-you-go
description: "Submit each stacked PR via gt submit when its branch is implemented and green — never ask whether to submit"
condition: "(?i)want me to submit|submit the stack|leave that to you|defer.*submission|submit.*or leave"
scope: "text"
---

A stacked branch (`gt create`, commit, focused tests green) isn't done until submitted. Run `gt submit --cli --edit` (or `gh pr create` against the parent) per slice as it completes. Don't ask whether to submit, and don't batch submissions for the end. Only gates that need the user's live environment (Compose secrets, the Dockerized API) justify waiting, and even then submit first and note the pending gate on the PR.
