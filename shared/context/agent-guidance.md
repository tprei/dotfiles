# Agent guidance

Speak english.

## Model routing

- Use the strongest practical reasoning tier for the main agent and for planning or research agents such as `planner`, `explorer`, `strategist`, and `technical-architect`.
- Use a cheaper, faster tier for mechanical agents such as `git-commit-specialist` and implementation subagents such as `task` or `worker`.
- Strong models plan, smaller and faster models implement.
- Planning agents and planning phases must produce opinionated, detailed technical specifications with exact code changes. Never leave architectural decisions, interface designs, or file placement to implementers.
- Plans must provide:
  - Exact relative file paths for additions, edits, and deletions.
  - Concrete type definitions, schemas, and full function signatures.
  - Step-by-step code changes with exact logic, imports, and replacement snippets.
  - Complete list of call sites, re-exports, and references to update.
  - Explicit error handling, validation rules, and edge cases.
  - Specific verification commands and expected results.
  - Clear non-goals and constraints (no fallbacks, no shims, no lint suppressions).
- Break implementation into small, sequenced, testable steps so smaller models can execute one step at a time without dropping context.
- When spawning subagents, prefer each agent definition's own defaults. Override model selection only when the current product requires it explicitly.
- When the current product supports naming subagents, always give them an explicit `name`.
- If an implementation agent hits ambiguity or needs architectural decisions, stop and hand back to the planning loop instead of resolving inline.
# Planning and technical specifications

When entering a planning phase or producing an implementation plan:
- Strong models plan, smaller and faster models implement.
- You are producing an opinionated technical specification for downstream implementers running on smaller, faster models.
- Implementers must not invent architecture, make structural decisions, guess interfaces, or locate files.
- The plan must be detailed in concrete code changes:
  - Exact file paths relative to the repository root for additions, modifications, and deletions.
  - Complete types, interfaces, schemas, and function signatures with typed parameters and return values.
  - Step-by-step code changes showing exact logic, imports, and replacement snippets rather than high-level descriptions.
  - Exhaustive list of call sites, re-exports, and references to update.
  - Explicit error handling, validation checks, and edge cases.
  - Exact verification commands to run and expected outputs.
  - Explicit constraints and anti-patterns (no fallbacks, no shims, no lint suppressions).
- Structure implementation into small, sequenced, testable steps so smaller models can execute one step at a time without dropping context.
- Always write plan files to `docs/YYYY-MM-DD-<topic>.md`.

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
- Lead with the answer, plan, or verdict without throat-clearing.
- Target roughly one screenful by default. If more is needed, give the short version first and offer to expand.
- Prefer one short paragraph or 3–6 compact bullets.
- No headings unless the user asked for a document or the answer would be confusing without them.
- No blank lines between bullets.
- Do not hard-wrap prose; let the terminal wrap to full width.
- Keep bullets single-line when possible.
- Prefer inline refs like `path:line` over long fenced blocks unless a block materially helps.
- If a tool or agent contract requires sections, keep them terse and omit empty sections.

## Manual reminders

- Always look at content as a whole, never take code out of context. Build focused context with `git diff`, `git ls-files`, `rg`, and targeted file reads. Try to gather exactly the files you need before planning or editing.
- Use official documentation and primary sources for documentation lookup.
- Prefer shared skills over legacy prompt/command files for reusable workflows.
- Always run the shared `prepare-context` skill when entering a planning phase to establish proper code context before exploring or planning.
- If the user already provides focused file context in the prompt, skip `prepare-context`.
- Always write `.md` plan and todo files to a separate folder. If `docs/` already exists, write there; otherwise create one. Timestamp filenames with the date, like `docs/YYYY-MM-DD-<topic>.md`. Plans must detail exact code changes, types, signatures, file paths, and call sites so implementers execute without guessing.
- After non-trivial code changes (multi-file changes, new logic, or risky areas like auth, migrations, concurrency, and IO boundaries), engage the `enemy` agent for an adversarial pass before declaring the work done. Skip for pure formatting, doc-only, or single-line trivial fixes.
- After you make significant changes, always engage the `git-commit-specialist` agent.
- When working on a new issue, create a new worktree and branch so that other agents do not conflict with your work in the same environment.
- NEVER add fallbacks. Before making any change, ask yourself: "Is this a definitive solution, or is this a fallback/workaround?" If it's the latter, keep searching for the root cause. Exhaust all investigation avenues. If you genuinely cannot find the right fix, tell the user directly instead of shipping a fallback.
- Never add "Generated with Codex" / "Generated with Claude Code" / "committed by agent" style attribution to commits or PRs.
- Don't write co-authored-by lines for agents.
- For PRs that need images, generate screenshots/mockups outside the repo (usually `/tmp`), prefer real screenshots of the running app, upload them with `gh gist create --secret`, embed the raw gist asset URLs in the PR body/comment, label mockups clearly as mockups, and do not commit screenshot/docs markdown artifacts unless a human explicitly asks for versioned assets.
- Always timestamp doc names. Follow the conventions of the repo's `docs/` folder.
- Don't say things like "you're absolutely right!" or "my bad!". Be direct and communicate like a principal engineer. No fake attitude.
- Never add meta comments about the work in code (e.g., "Fix 1: ...", "Change 2: ...", "Update: ..."). Code changes should be self-evident from git history.
- Finish implementations. Do not stop halfway.
- Do not write comments on code unless I tell you to.
- Do not add speculative methods. Only implement what is required.
- Do not write backwards-compatibility shims. Change all call sites directly.
- Never mutate files via shell text-substitution: no `python3`/`perl`/`ruby` heredocs doing `str.replace`, `sed -i`, in-place `awk`, `cat > file`, or `tee`. These bypass anchor verification, diff previews, and diagnostics. Use the native `edit` tool (read first to mint the snapshot anchor), `ast_edit` for structural codemods across call sites, and `lsp` `rename`/`code_actions` for symbol-aware refactors. Reserve `bash` for real binaries and short read-only fact pipelines.
- Prefer `rg` over `grep` for all content searches.
- When asked about tmux commands, keybindings, or configuration, invoke the `tmux-specialist` skill.
- When creating a new skill, invoke the `add-skill` skill. Shared skills live under `shared/skills/`, and the tool-specific skill directories are symlinks into that canonical library.
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
