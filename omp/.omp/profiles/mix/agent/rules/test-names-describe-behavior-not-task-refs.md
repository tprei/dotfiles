---
name: test-names-describe-behavior-not-task-refs
description: "Test/describe names must describe the scenario or behavior under test, never reference a review, PR, ticket, or priority label"
condition: ["P[0-9]\\s*\\(review\\s*#", "\\(review\\s*#\\d+\\)", "Fix\\s+P[0-9]\\s*:", "review\\s*#\\d+\\s*\\)?\\s*:", "PR\\s*#\\d+"]
scope: ["tool:write(*.test.ts)", "tool:write(*.spec.ts)", "tool:edit(*.test.ts)", "tool:edit(*.spec.ts)", "tool:write(*.test.tsx)", "tool:edit(*.test.tsx)"]
---

Name tests after the observable scenario/behavior being verified, never after the review finding, PR number, or priority label that motivated the change (e.g. no `P1 (review #12): ...` or `Fix P0: ...` prefixes in `it(...)`/`describe(...)` titles). Test names are durable documentation of behavior and must read correctly with zero knowledge of any review, PR, ticket, or session — a reviewer six months from now sees only the code, not the review thread.

Bad: `it("P1 (review #12): a review_required resolver still blocks a second resolution command", ...)`
Good: `it("blocks a second resolution command while the first is in review_required", ...)`

If provenance/context matters, put it in a code comment above the test, not in the title string. Rename any existing offending test titles found nearby before moving on, and grep the touched test files for the same pattern (`review #`, `PR #`, `Fix P0/P1`) before finishing.