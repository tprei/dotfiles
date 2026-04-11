---
name: review
description: "Comprehensive PR review. Use when the user asks to review a pull request, PR link, or PR number."
argument-hint: "<PR number or URL>"
model: opus
allowed-tools: Read Glob Grep Bash(gh:*) Bash(git:*)
user-invocable: true
disable-model-invocation: false
effort: max
---

# PR review

Perform a comprehensive, multi-dimensional review of a pull request.

## When to use

- User invokes `/review <PR>` with a PR number or URL
- User asks to review a pull request

## Instructions

### 1. Fetch PR context

Determine the PR to review from `$ARGUMENTS`:

- If a full URL (e.g. `https://github.com/owner/repo/pull/123`), extract owner/repo and number
- If a bare number (e.g. `123`), use the current repo context
- If empty, ask which PR to review

Fetch PR metadata and diff:

```
gh pr view <PR> --json title,body,author,baseRefName,headRefName,files,additions,deletions,commits,reviews,labels,milestone
gh pr diff <PR>
```

### 2. Understand the repository

Before reviewing the diff in isolation, build context:

- Read the repo's README, CLAUDE.md, and any contributing guidelines
- Identify the tech stack, test framework, and CI configuration
- Understand the directory structure and architectural patterns

### 3. Review dimensions

Evaluate the PR across every dimension below. For each, note findings as **praise**, **concern**, or **question**. Skip dimensions that don't apply.

#### Correctness
- Does the code do what the PR description claims?
- Are there logic errors, off-by-one mistakes, or unhandled edge cases?
- Do conditional branches cover all cases?

#### Architecture and design
- Does this fit the repo's existing patterns and abstractions?
- Are there unnecessary abstractions or missing ones?
- Does the change respect module boundaries and separation of concerns?
- Will this scale with anticipated growth?

#### Product impact
- Does this change serve the user well?
- Are there UX regressions, accessibility gaps, or usability concerns?
- Does error messaging help the end user understand what happened?

#### Tests
- Are new behaviors covered by tests?
- Are edge cases and failure paths tested?
- Do existing tests still make sense after this change, or do some need updating?
- Is the test strategy appropriate (unit vs integration vs e2e)?

#### Security
- Does this introduce injection vectors (SQL, XSS, command injection)?
- Are secrets, tokens, or credentials handled safely?
- Are authorization checks in place for new endpoints or operations?
- Does input validation happen at system boundaries?

#### Performance
- Are there N+1 queries, unnecessary allocations, or blocking calls?
- Could this regress latency or memory under load?
- Are database queries indexed appropriately?

#### Reliability
- How does this behave under failure (network errors, timeouts, invalid input)?
- Are retries, circuit breakers, or fallbacks appropriate here?
- Does this change affect observability (logging, metrics, alerting)?

#### Code quality
- Is the code readable and self-documenting?
- Are names precise and consistent with the codebase?
- Is there dead code, duplication, or unnecessary complexity?

#### Dependencies and configuration
- Are new dependencies justified and well-maintained?
- Do config changes have safe defaults?
- Are migrations reversible?

#### Documentation
- Does the PR description explain the why, not just the what?
- Are public APIs or user-facing changes documented?
- Do inline comments add value where logic is non-obvious?

### 4. Read changed files in full

Do not review the diff in isolation. For every changed file, read the full file to understand context around the modifications. This prevents false positives and reveals impact on surrounding code.

### 5. Produce the review

Structure your output as:

```markdown
## Summary

<One paragraph: what this PR does, who it affects, and your overall assessment>

## Verdict

<APPROVE | REQUEST_CHANGES | COMMENT> — <one-line rationale>

## Findings

### Critical (must fix before merge)
- ...

### Suggestions (would improve the PR)
- ...

### Nits (optional polish)
- ...

### Praise (what's done well)
- ...

## Questions
- ...
```

Omit empty sections. Reference specific files and line numbers. Quote code when relevant.
