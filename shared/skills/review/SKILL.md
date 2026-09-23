---
name: review
description: Comprehensive PR review. Use when the user asks to review a pull request, PR link, or PR number.
---

# PR review

## 1. Fetch the PR

Full URL: extract owner, repo, and number. Bare number: current repo. Nothing given: ask.

```bash
gh pr view <PR> --json title,body,author,baseRefName,headRefName,files,additions,deletions,commits,reviews,labels,milestone
gh pr diff <PR>
```

## 2. Delegate to `reviewer`

Every review runs through the `reviewer` task agent (`task`, `agent: "reviewer"`), never inline. The omp config pins `reviewer` to `zai/glm-5.3:max` (root, `mix`, and `china` profiles); delegating guarantees that model reviews. Pass one self-contained prompt with the PR metadata and diff (or the `gh` commands), plus sections 3 to 5 below. Relay its output as the review; don't re-review.

## 3. Context the reviewer builds

- README, `AGENTS.md`/`CLAUDE.md`, and contributing guides.
- Stack, test framework, CI, directory layout, architectural patterns, and the domain model: bounded contexts, aggregates, and the domain language.
- Every changed file read in full, not only the diff.

## 4. Dimensions

Mark each finding praise, concern, or question. Skip dimensions that don't apply.
- Correctness: matches the description; logic errors, off-by-one, uncovered branches and edge cases.
- Design: fits existing patterns and module boundaries; missing or needless abstractions; domain logic in the domain layer, not handlers, UI, or infra; names in the domain language; no crossed bounded contexts; scales with expected growth.
- Product: user impact, UX regressions, accessibility, useful error messages.
- Tests: new behavior and failure paths covered; stale tests updated; right level (unit, integration, e2e).
- Security: injection (SQL, XSS, command), secret handling, authz on new operations, validation at boundaries.
- Performance: N+1 queries, needless allocations, blocking calls, missing indexes, latency or memory regressions.
- Reliability: behavior on network errors, timeouts, and bad input; retries; observability.
- Quality: readability, precise and consistent names, dead code, duplication, needless complexity.
- Dependencies and config: justified, maintained deps; safe defaults; reversible migrations.
- Docs: PR explains why; public APIs and user-facing changes documented; comments only where logic is non-obvious.

## 5. Output

Cite files and lines; quote code when it helps. Omit empty sections.

```markdown
## Summary
<what it does, who it affects, overall assessment>

## Verdict
<APPROVE | REQUEST_CHANGES | COMMENT>: <one-line rationale>

## Findings
### Critical (must fix before merge)
### Suggestions
### Nits
### Praise

## Questions
```
