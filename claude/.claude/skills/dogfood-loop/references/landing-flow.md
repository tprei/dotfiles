# Landing a session: push → PR → merge

For online repos (any remote whose URL begins with `https://`, `http://`, or `git@`), the engine's `landing/index.ts` runs:

1. `ensurePushedAndPRed(slug)`
   - `pushBranch(worktree, branch)` — `git push -u origin <branch>` from the worktree, where `origin` is the bare clone, which itself has `origin → github.com/...`. Auth comes from the GitHub App via the askpass shim (`ci/askpass.ts`) when `MINIONS_GH_APP_*` is set, otherwise from `gh` CLI's stored credentials.
   - `ensurePullRequest({ ctx, slug })` — `gh pr create --title <title> --body ... --base <base> --head <branch> --repo <owner/repo>`. Persists the resulting PR on the session row via `SessionRepo.setPr`.

2. `gh pr merge <number> --squash` — github does the merge. CI gates and conflict detection happen on github's side, which is what we want; doing the merge locally was brittle (the worktree's `origin/<base>` ref may not match github's HEAD).

3. After merge succeeds:
   - `RestackManager.restackChildren(slug)` walks all sessions whose `baseBranch === <landed branch>` and tries to rebase them. On conflict, spawns a `rebase-resolver` session and raises a `rebase-conflict` attention flag.
   - DAG nodes referencing the same base get the same treatment.

## Triggering a land

```
TOKEN=$(grep '^MINIONS_TOKEN=' .env.local | cut -d= -f2)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"kind":"land","sessionSlug":"<slug>","strategy":"squash","force":true}' \
  http://127.0.0.1:8787/api/commands
```

`force: true` skips readiness when CI is still in progress; drop it when you want the merge to gate on green CI.

## What you can verify

After triggering land:

```
# Engine log
tail -25 /tmp/engine.log | grep landing

# Session state
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8787/api/sessions/<slug>" \
  | python3 -c 'import sys,json; s=json.load(sys.stdin); print("status:", s["status"]); print("pr:", s.get("pr"))'

# GitHub side
gh pr view <number> --json number,state,mergeCommit
gh run list --branch=<branch> --limit 5
```

## Common failures

| symptom | cause | fix |
|---|---|---|
| `failed to push <branch> to origin` | GH App token didn't reach git over askpass; or branch already exists with diverged history | `gh auth status` to confirm App is installed; for diverged branch `gh pr close <n> -d` and recreate |
| `gh pr create` fails with "could not find any commits between..." | branch matches base | the agent didn't actually commit; check `.dev-workspace/<slug>` |
| `gh pr merge` succeeds but local main lags | `git pull --ff-only origin main` |
| CI red, `force: false` blocks land | readiness check failing on quality/ci | either fix the cause (re-dispatch a fix session), or `force: true` if you accept it |
| Test-engine flakes on push event but passes on pull_request | concurrency cancelling the push run | not a real failure; check the pull_request run conclusion instead |

## DAG cascade (auto-restack on parent land)

This is wired in `landing/restack.ts` but hasn't been exercised end-to-end yet in this repo's history. To demo:

1. Spawn a 3-node DAG (A→B→C) via `POST /api/sessions { mode:'ship' }` or via `/api/dags` if exposed.
2. Land A (`POST /api/commands {kind:"land", sessionSlug:<A>, strategy:"squash", force:true}`).
3. Watch engine logs: should emit `restacking child <B>` and trigger fetch + rebase in B's worktree.
4. If B has a clean rebase, B's branch is force-pushed and its PR base is updated.
5. On conflict: B gets `attention.kind === 'rebase-conflict'` and a `rebase-resolver` subsession spawns to fix it.

If this doesn't fire, check that `RestackManager.restackChildren` is actually being called (it is — at the end of `LandingManager.land`). Most likely cause for "no restack" is that the children's `baseBranch` field on the session row doesn't match the landed parent's branch — verify with:

```
sqlite3 .dev-workspace/engine.db "select slug, branch, base_branch from sessions where status not in ('cancelled','failed');"
```

## CI babysitter + auto-fix-CI

`ci/babysitter.ts` polls `gh pr checks <prNumber>` every 30s for sessions with open PRs. On any failed check it raises `attention.kind === 'ci_failed'` and, when `runtime.effective().ciAutoFix === true`, spawns a `fix-CI` subsession with the failure logs in the prompt.

Toggle it via:

```
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"ciAutoFix": true}' \
  http://127.0.0.1:8787/api/config/runtime
```

The sidecar (`@minions/sidecar`) runs the same kind of policing in a separate process — its `failedCiNoFix.ts` rule is a parallel safety net when `ciAutoFix` is off, or for environments where the engine completion handlers are inert (like the codex sandbox case).
