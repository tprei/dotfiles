---
name: wait-for-ci-green
description: "Do not stop while CI is pending or failing; continue until all checks pass or no actionable work remains"
condition: "GitHub has queued fresh CI runs[\\s\\S]*current status is pending"
scope: "text"
---

Do not yield while CI is queued, pending, or failing. Continue monitoring the checks, diagnose and fix failures, and rerun them until every required check is green. Stop only when all CI is green or there is genuinely no actionable work left; state the exact blocker if one remains.