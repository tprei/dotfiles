---
name: no-issue-refs-in-code-comments
description: "Code comments must never reference issue numbers, tickets, or planning conversations"
condition: "issue #[0-9]"
scope: ["tool:write(*)", "tool:edit(*)"]
---

Code comments describe current behavior. Never reference issue numbers (`issue #157`), issue URLs, or planning talk (`as discussed`, `the issue asks`). Rephrase them as self-contained behavior in `.go`, `.py`, `.ts`, `.tsx`, and `.js` files. Planning artifacts (`.md`, `local://`) may reference issues.

When done, grep the whole repo for `issue #`, not only the directories you edited.
