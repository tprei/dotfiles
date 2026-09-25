---
name: jev-sweep
description: Classify a repo-wide inventory (suppressions, casts, catches, dead-code findings, review hits) with omp's eval `judge_batch` (jev), audit the verdicts, and land the fixes as a stack of PRs. Use with `jevify`, deslop, or any sweep of 20+ homogeneous hits across a repo.
---

# Jev sweep

Jev sorts a few hundred units in about 2 seconds for under a cent. It's also confidently wrong whenever the fact that decides a unit lives outside the state you gave it. Put your effort into the state and the audit, not into hand-reading every hit.

The last run (dividimos deslop, 2026-09-25) judged 144 units (140 regex hits, 4 config blocks) for $0.006. The agent then overturned 62 verdicts (43%). Jev called 36 of 47 empty catches `slop`, and all 47 were legitimate. About 17 were `refresh*` or `markRead` calls whose callee already records or reconciles the failure (`trackedRead` stores it before rethrowing); the rest were test rollbacks, teardown, and best-effort cleanup. A ±8-line snippet shows none of that. Many wrong verdicts had p ≥ 0.7, so a `p < 0.7` escalation rule never saw them. The agent fixed that by hand-reading and overriding; the re-judge loop below is what it should have done.

Needs omp's `eval` tool: Python `judge_batch`, JavaScript `judgeBatch`. Code for each step is in `references/recipes.md`.

## 1. Inventory

1. Check `gh auth status` and push access before anything else, and tell the user right away if either is broken so they can fix it while you work. In dividimos the agent saw the dead token at the start, kept quiet, and later needed a 57-call pty session to submit.
2. Enumerate with structural tools as well as regex. Jev never sees what the scan missed. For TypeScript: `ast-grep` for type assertions and non-null assertions, knip for dead code, `tsc -p` for every tsconfig project. The dividimos regex caught `as unknown as` but missed `as never`, `x as string` on nullables, and `return data as T` in 15 files.
3. Pre-filter deterministically (prose files, already-strict settings) and count what you removed.
4. Print counts per category and nothing else until the rubric is frozen. In the second dividimos pass the agent read knip's output first and wrote the rubric around it.
5. Cluster hits whose deciding evidence is identical: same normalized line, same enrichment key (for a catch, the callee). Judge one state per cluster and list every location in it. Judged separately, `globalThis.fetch = fetchMock as unknown as typeof fetch;` at `mutations.test.ts:1385` and `:1478` got opposite verdicts (`slop` 0.52, `legitimate` 0.58).

## 2. Rubric

1. Every label must be decidable from the state alone. If the deciding fact lives in another file (the callee records the error, a config loads the file, a caller validates), put it in the state or don't judge that category.
2. Extract that evidence precisely or not at all. Use LSP `definition` when a server runs for the repo, or a per-category extractor you've checked by hand on 3 hits. In a smoke test on the omp repo, a name-grep extractor resolved `finally` to an unrelated prelude file and `emitSessionEvent` to an interface declaration. Wrong evidence is worse than none.
3. Compute facts in code and gate on them. A label that follows from numbers you already have (reference counts, path class, file kind) isn't a judge question. Given `uses_in_own_file_including_definition: 1` and no outside references, jev still labeled `requireAuth`, `withApiHandler`, `hasErrorCode`, and nine other dead exports `internal_only` at p 0.71 to 0.89.
4. Ask only what the state can answer. A `fix_scope` question over single-file snippets came back `local` for 142 of 144 units.
5. Size states for evidence, and clip. Jev rejects a branch past about 33k tokens (`max_tokens_exceeded`); a 24k-character state cap leaves room for the question. Clip every field, long lines included: in the smoke test a generated file with a 134k-character line, pulled in as evidence, overflowed two states. Count clipped and overflowing states.
6. Don't treat an `unclear` label as your safety net. Jev chose it 0 of 144 times in the slop pass, where nothing in a snippet hinted at the missing callee, and 22 of 118 in the dead-code pass, mostly for exports whose names showed up in other files. It fires when the state shows a doubt, not when the deciding fact is simply absent. Escalate by probability and by audit.

## 3. Judge and audit

1. Fire one batch over all clusters with every question in it. The batch outlives the cell; tabulate from `results()` and `failed()`, and keep each failure as an `ERROR` row.
2. Read every `p < 0.7` verdict and every error, plus a random sample of at least 3 high-confidence verdicts per (category, label).
3. One overturn in a high-confidence sample makes that bucket suspect. Overturns that cluster in one category mean the state is wrong, not that jev is noisy. Fix that category's extractor, rebuild its states, re-judge the whole category (it costs cents and seconds), and sample again. Any change to the questions themselves invalidates every verdict: re-judge everything. Don't re-roll unchanged states; in the smoke test an identical re-run flipped one verdict in 20, at p 0.55.
4. Record final verdicts in code with a reason per override. Report pre-filter removals, judge counts, final counts, the overturn count, and clipped states.

## 4. Slice

1. One PR per fix kind (typed globals, test doubles, decoders, one migration, dead files), each under the repo's per-PR line cap. The cap is per PR, not per commit; split an oversized slice at assembly (dead code went 1,275 lines into two PRs of 837 and 659).
2. Write the contract for shared files before fan-out: which slice owns which hunk, which exports must stay. With that in place, six parallel slices cherry-picked cleanly.
3. One worktree and one commit per slice from the same base, pre-commit hooks on. Hand each slice the exact fixes from the audit, not the verdict table. A slice that finds its fix is wrong stops and reports.
4. A fix can't introduce another slop kind from `deslop`'s catalog: a new cast, a runtime guard on an in-process value the types already cover, an error kind, code, or log event nothing consumes, or a test that passes whatever the unit returns. Data crossing a wire or process edge (RPC, HTTP, storage, `postMessage`) goes through the existing production decoder, not a new hand-rolled one. In dividimos the cast removals added `args as never` in a shared test helper, the one new cast of the stack.
5. Slices report the commit SHA, `git show --stat`, each verification command with its exit code, and every item deliberately left alone with evidence.
6. A subagent killed by a provider limit (429) leaves its worktree untouched or half done. Check `git status` there, then respawn the same spec under a new name.

## 5. Environment

1. `rg` with no path argument reads stdin when stdin isn't a TTY, so a kernel subprocess hangs until the 30 s cell timeout. Give every subprocess an explicit path, `stdin=DEVNULL`, and a timeout, plus `cwd=ROOT` when the repo isn't the session cwd (worktrees). Raise the cell's `timeout` for scans or run them in `bash` writing JSON.
2. An interrupted cell leaves half its definitions behind. Keep helpers in their own cell and re-run it after an interrupt.
3. Local services (database stacks, dev servers) may belong to other worktrees. Start your own with a separate project id and ports; never reset someone else's.
4. A symlinked `node_modules` works for `tsc`, lint, and vitest, but `next build` (Turbopack) rejects a symlink that points outside the project root. `npm ci --ignore-scripts` skips postinstall binaries such as the Supabase CLI. In dividimos `npm rebuild supabase` failed on the network; copying the pinned binary from another checkout of the same lockfile worked.

## 6. Assemble, submit, verify

1. Build the stack in a fresh worktree. `gt create` needs a checked-out branch, so create the first one with `git checkout -b <branch> && git commit`, then `gt track <branch> --parent main`. For each later slice: `git cherry-pick -n <sha> && gt create <branch> -m "$(git log -1 --format=%B <sha>)"`. Amend with `gt modify -a` so everything upstack restacks.
2. Verify each branch on its own (lint, typecheck, unit tests), then submit the stack; don't hold green branches for the end. With `gh`: `gt submit --stack --no-edit --publish` (`--draft` for a PR that must wait on a deploy), then `gh pr edit <n> --title <title> --body-file <file>` per PR. Without `gh`: run `gt submit --cli --edit` in a pty with `EDITOR` pointing at a script that copies prepared bodies.
3. Verify the tip in full: every suite, build, fresh database replay, generated-type diff. Run heavy suites one at a time; concurrent runs flaked twice in dividimos. Name any failing test before calling it a flake.
4. Run `enemy` on the submitted stack and don't amend while it reads; last time the branch moved mid-review. It caught a fix that only moved an error mask from SQL to the client, and the new `as never` cast. Fold findings in with `gt modify -a`, then submit again.
5. Before asking for review, check what the dividimos stack needed: repo gates that want a maintainer label (`trusted-ci-change` for CI and `package.json` changes) named in the PR body; a client change that depends on a new migration stacked on top as a draft, merged after the migration deploys; a contract change keeping a test of the old payload installed clients still send; a surfaced fault logging the error's `message` and `code`, not the object (`[object Object]`).
6. Re-scan on the tip and report before and after counts per category.

## References

| File | Contents |
|------|----------|
| `references/recipes.md` | Eval cells: safe scans, pre-filter, clustering with stable ids, state caps, judging, audit sampling, category re-judge |
