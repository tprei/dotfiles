---
description: Run a deep read-only bug hunt. Prefer the shared deep-bug-hunt skill when available; otherwise emulate its workflow directly.
argument-hint: "[scope or focus]"
---

# Deep Bug Hunt

If the `deep-bug-hunt` skill is available, load or invoke it and follow it.

If the skill is not available, emulate the workflow directly:

- Treat any slash-command arguments or extra user guidance as the primary scope filter.
- Stay strictly read-only. Do not edit, stage, or commit anything.
- Map the surface first with `git ls-files`, recent `git log`, and current diff summaries before reading file contents.
- Slice the repo into independent, high-yield domains.
- Prefer a dedicated adversarial `enemy` agent for each slice. Otherwise use the strongest available read-only reviewer/explorer agent with an explicitly adversarial prompt.
- Run the slices in parallel when the current product supports parallel/background agents.
- Require evidence-backed findings with `file:line`, a small code quote or snippet, a concrete failure scenario, severity, and impact.
- Use second and third waves only where returned findings justify deeper digging.
- End with a severity-ranked report plus a coverage map and open questions.
