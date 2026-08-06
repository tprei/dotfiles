---
name: no-eslint-disable-comments
description: "Never disable linting rules inline — fix the underlying code instead"
condition: "eslint-disable"
scope: "tool"
---

Never add `// eslint-disable` or `// eslint-disable-next-line` to silence a lint violation. Restructure the code to satisfy the rule instead of suppressing it.

For an ambient global declared with `var` (e.g. `declare global { var X: T }`, which trips `no-var`), move the ambient declaration to a project-level `*.d.ts` file where `declare global` blocks are exempt from `no-var`, rather than inlining it in a `.ts`/`.tsx` source or test file.

If a lint rule is genuinely incompatible with a pattern the code truly needs, fix it once at the shared ESLint config level with a documented justification. Never suppress it locally — a local disable comment hides the violation from every future reader and from CI's own lint pass.