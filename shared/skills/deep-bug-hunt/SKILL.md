---
name: deep-bug-hunt
description: Ultra-deep read-only bug hunt across a codebase using adversarial agent slices in parallel. Use when the user asks to hunt bugs, find everything wrong, do a deep dive, or wants a broad pre-release audit without making changes.
---

# Deep Bug Hunt

Run an ultra-deep adversarial sweep. Stay read-only, fan out when the current tool supports parallel agents, and aggregate the findings into a severity-ranked report.

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

### Phase 2 — Dispatch wave 1

For each domain slice, launch one read-only adversarial agent.

- Prefer the dedicated `enemy` agent when available.
- Otherwise use the strongest available reviewer/explorer agent with an explicitly adversarial prompt.
- Use background or parallel execution when the current product supports it.
- Do not override agent model defaults unless the current product requires explicit model selection.

Each child prompt must:
- Name the exact files to read end-to-end.
- List the bug categories to look for: races, leaks, off-by-one errors, inversions, validator gaps, state machine violations, bad contracts, security gaps, and missing failure handling.
- Require `file:line + code snippet + scenario + severity` for each finding.
- Ask for 6–15 concrete issues when available.
- Forbid code changes.

If the current product has a task tracker, use it to track slices and follow-ups. Otherwise keep the coverage map in chat.

### Phase 3 — Wait; never poll

Do not busy-poll. Wait for completion notifications or check in only when you need results for synthesis. When an agent finishes:
1. Record its high-severity findings.
2. Record anything it could not verify.
3. Queue follow-up passes for whatever it flagged as worth deeper digging.

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

- **Never make code changes** — this skill is strictly read-only.
- The parent agent dispatches and aggregates; child agents read and report.
- Prefer dedicated adversarial agents over generic explorers.
- Each child prompt must include concrete file paths and specific bug categories — terse prompts produce shallow work.
- Run for hours if needed: if all agents finish and elapsed time is short, dispatch a new wave on untouched files or unexplored matrix combinations.
