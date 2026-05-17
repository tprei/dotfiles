---
name: deep-bug-hunt
description: Ultra-deep adversarial sweep of a codebase via many parallel enemy subagents. Use when the user asks to "hunt bugs", "find everything wrong", "deep dive", or wants hours-long exploration without making changes.
model: opus
allowed-tools: Agent Bash(git ls-files:*) Bash(git log:*) Bash(git diff:*) Bash(rg:*) Glob Grep Read TaskCreate TaskUpdate TaskList TaskGet
user-invocable: true
disable-model-invocation: false
effort: max
---

# Deep Bug Hunt

Ultra-deep adversarial sweep via many parallel enemy subagents. Read-only — never makes code changes.

## When to use

- User asks to "hunt bugs", "find everything wrong", or "deep dive"
- User wants hours-long exploration without making changes
- Post-feature audit before a major release
- Security review of a large, unfamiliar codebase

## Instructions

### Phase 0 — Map the surface

Run `git ls-files` and `git log --oneline -20` to understand file layout and recent changes. Group files by domain:

- App layer (business logic, services, controllers)
- Persistence (DB models, migrations, queries)
- Transport (HTTP handlers, WebSocket, queues)
- Plugins / integrations (third-party SDKs)
- UI / frontend (components, state, forms)
- Hooks / middleware (auth, logging, validation)
- PWA / workers (service workers, caching)
- Scripts / infra (build, deploy, CI)
- Tests (coverage, correctness, contract)
- Shared (utils, types, constants)

Do not read file contents yet — map only.

### Phase 1 — Slice into 10–20 domains

Identify non-overlapping slices. Use these axes:

- **By layer**: app / persistence / transport / plugins / UI / supervisor
- **By concern**: concurrency / error handling / security / resource leaks / contract drift / state machine
- **By recent commits**: whatever landed in the last week — highest bug yield
- **By user-flow × edge-condition matrix**: create × disconnect, retry × quota, switch × in-flight
- **By test audit**: buggy tests + coverage gaps

### Phase 2 — Dispatch wave 1 (all parallel, all background)

For each domain slice, spawn one subagent with:
- `subagent_type: enemy`
- `model: opus`
- `run_in_background: true`
- A prompt that:
  - Names the exact files to read end-to-end (no guessing)
  - Lists the bug categories to look for: races, leaks, off-by-one errors, inversions, validator gaps, state machine violations, etc.
  - Demands `file:line + code snippet + scenario + severity` for each finding
  - Asks for 6–15 concrete issues
  - Forbids code changes

Track each with `TaskCreate`. Set owner = agent ID. One task per agent.

### Phase 3 — Wait; never poll

Do not poll. Wait for background completion notifications. When an agent finishes:
1. Mark its task completed via `TaskUpdate`
2. Extract high-severity findings from its summary
3. Queue follow-up agents on whatever it flagged as worth digging into

### Phase 4 — Second and third waves

After wave 1 returns, dispatch targeted waves:
- Cross-cutting concerns (contract drift, state machine consistency)
- Recent feature deep-dives (last 3–5 commits)
- Deep-dives on the highest-severity findings from wave 1
- Any domains not yet touched

Keep dispatching until elapsed time approaches the target or coverage saturates.

### Phase 5 — Aggregate and report

Collect each agent's final summary (never read transcripts directly — they overflow context). Produce a severity-ranked report:

```
## Critical
- [file:line] Description — scenario — impact

## High
...

## Medium
...

## Low / Informational
...
```

Group by domain, sort by severity within each group. Include a coverage map showing which domains were swept and how many agents ran each wave.

## Key constraints

- **Never make code changes** — this skill is strictly read-only
- Main agent dispatches and aggregates; subagents read
- Use `enemy` subagent type for adversarial framing — `Explore` is too shallow for this
- Background mode + completion notifications, never polling
- Each subagent prompt must include concrete file paths and specific bug categories — terse prompts produce shallow work
- Run for hours if needed: if all agents finish and elapsed time is short, dispatch a new wave on untouched files or unexplored matrix combinations
