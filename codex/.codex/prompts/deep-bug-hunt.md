---
description: Ultra-deep adversarial sweep of a codebase via many parallel enemy subagents. Read-only — never makes code changes.
argument-hint: [TARGET="<dir, path, or empty for cwd>"] [DURATION="<target wall-clock, e.g. 2h>"]
---

# Deep Bug Hunt

Orchestrate a multi-wave adversarial sweep. Dispatch many `enemy` subagents in parallel against non-overlapping slices of the codebase, then aggregate their findings into a severity-ranked report.

Target: $TARGET
Target duration: $DURATION

If `$TARGET` is empty, assume the current working directory. If `$DURATION` is empty, ask: "Target wall-clock for this sweep (e.g. `30m`, `2h`, `until exhausted`)?"

## When to use

- User asks to "hunt bugs", "find everything wrong", or "deep dive"
- User wants long-running exploration without making changes
- Post-feature audit before a major release
- Security review of a large, unfamiliar codebase

## Execution flow

### Phase 0 — Map the surface (main agent only, no file reads)

Run:
```bash
git ls-files
git log --oneline -20
```

Group files by domain. Don't read file contents yet — map only:

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

### Phase 1 — Slice into 10–20 domains

Identify non-overlapping slices. Use these axes:

- **By layer**: app / persistence / transport / plugins / UI / supervisor
- **By concern**: concurrency / error handling / security / resource leaks / contract drift / state machine
- **By recent commits**: whatever landed in the last week — highest bug yield
- **By user-flow × edge-condition matrix**: create × disconnect, retry × quota, switch × in-flight
- **By test audit**: buggy tests + coverage gaps

### Phase 2 — Dispatch wave 1 (all parallel)

For each domain slice, spawn one `enemy` subagent. The subagent's TOML already pins `model_reasoning_effort = "xhigh"` and `sandbox_mode = "read-only"` — do not override.

Each dispatch prompt MUST include:
- The exact files to read end-to-end (no guessing, no `*` globs)
- The bug categories to look for: races, leaks, off-by-one errors, inversions, validator gaps, state machine violations, hallucinated APIs, missing handling, security holes, perf/resource issues
- Required output format: `file:line + code snippet + scenario + severity` for each finding
- A floor: ask for 6–15 concrete issues
- An explicit ban on code changes ("read-only — return findings only")

Dispatch as many subagents in parallel as the runtime allows. Do not serialize.

### Phase 3 — Wait; never poll

When a subagent reports back, capture its final summary verbatim (never re-read its transcript — those overflow context). Extract:
1. Severity-bucketed findings
2. Domains the agent flagged as worth a deeper dive
3. Anything the agent said it could not verify

### Phase 4 — Second and third waves

After wave 1 returns, dispatch targeted waves:
- Cross-cutting concerns (contract drift, state machine consistency, error-handling consistency)
- Recent feature deep-dives (last 3–5 commits)
- Deep-dives on the highest-severity findings from wave 1
- Any domains not yet touched
- "What I could not verify" items rolled up from wave 1 outputs

Keep dispatching new waves until elapsed time approaches `$DURATION` or coverage saturates (three consecutive waves produce no new critical/high findings).

### Phase 5 — Aggregate and report

Produce a single severity-ranked report:

```markdown
# Deep bug hunt — $TARGET

Total waves: <N>
Total subagents: <N>
Elapsed: <hh:mm>

## Critical
- [file:line] Description — scenario — impact — discovered by wave <N>

## High
...

## Medium
...

## Low / informational
...

## Coverage map
| Domain | Files swept | Subagents | Findings (C/H/M/L) |
|--------|-------------|-----------|--------------------|
| ...    | ...         | ...       | ...                |

## Open questions
Items that subagents flagged as suspicious but could not confirm.
```

Group findings by domain within each severity bucket. Cite `file:line` for every entry.

## Key constraints

- **Never make code changes** — this prompt is strictly read-only, top to bottom
- Main agent dispatches and aggregates; subagents read
- Use the `enemy` subagent for adversarial framing — `explorer` is too shallow for this
- Each subagent prompt must include concrete file paths and specific bug categories — terse prompts produce shallow work
- Run for the full `$DURATION`: if all subagents finish and elapsed time is short, dispatch a new wave on untouched files or unexplored matrix combinations
- Do not summarize subagent transcripts mid-flight — work from each agent's final report only
