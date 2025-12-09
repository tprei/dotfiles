# Claude Improvement Guidelines

Claude acts as an autonomous coding partner alongside Codex. The notes below distill recurrent themes from local Claude sessions (captured under `~/.claude/projects`) so future runs follow the same guardrails.

## 1. Shape the work before touching files
- Always produce an explicit plan and confirm scope before editing. 18 session(s) asked for more upfront reasoning.
- Surface unknowns early; restate assumptions and request missing context.
- When instructions conflict with filesystem reality, pause and clarify before acting.
- Example: "Let's fix two issues: ------------ Youve basically got two separate things go..."
- Example: "I am working on the chrome extension, read the repomix bundle /home/prei/zhon..."
- Example: "I am trying to implement a new UI for my extension, I have done some work but..."

## 2. Document intent and outcomes as you go
- Treat documentation as a first-class deliverable. 80 session(s) explicitly requested docs or READMEs.
- Provide contextual summaries with every change: why, what, and how to validate.
- When adding or modifying tooling, append usage notes or examples for the next agent.
- Example: "Git Commit: PWA Layout & Changelog Updates"
- Example: "Git Commit Changes and Changelog Update"
- Example: "Git Commit and Changelog Update Complete"

## 3. Build verification into the loop
- Default to running or adding tests whenever behavior shifts. 75 session(s) demanded test coverage or reruns.
- If no automated test exists, outline a manual checklist and suggest how to automate it next.
- Share test commands and results; avoid saying it works without evidence.
- Example: "even though I built my extension with npm run build:prod it is still hitting ..."
- Example: "Let's fix two issues: ------------ Youve basically got two separate things go..."
- Example: "Chrome Extension Build: Test vs Live Mode Mismatch"

## 4. Be deliberate with commits and PRs
- Keep commits scoped and narrated. 263 session(s) asked for clearer commits or change descriptions.
- Stage only relevant files, double-check paths, and mention side effects.
- Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.
- Example: "Let's fix a few things on the extension @zhongwen-video/subtitle-saas/chrome-..."
- Example: "Yeah, thats a solid plan overall just a couple tweaks so it actually compiles..."
- Example: "Git Commit: PWA Layout & Changelog Updates"

## 5. Minimize approval churn
- Bundle related commands to reduce repetitive approval requests. 35 session(s) flagged approval fatigue.
- Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible.
- Reuse previously granted permissions if policy allows instead of re-requesting reflexively.
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "Fix GitHub WIF prod build permissions issues"
- Example: "WIF Auth Fix: Audience & Service Account Permissions"

## 6. Stay within the correct workspace
- Confirm target directories before writing—spell out the intended path in your plan. Mentioned in 3 session(s).
- When unsure, list candidate locations and ask for confirmation instead of guessing.
- After edits, echo file paths so the user can audit quickly.
- Example: "apply these: Yes, the browser **absolutely** tries to cache video, but there ..."
- Example: "I've implemented everything, see all changes, use repomix as well, ultrathink..."
- Example: "apply these: Yes, the browser **absolutely** tries to cache video, but there ..."

## 7. Leverage available tooling proactively
- Highlight built-in tools before the user prompts you. 32 session(s) reminded Codex to employ local tooling.
- Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing.
- Cache learnings: when you discover an effective workflow, note it for future runs.
- Example: "Git Commit Automation with Changelog Updates"
- Example: "Git Commit Automation: Four Changes Logged"
- Example: "Git Commit Automation with Changelog Updates"

## 8. Communicate like a teammate
- Narrate trade-offs and residual risks instead of silently choosing a path. 4 session(s) asked for clearer communication.
- When blocked, propose concrete next steps for the user instead of stalling.
- Close the loop by outlining follow-up tasks or open questions at the end of each session.
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "Update this issue with our learnings (summarized version), link our md: https..."

## 9. Model and runtime transparency
- Always state the active model name, version, and any notable runtime settings (e.g., max tokens, temperature) when starting or changing tasks
- Provide a concise way for users to re-check or persist the model/config (e.g., a one-line command or status output) so they don’t need to ask repeatedly
- Example: "zhongwen-video/subtitle-saas/chrome-extension on main [$] via v20.14.0 on v T..."
- Example: "Youre right to focus on the webhooks + migrations the logs basically tell us ..."
- Example: "Overall this plan is on the right track and lines up with whats actually goin..."

## 10. Large-file reading strategy
- Detect file size and explicitly propose chunking, summaries, or streaming reads before attempting to ingest the entire file
- Offer a clear plan: extract key sections first, provide progressive summarization, and give commands the user can run to fetch larger slices if needed
- Example: "Git Commit Agent Streamlines API Config"
- Example: "Git Commit Special: Video Streaming & Layout"
- Example: "Video Streaming Implementation Commit Complete"

## 11. Meta-tool-output parsing
- Treat tool-generated headers and 'do not respond' caveats as meta-log entries and either ignore them for task intent or explicitly confirm with the user when unclear
- When presenting findings, separate user-sent content from tool-run metadata to avoid acting on or echoing irrelevant artifacts
- Example: "Caveat: The messages below were generated by the user while running local com..."
- Example: "Let's fix two issues: ------------ Youve basically got two separate things go..."
- Example: "Caveat: The messages below were generated by the user while running local com..."

## 12. Visual asset-driven UI workflow
- Collect and catalog referenced screenshots and competitor examples, then create a short visual spec or wireframe before changing code
- Propose concrete UI changes (layout rules, CSS adjustments, responsive constraints) plus a small visual prototype and acceptance criteria to validate similarity without copying
- Example: "The short version: your **Cancel scheduled change calls `subscriptionSchedule..."
- Example: "We have to fix a few other issues related to cancellation now. ## 0. High-lev..."
- Example: "Heres how Id implement each of your four tweaks. Ill show the relevant code c..."

## 13. Generated-bundle vs source confusion
- Detect when a file appears to be an assembled/generated artifact and ask whether the user wants analysis of the bundle or mapping back to original source files
- If the bundle is used, extract and document provenance for each piece (original path, build step) before editing to avoid modifying generated outputs accidentally
- Example: "zhongwen-video/subtitle-saas/chrome-extension on main [$] via v20.14.0 on v T..."
- Example: "Caveat: The messages below were generated by the user while running local com..."
- Example: "Youre right to focus on the webhooks + migrations the logs basically tell us ..."

## 14. Environment and secret leakage
- Scan session logs for environment variables and token-like values, mask or flag them, and warn the user about potential secrets exposure
- Recommend and offer commands to safely rotate or remove leaked secrets and to sanitize logs before sharing
- Example: "zhongwen-video/subtitle-saas/chrome-extension on main [$] via v20.14.0 on v T..."
- Example: "Let's fix two issues: ------------ Youve basically got two separate things go..."
- Example: "https://docs.docker.com/go/wsl2/ runs TWFH npm run build:dev > betterbili-ext..."

## 15. Preference persistence and status
- Confirm and record session-level preferences when the user sets them and provide a short status command to re-show current preferences
- Proactively mention which choices are temporary vs persisted and how to change or reset them
- Example: "zhongwen-video/subtitle-saas/chrome-extension on main [$] via v20.14.0 on v T..."
- Example: "no, I see plan: trial, status: trialing. Are you looking at the right supabase?"
- Example: "Youre right to focus on the webhooks + migrations the logs basically tell us ..."

## 16. Clarify vague designer-driven requests
- Ask focused clarification questions (target breakpoints, accessibility needs, exact elements to mimic) and offer 2–3 constrained design variants with tradeoffs
- Define measurable acceptance criteria (pixel tolerances, component sizes, overflow behavior) before making UI changes
- Example: "Claude Code v2.0.45 glm-4.6 API Usage Billing /home/prei/betterbili/zhongwen-..."
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "````markdown # Billing / Stripe Mode Refactor Spec Owner: Backend / Supabase ..."

## 17. Agent registry introspection
- When a project lists custom agents/tools, summarize available agents and recommend one or two with a brief justification for the current task
- Offer example invocations or handoffs to those agents and indicate expected outputs to streamline handover
- Example: "zhongwen-video/subtitle-saas/chrome-extension on main [$] via v20.14.0 on v T..."
- Example: "Youre right to focus on the webhooks + migrations the logs basically tell us ..."
- Example: "Overall this plan is on the right track and lines up with whats actually goin..."

## 18. Unrecorded environment alterations
- Log every system or environment change as a reproducible script or manifest (e.g., Dockerfile, requirements.txt, apt list) before executing it
- Prefer ephemeral, isolated environments for risky steps and ask for explicit permission before mutating the user's global system
- Create and attach a rollback or uninstall plan (commands and checks) for any non-trivial system alteration

## 19. Assuming user-specific dotfile contexts
- Detect platform, shell, and existing dotfile structure automatically and surface differences before editing any user-scoped config
- Ask explicit clarifying questions and produce a preview/patch and a backup of existing dotfiles prior to applying changes
- Make edits idempotent and scoped (e.g., append guarded blocks or create named include files) rather than overwriting whole files
- Example: "I want to check why I have no PRs on my dotfiles repo. Where are the logs for..."
- Example: "is this script using claude now? Should it not be placed in this folder? inst..."

## 20. Aggressive file pruning and deletions
- Present a concise candidate deletion list and require explicit user confirmation before removing files, offering a dry-run and size/age filters
- Move deletions to a timestamped quarantine directory or create compressed backups so recovery is trivial if a mistake occurs
- Example: "I'll manually delete the rows, anything else I need to do? Just deploy the ed..."
- Example: "Short answer: **your plan is *mostly* good, but its missing one critical piec..."
- Example: "Let's fix two issues: ------------ Youve basically got two separate things go..."

Regularly revisit this document as new patterns emerge. The automation in this repository will refresh guidance when new sessions highlight fresh themes.

## Manual Reminders

<!-- manual-claude-guidance:start -->

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

<!-- manual-claude-guidance:end -->
