---
name: do-not-yield-with-pending-published-ci
description: "Do not report published pull requests complete while their required CI remains pending or failing."
condition: "Initial CI on #\\d+:.*\\b(?:pending|failed|red)\\b"
scope: "text"
---

After creating or pushing pull requests, poll the required checks for the published stack. If a check fails, inspect its logs, fix actionable failures, push the repair, and repeat until green. Do not present PR publication as complete while checks are pending or red unless an unavailable external prerequisite makes progress impossible; then name that exact blocker.