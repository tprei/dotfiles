---
name: do-not-yield-with-pending-published-ci
description: "Do not report published pull requests complete while their required CI remains pending or failing."
condition: "Initial CI on #\\d+:.*\\b(?:pending|failed|red)\\b"
scope: "text"
---

After pushing PRs, poll the stack's required checks. On failure, read the logs, fix, push, and repeat until green. Don't report publication complete while checks are pending or red unless an unavailable external prerequisite blocks progress; name it.
