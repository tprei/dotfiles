---
name: jev-rubric-checklist
description: "Before a judge rubric runs: labels decidable from the state, facts computed in code, identical hits clustered, high-confidence audit planned"
condition:
  - "judge_batch\\("
  - "judgeBatch\\("
  - "\\bjudge\\("
  - "type\\W{1,8}(?:choice|bool|score)\\b"
scope: "tool:eval"
---

Check the rubric before jev sees any data. In the last repo-wide sweep, 62 of 144 verdicts were wrong, many at p ≥ 0.7, because the fact that decided them wasn't in the state.

- Can every label be decided from the state alone? If the deciding fact lives in another file (the callee records the error, a config loads the file, a caller validates), extract it into the state precisely, or read that category instead of judging it.
- Is any label a function of numbers you already computed (reference counts, path class)? Decide it in code. Jev ignored `uses_in_own_file_including_definition: 1` and called dead exports `internal_only` at p 0.71 to 0.89.
- Are hits with identical deciding evidence clustered, one state per cluster with every location listed?
- Does each state carry the evidence and stay under about 24k characters with long lines clipped?
- Is the audit planned: every error, every `p < 0.7`, and a random 3 per (category, label) above that? An overturn in a high-confidence sample means fix the state and re-judge the whole category.

Full workflow and tested cells: `skill://jev-sweep`.
