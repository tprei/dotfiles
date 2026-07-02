---
name: deslop
description: Audit a repo for slop — inline lint/typecheck suppressions, advisory CI gates, silenced errors, dead code, debug leftovers — and remove it by fixing root causes, never by re-suppressing. Use for "deslop", "remove ignores/suppressions", "make mypy/tsc/eslint blocking", or a post-change cleanliness sweep.
---

# Deslop

Audit a repo for slop — inline lint/typecheck suppressions, advisory CI gates, silenced errors, dead code, and debug leftovers — and remove it by fixing root causes, never by re-suppressing.

## When to use

- User asks to "deslop", "remove ignores/suppressions", or "clean up the slop".
- User wants to make a checker blocking ("make mypy/tsc/eslint blocking", "warnings as errors").
- A post-large-change verification sweep, before handing off or opening a PR.
- You suspect a checker has been silently passing because its gate is advisory.

## Non-negotiables

- Never fix a hit by adding or widening a suppression. Removing one ignore by adding another is not progress.
- Never globally disable a rule (or exclude a module) to clear a local error. Narrow the blast radius, never widen it.
- If a hit is genuinely unfixable, STOP and report it to the user with the file, the error, and what you tried — per the no-fallback rule. Do not leave a suppression behind to make the run "green".
- An approved exception (user signs off) must be the narrowest possible scope, carry an inline reason, and link a tracking issue.

## Instructions

Work the loop: scan → classify → fix → verify.

### 1. Detect the stack and gates

Read the CI configs (`.github/workflows/*`, `.gitlab-ci.yml`, etc.) and tool config (`pyproject.toml`, `setup.cfg`, `ruff.toml`, `mypy.ini`, `pyrightconfig.json`, `eslint.config.*`, `.eslintrc*`, `tsconfig*.json`, `package.json` scripts). Identify every lint and typecheck command and, for each, whether it is blocking or advisory.

### 2. Scan for slop

Run every pattern in `references/slop-catalog.md` with `rg`. Produce a per-category, per-file inventory with counts. Don't fix yet — inventory first.

### 3. Baseline the gates

Run lint + typecheck and capture the current pass/fail. Flag every advisory escape hatch: `continue-on-error: true`, `|| true` wrappers, silencing per-module `exclude`/override blocks, suppression baseline files, and `--max-warnings <n>` slack. A gate that "passes" only because it is advisory is failing.

### 4. Classify each hit

Default is removable — fix the root cause. Mark a hit as genuinely unavoidable only when it is rare and real (e.g., an upstream stub bug): that requires user sign-off, the narrowest scope, an inline reason, and a linked issue. When in doubt, it's removable.

### 5. Fix root causes

- **Large repos:** fan out parallel implementation subagents partitioned by directory/area. Spawn each with an explicit `name` and rely on the subagent's own definition file for model selection (per the agent routing rules). Instruct every subagent to fix the underlying error — never re-suppress, never widen an ignore — and to stop and hand back on architectural ambiguity rather than resolving it inline.
- **Small repos:** single pass, no fan-out.
- Either way: fix the type, the import, the unused binding, the broad except. Never the suppression that hid it.

### 6. Make gates blocking

Remove `continue-on-error`/advisory wrappers and `|| true`. Drop silencing `exclude`/override blocks and suppression baseline files. Set warnings-as-errors (`--max-warnings 0`, `strict`, or the tool's equivalent). Lint + typecheck must fail loudly on any new violation.

### 7. Verify

Lint clean, typecheck reports zero errors, tests pass. Re-run the catalog scan and confirm no new suppressions appeared and the inventory shrank (ideally to zero). Then run the `enemy` subagent on non-trivial fixes per the standing reminder, and hand off to `git-commit-specialist`.

### 8. Report

Produce a before/after table per category:

```
| Category              | Before | After |
|-----------------------|--------|-------|
| # type: ignore        |     14 |     0 |
| continue-on-error     |      2 |     0 |
| as any                |      9 |     0 |
| ...                   |    ... |   ... |
```

Call out any approved exceptions explicitly with their scope, reason, and linked issue.

## Reference files

| File | Contents |
|------|----------|
| `references/slop-catalog.md` | The ripgrep pattern catalog grouped by language/tool — every category to scan for. |
