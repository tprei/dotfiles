---
name: no-eslint-disable-comments
description: "Never disable linting rules inline — fix the underlying code instead"
condition: "eslint-disable"
scope: "tool"
---

Never add `// eslint-disable` or `// eslint-disable-next-line`. Restructure the code to satisfy the rule.

- A `declare global { var X: T }` that trips `no-var` belongs in a project `*.d.ts`, where `declare global` is exempt, not inline in source or tests.
- A rule truly incompatible with a needed pattern gets fixed once in the shared ESLint config with a justification, never locally.
