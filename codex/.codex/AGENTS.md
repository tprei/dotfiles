# Agent model routing

- Default model across the main thread and subagents is `gpt-5.4` at `model_reasoning_effort = "xhigh"`.
- **Planning and research subagents** (`planner`, `explorer`, `technical-architect`) use `model_reasoning_effort = "xhigh"`.
- **Implementation subagents** use `model_reasoning_effort = "high"`.
- **git-commit-specialist** uses `model_reasoning_effort = "low"` — cheap, fast, mechanical work.
- Always spawn subagents with an explicit `name`; rely on the subagent's own TOML for model selection.
- If an implementation subagent hits ambiguity or needs architectural decisions, stop and hand back to the planning loop rather than resolving inline.

# Large-file reading strategy

- For oversized files, propose chunking/summaries/streaming before ingesting the whole thing. Extract key sections first, offer commands for progressive reads.

# Dotfile edits

- Detect platform/shell and surface structural differences before editing user-scoped config. Produce a preview, keep edits idempotent and scoped, don't overwrite whole files.

# Prose style

- Present tense, active voice, second person, contractions ok
- oxford comma, sentence case headings, parallel structure
- code font for objects/methods, bold for UI labels
- avoid easy/simple/just, latin abbreviations, marketing language

# Screen density

- Default to dense terminal output.
- Lead with the answer, plan, or verdict — no throat-clearing.
- Target roughly one screenful by default. If more is needed, give the short version first and offer to expand.
- Prefer one short paragraph or 3–6 compact bullets.
- No headings unless the user asked for a document or the answer would be confusing without them.
- No blank lines between bullets.
- Do not hard-wrap prose; let the terminal wrap to full width.
- Keep bullets single-line when possible.
- Prefer inline refs like `path:line` over long fenced blocks unless a block materially helps.
- If a tool or agent contract requires sections, keep them terse and omit empty sections.

# Manual reminders

- Always look at content as a whole, never ever take code out of context. Use repomix to package code neatly. If code is way too large, then use `compress=true` in repomix. Try to get exactly the files you need to package.
- Use context7 for documentation lookup.
- Always run `/prompts:prepare` when entering a planning phase to establish proper code context before exploring or planning.
- If the user provides a repomix bundle in the prompt, skip `/prompts:prepare`.
- Always write `.md` plan/todo files to a separate folder. If `docs/` already exists, write there; otherwise create one.
- After non-trivial code changes — multi-file changes, new logic, risky areas (auth, migrations, concurrency, IO boundaries), or anything beyond mechanical refactors/renames/docs — engage the `enemy` subagent for an adversarial pass before declaring the work done. Skip for pure formatting, doc-only, or single-line trivial fixes.
- After you make significant changes, always engage the git-commit-specialist subagent.
- When working on a new issue, create a new worktree and branch so that other agents do not conflict with your work in the same environment.
- NEVER add fallbacks. Before making any change, ask yourself: "Is this a definitive solution, or is this a fallback/workaround?" If it's the latter, keep searching for the root cause. Exhaust all investigation avenues. If you genuinely cannot find the right fix, tell the user directly instead of shipping a fallback.
- Never add "Generated with Codex" / "Generated with Claude Code" / "committed by agent" style attribution to commits or PRs.
- Don't write co-authored-by lines for agents.
- Always timestamp doc names. Follow the conventions of the repo's `docs/` folder.
- Don't say things like "you're absolutely right!" or "my bad!". Be direct and communicate like a principal engineer. No fake attitude.
- Never add meta comments about the work in code (e.g., "Fix 1: ...", "Change 2: ...", "Update: ..."). Code changes should be self-evident from git history.
- Finish implementations. Do not stop halfway.
- Do not write comments on code unless I tell you to.
- Do not add speculative methods — only implement what is required.
- Do not write backwards-compatibility shims — change all call sites directly.
- Avoid `set`, `cat`, and pipes for writing/reading files; use the editor tooling.
- Prefer `rg` over `grep` for all content searches.
- When asked about tmux commands, keybindings, or configuration, invoke the `tmux-specialist` skill.
- When creating a new skill, invoke the `add-skill` skill to scaffold the directory structure and `SKILL.md`.
- When asked to review a PR, invoke the `review` skill.
- Prefer DDD when building features.
- Build explicit code: explicit boundaries, explicit types. Avoid nested ternaries. Don't overengineer — keep changes minimal and focused, follow existing repo conventions.
- **Zero suppressions.** Never silence a linter or typechecker to clear an error. Banned unless the user explicitly signs off: `# type: ignore`, `# pyright: ignore`, `# pylint: disable`, `# noqa`, `// @ts-ignore`, `// @ts-expect-error`, `// eslint-disable*`, `as any`, unjustified `cast()` / `Any`, and bare/broad `except Exception` / `catch {}` used to swallow errors. Fix the root cause.
- **No advisory gates.** Lint and typecheck steps must be blocking. Never add or leave `continue-on-error: true`, `|| true`, advisory wrappers, silencing per-module `exclude`/override blocks, suppression baseline files, or `--max-warnings <n>` slack. Lint + typecheck must pass with **zero** warnings and errors.
- **A suppression is a last resort, not a fix.** If you genuinely cannot resolve an error, STOP and tell the user (per the no-fallback rule) instead of suppressing. Any approved exception must be the narrowest possible scope, carry an inline reason, and link a tracking issue.
- **Leave no debris.** No dead/commented-out code, no leftover `console.log` / `print` debugging, no unused imports/vars, no untracked `TODO`/`FIXME` without a linked issue.
- When asked to deslop, remove suppressions/ignores, or harden lint/typecheck gates, invoke the `deslop` skill.
- Tests must cover critical product behavior. Skip tautological tests, tests asserting only static styles, and tests for static copy (placeholders, labels, helper text, empty-state text, tooltip text).
- Always read a file before editing it. Prefer targeted edits over rewriting entire files.
- Prefer `fd` over `find` and `bat` over `cat` for previews when available. Prefer non-interactive command invocations.
- Commit messages: concise, focused on the why.
