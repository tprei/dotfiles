---
name: test-names-describe-behavior-not-task-refs
description: "Test/describe names must describe the scenario or behavior under test, never reference a review, PR, ticket, or priority label"
condition: ["P[0-9]\\s*\\(review\\s*#", "\\(review\\s*#\\d+\\)", "Fix\\s+P[0-9]\\s*:", "review\\s*#\\d+\\s*\\)?\\s*:", "PR\\s*#\\d+"]
scope: ["tool:write(*.test.ts)", "tool:write(*.spec.ts)", "tool:edit(*.test.ts)", "tool:edit(*.spec.ts)", "tool:write(*.test.tsx)", "tool:edit(*.test.tsx)"]
---

Name tests after the behavior they verify, never the review finding, PR, ticket, or priority that prompted them. Titles must make sense to a reader who never saw the review.

- Bad: `it("P1 (review #12): a review_required resolver still blocks a second resolution command", ...)`
- Good: `it("blocks a second resolution command while the first is in review_required", ...)`

Rename offending titles nearby, and grep touched test files for `review #`, `PR #`, and `Fix P0/P1` before finishing.
