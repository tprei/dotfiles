## Agent model routing
- **Planning and research agents** (`planner`, `explorer`, `technical-architect`) use `model: opus`.
- **Implementation agents** use `model: sonnet`.
- **git-commit-specialist** uses `model: haiku`.
- When spawning via the Agent tool, always set `model` explicitly.
- If an implementation agent hits ambiguity or needs architectural decisions, stop and return to the planning loop with an opus-tier agent rather than resolving inline.

## Large-file reading strategy
- For oversized files, propose chunking/summaries/streaming before ingesting the whole thing. Extract key sections first, offer commands for progressive reads.

## Dotfile edits
- Detect platform/shell and surface structural differences before editing user-scoped config. Produce a preview, keep edits idempotent and scoped, don't overwrite whole files.

# Prose style

- Present tense, active voice, second person, contractions ok
- oxford comma, sentence case headings, parallel structure
- code font for objects/methods, bold for UI labels
- avoid easy/simple/just, latin abbreviations, marketing language

# Manual Reminders

<!-- manual-claude-guidance:start -->

- Always look at content as a whole, never ever take code out of context. Use repomix to package code neatly. If code is way too large, then use compress=true in repomix. Try to get exactly the files you need to package
- Use context7 for context
- Always run `/prepare` when entering plan mode to establish proper code context before exploring or planning
- If the user provides a repomix bundle in the prompt, skip `/prepare`
- Always write .MD plan/todo files to separate folder. If docs already exists, write it there, otherwise create one
- After you make significant changes, always engage the git commit specialist agent
- When working on a new issue, create a new worktree and branch so that other agents do not conflict with your work in the same environment
- NEVER add fallbacks. Before making any change, ask yourself: "Is this a definitive solution, or is this a fallback/workaround?" If it's the latter, keep searching for the root cause. Exhaust all investigation avenues. If you genuinely cannot find the right fix, tell the user directly instead of shipping a fallback
- Never add "🤖 Generated with Claude Code" to PRs
- Never put "commited by agent" or "committed by claude code" -- same for PRs
- Don't write co-authored by Claude
- Always timestamp doc names. Follow conventions of the repo under docs repo
- Don't say things like "you're absolutely right!" or "my bad!". Be direct and communicate like a principal engineer. I don't want your fake attitude
- Never add meta comments about the actual work in code (e.g., "Fix 1: ...", "Change 2: ...", "Update: ..."). Code changes should be self-evident from git history
- Finish implementations. Do not stop halfway
- Do not write comments on code unless I tell you to
- Do not add speculative methods - only implement what is required
- Do not write backwards-compatibility shims - change all call sites directly
- Avoid set, cat, pipes for writing/reading files
- Prefer `rg` over `grep` for all content searches; use the Grep tool (which uses ripgrep) rather than raw `grep` commands
- When asked about tmux commands, keybindings, or configuration, use the /tmux-specialist skill for quick answers
- When creating a new Claude Code skill, use the /add-skill skill to scaffold the directory structure and SKILL.md
- When asked to review a PR, use the /review skill
- Prefer DDD when building features
- Build explicit code: explicit boundaries, explicit types. Avoid nested ternaries. Don't overengineer — keep changes minimal and focused, follow existing repo conventions
- Never disable eslint rules (or the equivalent lint/typecheck mechanism in the language) to make errors go away — fix the underlying issue
- Tests must cover critical product behavior. Skip tautological tests, tests asserting only static styles, and tests for static copy (placeholders, labels, helper text, empty state text, tooltip text)
- Always read a file before editing it. Prefer the Edit tool for targeted changes over rewriting entire files
- Prefer `fd` over `find` and `bat` over `cat` for previews when available. Prefer non-interactive command invocations
- Commit messages: concise, focused on the why

<!-- manual-claude-guidance:end -->
