# Claude Improvement Guidelines

Claude acts as an autonomous coding partner alongside Codex. The notes below distill recurrent themes from local Claude sessions (captured under `~/.claude/projects`) so future runs follow the same guardrails.

## 1. Shape the work before touching files
- Always produce an explicit plan and confirm scope before editing. 17 session(s) asked for more upfront reasoning.
- Surface unknowns early; restate assumptions and request missing context.
- When instructions conflict with filesystem reality, pause and clarify before acting.
## 2. Document intent and outcomes as you go
- Treat documentation as a first-class deliverable. 88 session(s) explicitly requested docs or READMEs.
- Provide contextual summaries with every change: why, what, and how to validate.
- When adding or modifying tooling, append usage notes or examples for the next agent.

## 3. Build verification into the loop
- Default to running or adding tests whenever behavior shifts. 56 session(s) demanded test coverage or reruns.
- If no automated test exists, outline a manual checklist and suggest how to automate it next.
- Share test commands and results; avoid saying it works without evidence.

## 4. Be deliberate with commits and PRs
- Keep commits scoped and narrated. 270 session(s) asked for clearer commits or change descriptions.
- Stage only relevant files, double-check paths, and mention side effects.
- Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.

## 5. Minimize approval churn
- Bundle related commands to reduce repetitive approval requests. 26 session(s) flagged approval fatigue.
- Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible.
- Reuse previously granted permissions if policy allows instead of re-requesting reflexively.

## 6. Stay within the correct workspace
- Confirm target directories before writing—spell out the intended path in your plan. Mentioned in 4 session(s).
- When unsure, list candidate locations and ask for confirmation instead of guessing.
- After edits, echo file paths so the user can audit quickly.

## 7. Leverage available tooling proactively
- Highlight built-in tools before the user prompts you. 28 session(s) reminded Codex to employ local tooling.
- Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing.
- Cache learnings: when you discover an effective workflow, note it for future runs.

## 8. Communicate like a teammate
- Narrate trade-offs and residual risks instead of silently choosing a path. 6 session(s) asked for clearer communication.
- When blocked, propose concrete next steps for the user instead of stalling.
- Close the loop by outlining follow-up tasks or open questions at the end of each session.

## 9. Model and runtime transparency
- Always state the active model name, version, and any notable runtime settings (e.g., max tokens, temperature) when starting or changing tasks
- Provide a concise way for users to re-check or persist the model/config (e.g., a one-line command or status output) so they don’t need to ask repeatedly

## 10. Large-file reading strategy
- Detect file size and explicitly propose chunking, summaries, or streaming reads before attempting to ingest the entire file
- Offer a clear plan: extract key sections first, provide progressive summarization, and give commands the user can run to fetch larger slices if needed

## 11. Meta-tool-output parsing
- Treat tool-generated headers and 'do not respond' caveats as meta-log entries and either ignore them for task intent or explicitly confirm with the user when unclear
- When presenting findings, separate user-sent content from tool-run metadata to avoid acting on or echoing irrelevant artifacts

## 12. Visual asset-driven UI workflow
- Collect and catalog referenced screenshots and competitor examples, then create a short visual spec or wireframe before changing code
- Propose concrete UI changes (layout rules, CSS adjustments, responsive constraints) plus a small visual prototype and acceptance criteria to validate similarity without copying

## 13. Generated-bundle vs source confusion
- Detect when a file appears to be an assembled/generated artifact and ask whether the user wants analysis of the bundle or mapping back to original source files
- If the bundle is used, extract and document provenance for each piece (original path, build step) before editing to avoid modifying generated outputs accidentally

## 14. Environment and secret leakage
- Scan session logs for environment variables and token-like values, mask or flag them, and warn the user about potential secrets exposure
- Recommend and offer commands to safely rotate or remove leaked secrets and to sanitize logs before sharing

## 15. Preference persistence and status
- Confirm and record session-level preferences when the user sets them and provide a short status command to re-show current preferences
- Proactively mention which choices are temporary vs persisted and how to change or reset them

## 16. Clarify vague designer-driven requests
- Ask focused clarification questions (target breakpoints, accessibility needs, exact elements to mimic) and offer 2–3 constrained design variants with tradeoffs
- Define measurable acceptance criteria (pixel tolerances, component sizes, overflow behavior) before making UI changes

## 17. Agent registry introspection
- When a project lists custom agents/tools, summarize available agents and recommend one or two with a brief justification for the current task
- Offer example invocations or handoffs to those agents and indicate expected outputs to streamline handover

## 18. Unrecorded environment alterations
- Log every system or environment change as a reproducible script or manifest (e.g., Dockerfile, requirements.txt, apt list) before executing it
- Prefer ephemeral, isolated environments for risky steps and ask for explicit permission before mutating the user's global system
- Create and attach a rollback or uninstall plan (commands and checks) for any non-trivial system alteration

## 19. Assuming user-specific dotfile contexts
- Detect platform, shell, and existing dotfile structure automatically and surface differences before editing any user-scoped config
- Ask explicit clarifying questions and produce a preview/patch and a backup of existing dotfiles prior to applying changes
- Make edits idempotent and scoped (e.g., append guarded blocks or create named include files) rather than overwriting whole files

## 20. Aggressive file pruning and deletions
- Present a concise candidate deletion list and require explicit user confirmation before removing files, offering a dry-run and size/age filters
- Move deletions to a timestamped quarantine directory or create compressed backups so recovery is trivial if a mistake occurs

Regularly revisit this document as new patterns emerge. The automation in this repository will refresh guidance when new sessions highlight fresh themes.

## Manual Reminders

<!-- manual-claude-guidance:start -->

- Always look at content as a whole, never ever take code out of context. Use repomix to package code neatly. If code is way too large, then use compress=true in repomix. Try to get exactly the files you need to package
- Use context7 for context
- Always write .MD plan/todo files to separate folder. If docs already exists, write it there, otherwise create one
- After you make significant changes, always engage the git commit specialist agent
- DONT ADD FALLBACKS
- When working on a new issue, create a new worktree and branch so that other agents do not conflict with your work in the same environment
- Never add fallbacks
- Never add "🤖 Generated with Claude Code" to PRs
- Never put "commited by agent" or "committed by claude code" -- same for PRs
- Don't write co-authored by Claude
- Always timestamp doc names. Follow conventions of the repo under docs repo
- Don't say things like "you're absolutely right!" or "my bad!". Be direct and communicate like a principal engineer. I don't want your fake attitude

<!-- manual-claude-guidance:end -->
