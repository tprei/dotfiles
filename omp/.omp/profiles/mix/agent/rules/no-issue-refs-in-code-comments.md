---
name: no-issue-refs-in-code-comments
description: "Code comments must never reference issue numbers, tickets, or planning conversations"
condition: "issue #[0-9]"
scope: ["tool:write(*)", "tool:edit(*)"]
---

Code comments must describe current behavior only — never reference issue numbers (`issue #157`), issue URLs, or planning conversations (`as discussed`, `the issue asks`). When writing or editing `.go`, `.py`, `.ts`, `.tsx`, `.js` files, scan every comment for `issue #` references and rephrase them as self-contained behavior descriptions. In planning artifacts (`.md`, `local://`), issue references are acceptable.

When you finish removing issue references from code, grep the ENTIRE repo — not just the directories you edited. A narrow `git grep -- path1 path2` that excludes `services/embedding/` or other subtrees will miss references like `# The vocabulary-mismatch pair from issue #157` in files outside your edit scope.