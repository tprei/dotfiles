# Claude Improvement Guidelines

Claude acts as an autonomous coding partner alongside Codex. The notes below distill recurrent themes from local Claude sessions (captured under `~/.claude/projects`) so future runs follow the same guardrails.

## 1. Shape the work before touching files
- Always produce an explicit plan and confirm scope before editing. 22 session(s) asked for more upfront reasoning.
- Surface unknowns early; restate assumptions and request missing context.
- When instructions conflict with filesystem reality, pause and clarify before acting.
- Example: "I am working on the chrome extension, read the repomix bundle /home/prei/zhon..."
- Example: "Based on the information gathered within @pages/session_20250920_152027 and t..."
- Example: "Whenever we click the hamburger menu there is a small flicker (the page shift..."

## 2. Document intent and outcomes as you go
- Treat documentation as a first-class deliverable. 91 session(s) explicitly requested docs or READMEs.
- Provide contextual summaries with every change: why, what, and how to validate.
- When adding or modifying tooling, append usage notes or examples for the next agent.
- Example: "First let's document this repo better. Within @artiffacts you'll see a lot of..."
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "Claude Code v2.0.1 Tips for getting started Welcome back Thiago! Run /init to..."

## 3. Build verification into the loop
- Default to running or adding tests whenever behavior shifts. 46 session(s) demanded test coverage or reruns.
- If no automated test exists, outline a manual checklist and suggest how to automate it next.
- Share test commands and results; avoid saying it works without evidence.
- Example: "Claude Code v2.0.1 Tips for getting started Welcome back Thiago! Run /init to..."
- Example: "<bash-stdout>> npx > create-playwright Getting started with writing end-to-en..."
- Example: "No fuck your test. I tried running it myself: wstill noithing. I'm in WSL as ..."

## 4. Be deliberate with commits and PRs
- Keep commits scoped and narrated. 107 session(s) asked for clearer commits or change descriptions.
- Stage only relevant files, double-check paths, and mention side effects.
- Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.
- Example: "First let's document this repo better. Within @artiffacts you'll see a lot of..."
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "perfect commit changes and push"

## 5. Minimize approval churn
- Bundle related commands to reduce repetitive approval requests. 58 session(s) flagged approval fatigue.
- Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible.
- Reuse previously granted permissions if policy allows instead of re-requesting reflexively.
- Example: "<command-name>/permissions</command-name> <command-message>permissions</comma..."
- Example: "Please analyze the current changes and create appropriate git commits for the..."
- Example: "If you believe current changes can be compacted into a commit, use the git co..."

## 6. Stay within the correct workspace
- Confirm target directories before writing—spell out the intended path in your plan. Mentioned in 0 session(s).
- When unsure, list candidate locations and ask for confirmation instead of guessing.
- After edits, echo file paths so the user can audit quickly.

## 7. Leverage available tooling proactively
- Highlight built-in tools before the user prompts you. 26 session(s) reminded Codex to employ local tooling.
- Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing.
- Cache learnings: when you discover an effective workflow, note it for future runs.
- Example: "I want to check why I have no PRs on my dotfiles repo. Where are the logs for..."
- Example: "Playwright is now installed so you can use it to browse. Let's try to go back..."
- Example: "I am working on a bot to schedule visa appointments under this URL: https://c..."

## 8. Communicate like a teammate
- Narrate trade-offs and residual risks instead of silently choosing a path. 31 session(s) asked for clearer communication.
- When blocked, propose concrete next steps for the user instead of stalling.
- Close the loop by outlining follow-up tasks or open questions at the end of each session.
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "This session is being continued from a previous conversation that ran out of ..."
- Example: "Are you able to make a document in @pages/README.md explaining everything fro..."

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
