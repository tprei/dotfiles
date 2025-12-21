# Claude Improvement Guidelines

Claude acts as an autonomous coding partner alongside Codex. The notes below distill recurrent themes from local Claude sessions (captured under `~/.claude/projects`) so future runs follow the same guardrails.

## 1. Shape the work before touching files
- Always produce an explicit plan and confirm scope before editing. 17 session(s) asked for more upfront reasoning.
- Surface unknowns early; restate assumptions and request missing context.
- When instructions conflict with filesystem reality, pause and clarify before acting.
- Example: "I am working on the chrome extension, read the repomix bundle /home/prei/zhon..."
- Example: "I am trying to implement a new UI for my extension, I have done some work but..."
- Example: "I am trying to implement a new UI for my extension, I have done some work but..."

## 2. Document intent and outcomes as you go
- Treat documentation as a first-class deliverable. 64 session(s) explicitly requested docs or READMEs.
- Provide contextual summaries with every change: why, what, and how to validate.
- When adding or modifying tooling, append usage notes or examples for the next agent.
- Example: "Git Commit: PWA Layout & Changelog Updates"
- Example: "Git Commit Changes and Changelog Update"
- Example: "Home.tsx Pagination Commit & Changelog Update"

## 3. Build verification into the loop
- Default to running or adding tests whenever behavior shifts. 56 session(s) demanded test coverage or reruns.
- If no automated test exists, outline a manual checklist and suggest how to automate it next.
- Share test commands and results; avoid saying it works without evidence.
- Example: "I'm loading the catalog, e.g.: { "items": [ { "video_hash": "0d8d3d02509801d8..."
- Example: "Create a pull request from the current staging branch to the main branch. The..."
- Example: "can you please pull main and rebase these changes? theres some refresh bug th..."

## 4. Be deliberate with commits and PRs
- Keep commits scoped and narrated. 245 session(s) asked for clearer commits or change descriptions.
- Stage only relevant files, double-check paths, and mention side effects.
- Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.
- Example: "Git Commit: PWA Layout & Changelog Updates"
- Example: "Git Commit Changes and Changelog Update"
- Example: "Pull Request from Staging to Main"

## 5. Minimize approval churn
- Bundle related commands to reduce repetitive approval requests. 28 session(s) flagged approval fatigue.
- Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible.
- Reuse previously granted permissions if policy allows instead of re-requesting reflexively.
- Example: "<bash-stdout>commit 7bb058e4b9a815f41a16549473e1869f6f64ea4c Author: tprei <t..."
- Example: "Here is the implementation specification for the coding agent. ````markdown #..."
- Example: "cool but now we need the identity tag because we have google auth, help me ex..."

## 6. Stay within the correct workspace
- Confirm target directories before writing—spell out the intended path in your plan. Mentioned in 3 session(s).
- When unsure, list candidate locations and ask for confirmation instead of guessing.
- After edits, echo file paths so the user can audit quickly.
- Example: "apply these: Yes, the browser **absolutely** tries to cache video, but there ..."
- Example: "I've implemented everything, see all changes, use repomix as well, ultrathink..."
- Example: "apply these: Yes, the browser **absolutely** tries to cache video, but there ..."

## 7. Leverage available tooling proactively
- Highlight built-in tools before the user prompts you. 28 session(s) reminded Codex to employ local tooling.
- Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing.
- Cache learnings: when you discover an effective workflow, note it for future runs.
- Example: "Git Commit Automation with Changelog Updates"
- Example: "Git Commit Automation: Four Changes Logged"
- Example: "Git Commit Automation with Changelog Updates"

## 8. Communicate like a teammate
- Narrate trade-offs and residual risks instead of silently choosing a path. 2 session(s) asked for clearer communication.
- When blocked, propose concrete next steps for the user instead of stalling.
- Close the loop by outlining follow-up tasks or open questions at the end of each session.
- Example: "Update this issue with our learnings (summarized version), link our md: https..."
- Example: "Why? I mean this was already all implemented and working before our .ts migra..."

## 9. Model and runtime transparency
- Always state the active model name, version, and any notable runtime settings (e.g., max tokens, temperature) when starting or changing tasks
- Provide a concise way for users to re-check or persist the model/config (e.g., a one-line command or status output) so they don’t need to ask repeatedly
- Example: "Git Commit: API Configuration Centralization"
- Example: "Git Commit: API Configuration Streamlined"
- Example: "I'm loading the catalog, e.g.: { "items": [ { "video_hash": "0d8d3d02509801d8..."

## 10. Large-file reading strategy
- Detect file size and explicitly propose chunking, summaries, or streaming reads before attempting to ingest the entire file
- Offer a clear plan: extract key sections first, provide progressive summarization, and give commands the user can run to fetch larger slices if needed
- Example: "Video Player PR: Multi-Format Streaming Commit"
- Example: "Git Commit Agent Streamlines API Config"
- Example: "Git Commit Special: Video Streaming & Layout"

## 11. Meta-tool-output parsing
- Treat tool-generated headers and 'do not respond' caveats as meta-log entries and either ignore them for task intent or explicitly confirm with the user when unclear
- When presenting findings, separate user-sent content from tool-run metadata to avoid acting on or echoing irrelevant artifacts
- Example: "Caveat: The messages below were generated by the user while running local com..."
- Example: "Caveat: The messages below were generated by the user while running local com..."
- Example: "Caveat: The messages below were generated by the user while running local com..."

## 12. Visual asset-driven UI workflow
- Collect and catalog referenced screenshots and competitor examples, then create a short visual spec or wireframe before changing code
- Propose concrete UI changes (layout rules, CSS adjustments, responsive constraints) plus a small visual prototype and acceptance criteria to validate similarity without copying
- Example: "The "stupid" look in the screenshot is caused by a layout issue where the inn..."
- Example: "<bash-stdout>commit 7bb058e4b9a815f41a16549473e1869f6f64ea4c Author: tprei <t..."
- Example: "The styling in channel / space page is completely broken now, check out @scre..."

## 13. Generated-bundle vs source confusion
- Detect when a file appears to be an assembled/generated artifact and ask whether the user wants analysis of the bundle or mapping back to original source files
- If the bundle is used, extract and document provenance for each piece (original path, build step) before editing to avoid modifying generated outputs accidentally
- Example: "Caveat: The messages below were generated by the user while running local com..."
- Example: "Caveat: The messages below were generated by the user while running local com..."
- Example: "Caveat: The messages below were generated by the user while running local com..."

## 14. Environment and secret leakage
- Scan session logs for environment variables and token-like values, mask or flag them, and warn the user about potential secrets exposure
- Recommend and offer commands to safely rotate or remove leaked secrets and to sanitize logs before sharing
- Example: "<bash-stdout>commit 7bb058e4b9a815f41a16549473e1869f6f64ea4c Author: tprei <t..."
- Example: "apply these: Yes, the browser **absolutely** tries to cache video, but there ..."
- Example: "I need to commit the current changes to git. Based on the git status, there a..."

## 15. Preference persistence and status
- Confirm and record session-level preferences when the user sets them and provide a short status command to re-show current preferences
- Proactively mention which choices are temporary vs persisted and how to change or reset them
- Example: "<bash-stdout></bash-stdout><bash-stderr>From github.com:tprei/betterbili-land..."
- Example: "Analyze the current git status and changes to create an appropriate commit wi..."
- Example: "I need to commit the current changes in the betterbili-landing-studio reposit..."

## 16. Clarify vague designer-driven requests
- Ask focused clarification questions (target breakpoints, accessibility needs, exact elements to mimic) and offer 2–3 constrained design variants with tradeoffs
- Define measurable acceptance criteria (pixel tolerances, component sizes, overflow behavior) before making UI changes
- Example: "<bash-stdout>commit 7bb058e4b9a815f41a16549473e1869f6f64ea4c Author: tprei <t..."
- Example: "Heres a straight review of your implementation plan, phase by phase, plus a f..."
- Example: "Claude Code v2.0.45 glm-4.6 API Usage Billing /home/prei/betterbili/zhongwen-..."

## 17. Agent registry introspection
- When a project lists custom agents/tools, summarize available agents and recommend one or two with a brief justification for the current task
- Offer example invocations or handoffs to those agents and indicate expected outputs to streamline handover
- Example: "I'm loading the catalog, e.g.: { "items": [ { "video_hash": "0d8d3d02509801d8..."
- Example: "The "stupid" look in the screenshot is caused by a layout issue where the inn..."
- Example: "Cool can you make the refresh button have some sort of feedback (maybe color ..."

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
- Example: "Git Commit Changes with Code Cleanup"
- Example: "DONT DELETE BRANCH"
- Example: "Git commit cleanup and push"

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
