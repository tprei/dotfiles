---
name: deep-bug-hunt
description: Ultra-deep read-only bug hunt across a codebase using adversarial agent slices in parallel. Use when the user asks to hunt bugs, find everything wrong, do a deep dive, or wants a broad pre-release audit without making changes.
---

# Deep bug hunt

A read-only adversarial sweep: slice the codebase, fan out parallel agents, aggregate a severity-ranked report. Never change code. The parent dispatches and aggregates; children read and report.

## 0. Map

`git ls-files` and `git log --oneline -20`. Group files by bounded context and layer (domain logic, persistence, transport, integrations, UI, middleware, workers, scripts and infra, tests, shared). Don't read contents yet.

## 1. Slice into 10 to 20 non-overlapping domains

Cut along whichever axes yield most:
- bounded context and layer
- concern: concurrency, error handling, security, leaks, contract drift, state machines, domain invariants and boundary leaks
- recent commits (last week yields the most bugs)
- user flow × edge condition (create × disconnect, retry × quota, switch × in-flight)
- test audit: buggy tests and coverage gaps

## 2. Wave 1

One read-only adversarial agent per slice, in parallel. Prefer `enemy`; otherwise the strongest reviewer or explorer with an adversarial prompt. Keep agent model defaults unless the product requires a choice. Each prompt:
- names exact files to read end to end
- lists categories: races, leaks, off-by-one, inversions, validator gaps, state machine violations, broken contracts and invariants, security gaps, missing failure handling
- requires `file:line`, snippet, scenario, and severity per finding
- asks for 6 to 15 concrete issues
- forbids code changes

Track slices in the task tracker if there is one, otherwise in chat.

## 3. Wait, never poll

On each completion, record high-severity findings, unverified items, and follow-ups worth digging into.

## 4. Later waves

Cross-cutting concerns (contract drift, state consistency), the last 3 to 5 commits, deep dives on the worst wave-1 findings, and untouched domains. Keep dispatching until time runs out or coverage saturates; run for hours if needed.

## 5. Report

Use each agent's final summary, never raw transcripts. Group by domain, sort by severity, and end with a coverage map (domains swept, agents per wave).

```
## Critical
- [file:line] Description, scenario, impact
## High
## Medium
## Low / Informational
```
