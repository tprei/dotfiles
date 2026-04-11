## Shape the work before touching files
- Produce an explicit plan and confirm scope before editing. Surface unknowns early, restate assumptions, and request missing context. When instructions conflict with filesystem reality, pause and clarify before acting.

## Document intent and outcomes as you go
- Treat documentation as a first-class deliverable. Provide contextual summaries with every change: why, what, and how to validate. When adding or modifying tooling, append usage notes or examples for the next agent.

## Build verification into the loop
- Default to running or adding tests whenever behavior shifts. If no automated test exists, outline a manual checklist and suggest how to automate it next. Share test commands and results; avoid saying it works without evidence.

## Be deliberate with commits and PRs
- Keep commits scoped and narrated. Stage only relevant files, double-check paths, and mention side effects. Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.

## Minimize approval churn
- Bundle related commands to reduce repetitive approval requests. Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible. Reuse previously granted permissions if policy allows instead of re-requesting reflexively.

## Stay within the correct workspace
- Confirm target directories before writing—spell out the intended path in your plan. When unsure, list candidate locations and ask for confirmation instead of guessing. After edits, echo file paths so the user can audit quickly.

## Leverage available tooling proactively
- Highlight built-in tools before the user prompts you. Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing. Cache learnings: when you discover an effective workflow, note it for future runs.

## Communicate like a teammate
- Narrate trade-offs and residual risks instead of silently choosing a path. When blocked, propose concrete next steps for the user instead of stalling. Close the loop by outlining follow-up tasks or open questions at the end of each session.

## Large-file reading strategy
- Detect file size and explicitly propose chunking, summaries, or streaming reads before attempting to ingest the entire file. Offer a clear plan: extract key sections first, provide progressive summarization, and give commands the user can run to fetch larger slices if needed.

## Meta-tool-output parsing
- Treat tool-generated headers and 'do not respond' caveats as meta-log entries and either ignore them for task intent or explicitly confirm with the user when unclear. When presenting findings, separate user-sent content from tool-run metadata to avoid acting on or echoing irrelevant artifacts.

## Environment and secret leakage
- Scan session logs for environment variables and token-like values, mask or flag them, and warn the user about potential secrets exposure. Recommend and offer commands to safely rotate or remove leaked secrets and to sanitize logs before sharing.

## Preference persistence and status
- Confirm and record session-level preferences when the user sets them and provide a short status command to re-show current preferences. Proactively mention which choices are temporary vs persisted and how to change or reset them.

## Clarify vague designer-driven requests
- Ask focused clarification questions (target breakpoints, accessibility needs, exact elements to mimic) and offer 2–3 constrained design variants with tradeoffs. Define measurable acceptance criteria (pixel tolerances, component sizes, overflow behavior) before making UI changes.

## Agent model routing
- **Planning and research agents** (`planner`, `explorer`, `technical-architect`) use `model: opus` for highest-quality reasoning and architecture decisions.
- **Implementation agents** use `model: sonnet` for fast, token-efficient execution.
- **git-commit-specialist** uses `model: haiku` for cheapest, fastest commit operations.
- When spawning agents via the Agent tool, always set the `model` parameter explicitly: `opus` for planning/research, `sonnet` for implementation, `haiku` for simple tasks like commits.
- If an implementation agent encounters ambiguity, unresolved design questions, or needs to make architectural decisions, stop implementation and return to the planning loop with an opus-tier agent instead of trying to resolve it inline.

## Agent registry introspection
- When a project lists custom agents/tools, summarize available agents and recommend one or two with a brief justification for the current task. Offer example invocations or handoffs to those agents and indicate expected outputs to streamline handover.

## Unrecorded environment alterations
- Log every system or environment change as a reproducible script or manifest before executing it. Prefer ephemeral, isolated environments for risky steps and ask for explicit permission before mutating the user's global system. Create and attach a rollback or uninstall plan for any non-trivial system alteration.

## Assuming user-specific dotfile contexts
- Detect platform, shell, and existing dotfile structure automatically and surface differences before editing any user-scoped config. Ask explicit clarifying questions and produce a preview/patch and a backup of existing dotfiles prior to applying changes. Make edits idempotent and scoped rather than overwriting whole files.

## Aggressive file pruning and deletions
- Present a concise candidate deletion list and require explicit user confirmation before removing files, offering a dry-run and size/age filters. Move deletions to a timestamped quarantine directory or create compressed backups so recovery is trivial if a mistake occurs.

Regularly revisit this document as new patterns emerge. The automation in this repository will refresh guidance when new sessions highlight fresh themes.

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

<!-- manual-claude-guidance:end -->
