# Codex Improvement Guidelines

Codex acts as an autonomous coding partner. The notes below distill common issues spotted across past sessions in `~/.codex/history.jsonl` and turn them into guardrails that apply to any repo.

## 1. Shape the work before touching files
- Always produce an explicit plan and confirm scope before editing. 15 session(s) asked for more upfront reasoning.
- Surface unknowns early; restate assumptions and request missing context.
- When instructions conflict with filesystem reality, pause and clarify before acting.
- Example: "Can you reason deeply about everything within @video-miner including director..."
- Example: "Let's work on a bug related to bad subtitle burning. I've just ran a job (you..."
- Example: "Check most recent changes. Something is wrong when converting to audio. Think..."

## 2. Document intent and outcomes as you go
- Treat documentation as a first-class deliverable. 28 session(s) explicitly requested docs or READMEs.
- Provide contextual summaries with every change: why, what, and how to validate.
- When adding or modifying tooling, append usage notes or examples for the next agent.
- Example: "Cool can you write a README within video-miner folder so it can be used by co..."
- Example: "Where can I find docs for this alignment stuff? Sure let's implementing that ..."
- Example: "Sure implement. Also can you add a CHANGELOG to video-miner where things are ..."

## 3. Build verification into the loop
- Default to running or adding tests whenever behavior shifts. 24 session(s) demanded test coverage or reruns.
- If no automated test exists, outline a manual checklist and suggest how to automate it next.
- Share test commands and results; avoid saying it works without evidence.
- Example: "Can you make this change and document all of this including the change and fo..."
- Example: "Just to not confuse you: I also ran a second job with all burned in subs (man..."
- Example: "no. even after the changes it's stalling a lot after less than 300 MB, see th..."

## 4. Be deliberate with commits and PRs
- Keep commits scoped and narrated. 25 session(s) asked for clearer commits or change descriptions.
- Stage only relevant files, double-check paths, and mention side effects.
- Draft changelog-ready notes so follow-up agents inherit context without rereading diffs.
- Example: "it actually looks much much better and positioning of the subs are finally go..."
- Example: "First commit changes, I'll look into this later"
- Example: "do you see @changelog.md ? This file should not be ignored. We have an issue ..."

## 5. Minimize approval churn
- Bundle related commands to reduce repetitive approval requests. 6 session(s) flagged approval fatigue.
- Cite why elevated permissions are needed; suggest safe, sandboxed alternatives when possible.
- Reuse previously granted permissions if policy allows instead of re-requesting reflexively.
- Example: "Before that, I made some changes, take a look: ●User approved Claude's plan: ..."
- Example: "No. Use pydoll to solve the captcha https://github.com/autoscrape-labs/pydoll..."
- Example: "> - Jobs tab “Download” button: the popup fetches /subtitles/job/{id} expecti..."

## 6. Stay within the correct workspace
- Confirm target directories before writing—spell out the intended path in your plan. Mentioned in 1 session(s).
- When unsure, list candidate locations and ask for confirmation instead of guessing.
- After edits, echo file paths so the user can audit quickly.
- Example: "I want to build something quite simple: There is a file in my home: $HOME/.co..."

## 7. Leverage available tooling proactively
- Highlight built-in tools before the user prompts you. 20 session(s) reminded Codex to employ local tooling.
- Prefer existing scripts or automation hooks over ad-hoc commands; update or create helpers when they are missing.
- Cache learnings: when you discover an effective workflow, note it for future runs.
- Example: "So the burning happened: Docker logs"
- Example: "Let's work on a bug related to bad subtitle burning. I've just ran a job (you..."
- Example: "zhongwen on  translation-stuff [⇡$!] on 🐳 v27.5.1 using ☁️ default/zhongwen-..."

## 8. Communicate like a teammate
- Narrate trade-offs and residual risks instead of silently choosing a path. 13 session(s) asked for clearer communication.
- When blocked, propose concrete next steps for the user instead of stalling.
- Close the loop by outlining follow-up tasks or open questions at the end of each session.
- Example: "Check the whole credits system. Can you find ways to optimize it and implemen..."
- Example: "Check the whole credits system. Can you find ways to optimize it and implemen..."
- Example: "Check the whole credits system. Can you find ways to optimize it and implemen..."

Regularly revisit this document as new patterns emerge. The automation in this repository will refresh guidance when new sessions highlight fresh themes.

# Callouts

- DO NOT IMPLEMENT FALLBACKS. If you are unsure how to do something or something isn't working, avoid quick hacks like mocked data or assuming functionality is impossible; pause and surface the blocker instead.
- Prefer rg (ripgrep) over grep for searching.
- Leverage MCP tools—including Serena and Repomix—before resorting to manual spelunking.
