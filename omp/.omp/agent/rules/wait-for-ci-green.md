---
name: wait-for-ci-green
description: "Do not stop while CI is pending or failing; continue until all checks pass or no actionable work remains"
condition: "GitHub has queued fresh CI runs[\\s\\S]*current status is pending"
scope: "text"
---

Don't yield while CI is queued, pending, or failing. Watch the checks, fix failures, and rerun until every required check is green. Stop only when CI is green or no actionable work remains, and name the exact blocker if one does.
