---
name: deslop
description: Audit a repo for slop (lint/typecheck suppressions, advisory CI gates, silenced errors, dead code, debug leftovers) and remove it by fixing root causes, never by re-suppressing. Use for "deslop", "remove ignores/suppressions", "make mypy/tsc/eslint blocking", or a post-change cleanliness sweep.
---

# Deslop

Remove suppressions, advisory gates, silenced errors, dead code, and debug leftovers by fixing root causes. Patterns live in `references/slop-catalog.md`.

Non-negotiables:
- Never fix a hit by adding, moving, or widening a suppression, or by disabling a rule or excluding a module globally.
- A genuinely unfixable hit: stop and report the file, error, and what you tried. Don't leave a suppression to make the run green.
- An exception needs user sign-off, the narrowest scope, an inline reason, and a linked issue.

Loop: scan, classify, fix, verify.

1. Gates: read CI (`.github/workflows/*`, `.gitlab-ci.yml`) and tool config (`pyproject.toml`, `setup.cfg`, `ruff.toml`, `mypy.ini`, `pyrightconfig.json`, `eslint.config.*`, `.eslintrc*`, `tsconfig*.json`, `package.json` scripts). List every lint and typecheck command and whether it blocks.
2. Scan every catalog pattern with `rg`. Build a per-category, per-file inventory with counts before fixing anything.
3. Baseline: run lint and typecheck. Flag `continue-on-error: true`, `|| true`, silencing `exclude` or override blocks, baseline files, and `--max-warnings <n>`. An advisory gate that passes is failing.
4. Classify: every hit is removable unless it's rare and real (an upstream stub bug, for example), which follows the exception rule.
5. Fix the type, import, unused binding, or broad except, never the suppression that hid it. Large repos: fan out named implementation subagents by directory, using their default models, told never to re-suppress and to hand back on architectural ambiguity. Small repos: one pass.
6. Make gates blocking: remove advisory wrappers, silencing excludes, and baselines; turn on warnings-as-errors (`--max-warnings 0`, `strict`, or equivalent).
7. Verify: lint clean, zero typecheck errors, tests pass, and a re-scan shows the inventory shrank with nothing new. Run `enemy` on non-trivial fixes, then hand off to `git-commit-specialist`.
8. Report a before and after count per category, plus each approved exception with scope, reason, and issue:

```
| Category          | Before | After |
|-------------------|--------|-------|
| # type: ignore    |     14 |     0 |
| continue-on-error |      2 |     0 |
```
