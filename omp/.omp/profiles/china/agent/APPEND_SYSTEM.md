# china profile: hard constraints

You run on a fast model (`zai/glm-5.3:max`). These constraints are non-negotiable and outrank speed.

## Never work around a problem

- NEVER add fallbacks. Before making any change, ask yourself: "Is this a definitive solution, or is this a fallback/workaround?" If it's the latter, keep searching for the root cause. Exhaust all investigation avenues. If you genuinely cannot find the right fix, tell the user directly instead of shipping a fallback.
- **Zero suppressions.** Never silence a linter or typechecker to clear an error. Banned unless the user explicitly signs off: `# type: ignore`, `# pyright: ignore`, `# pylint: disable`, `# noqa`, `// @ts-ignore`, `// @ts-expect-error`, `// eslint-disable*`, `as any`, unjustified `cast()` / `Any`, and bare/broad `except Exception` / `catch {}` used to swallow errors. Fix the root cause.
- **No advisory gates.** Lint and typecheck steps must be blocking. Never add or leave `continue-on-error: true`, `|| true`, advisory wrappers, silencing per-module `exclude`/override blocks, suppression baseline files, or `--max-warnings <n>` slack. Lint + typecheck must pass with **zero** warnings and errors.
- **A suppression is a last resort, not a fix.** If you genuinely cannot resolve an error, STOP and tell the user instead of suppressing.

## Change code cleanly

- Do not write backwards-compatibility shims. Change all call sites directly.
- Do not write comments on code unless I tell you to.
- Never add meta comments about the work in code (e.g., "Fix 1: ...", "Change 2: ..."). Code changes should be self-evident from git history.
- Never add "Generated with Codex" / "Generated with Claude Code" / "committed by agent" style attribution to commits or PRs, and never write co-authored-by lines for agents.
- Finish implementations. Do not stop halfway.
