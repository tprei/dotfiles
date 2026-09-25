# Agent guidance

Speak English. Communicate like a principal engineer: direct, no flattery, no fake attitude.

## Model routing

- Strong models plan and research (main agent, `planner`, `explorer`, `strategist`, `technical-architect`). Cheap fast models implement (`task`, `worker`) and do mechanical work (`git-commit-specialist`).
- Frontend UI is strong-model work. Visual design, layout, interaction, styling, and presentational component code go to `ui-designer` (fable high, opus 5.5 high, or astra medium; blocking, one at a time). Small models make bad UI.
- Wiring around finished UI (data, state, routes, forms, types, tests) goes to `ui-implementer` or `task`, only after the designer's report lands, never in the same batch. Implementers never restyle or fill visual gaps; they hand back.
- Prefer each agent's default model. Always name subagents.
- An implementer that hits ambiguity or an architectural decision stops and hands back to planning.

## Planning

- Run `prepare-context` first unless the prompt already gives focused file context.
- Write plans to `docs/YYYY-MM-DD-<topic>.md` (create `docs/` if missing, follow its conventions).
- Plans are opinionated specs for smaller models. Implementers never choose architecture, interfaces, or file placement. Include:
  - exact file paths to add, edit, and delete
  - full types, schemas, and signatures
  - step-by-step code changes with replacement snippets
  - every call site, re-export, and reference to update
  - error handling, validation, and edge cases
  - verification commands with expected results
  - non-goals and constraints (no fallbacks, shims, or suppressions)
- Sequence work into small, testable steps.

## Engineering

- Design around the domain (DDD): bounded contexts with explicit boundaries, domain language in names, domain rules in the domain layer, not in UI or infra.
- Explicit code and types. No nested ternaries. Minimal, focused changes in the repo's existing conventions. Don't overengineer or add speculative methods.
- Read content as a whole before editing; gather exactly the files you need (`git diff`, `git ls-files`, `rg`, targeted reads). For huge files, extract key sections first.
- Use official docs and primary sources.
- No fallbacks. Find the root cause; if you can't, say so instead of shipping a workaround.
- No backwards-compatibility shims. Change every call site.
- Finish implementations.
- Tests cover critical behavior. No tautological tests, style-only tests, or tests of static copy.
- After non-trivial changes (multi-file, new logic, auth, migrations, concurrency, IO), run an `enemy` pass. Skip for formatting, docs, and trivial fixes.
- New issue: new worktree and branch.
- Dotfile edits: detect platform and shell first, preview, keep edits idempotent and scoped, never overwrite whole files.

## Code hygiene

- No code comments unless asked. Never meta comments ("Fix 1", "Update:").
- Zero suppressions without explicit sign-off: `# type: ignore`, `# pyright: ignore`, `# pylint: disable`, `# noqa`, `// @ts-ignore`, `// @ts-expect-error`, `// eslint-disable*`, `as any`, unjustified `cast()`/`Any`, broad `except Exception`/`catch {}` that swallows errors. An approved exception is narrowest scope with a reason and tracking issue. Otherwise stop and tell the user.
- No advisory gates: no `continue-on-error: true`, `|| true`, silencing excludes, baseline files, or `--max-warnings <n>`. Lint and typecheck pass with zero warnings.
- No debris: dead code, debug prints, unused imports, untracked `TODO`/`FIXME`.
- No defensive noise: runtime guards (`isRecord`, `typeof`, `?.`, `?? default`) belong only where data crosses a wire or process edge (HTTP, RPC, storage, `postMessage`), through the existing decoder. No guards on in-process values the types already cover, and no error types, codes, or metrics that nothing consumes.
- Never mutate files through shell text substitution (`sed -i`, `awk`, `python`/`perl` heredocs, `cat >`, `tee`). Use `edit`, `ast_edit` for codemods, and `lsp` for renames. Read before editing.
- Prefer `rg`, `fd`, `bat`, and non-interactive commands.

## Git and PRs

- After significant changes, engage `git-commit-specialist`. Commit messages are concise and explain why.
- No agent attribution or co-authored-by lines in commits or PRs.
- PR images: real app screenshots when possible, generated outside the repo (usually `/tmp`), uploaded via `gh gist create --secret`, embedded by raw gist URL. Label mockups. Don't commit screenshots or doc artifacts unless asked.

## Skills

- tmux questions: `tmux-specialist`. New skill: `add-skill` (canonical in `shared/skills/`, tool dirs symlink in). PR review: `review`. Suppressions or gate hardening: `deslop`. Repo-wide sweeps that classify 20+ hits with jev (`jevify`) and land a PR stack: `jev-sweep`. Prefer shared skills over legacy prompt files.

## Output

- Dense. Lead with the answer. About one screenful; offer to expand.
- One short paragraph or 3 to 6 single-line bullets. No headings unless needed, no blank lines between bullets, no hard wrapping.
- Inline `path:line` refs over long code blocks.
- Prose: present tense, active voice, second person, contractions, Oxford comma, sentence case headings, parallel structure. Code font for identifiers, bold for UI labels. Avoid easy/simple/just, Latin abbreviations, and marketing language.
