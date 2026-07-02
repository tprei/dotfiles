# Landing a session: push → PR → merge

For online repos (any remote whose URL begins with `https://`, `http://`, or `git@`), a typical orchestrator's landing flow runs:

1. `ensurePushedAndPRed(slug)`
   - `pushBranch(worktree, branch)` — `git push -u origin <branch>` from the worktree, where `origin` is the local bare clone, which itself has `origin → github.com/...`. Auth comes from the orchestrator's chosen mechanism: a GitHub App via askpass shim, the `gh` CLI's stored credentials, or an SSH key — whichever your orchestrator configures.
   - `ensurePullRequest({ ctx, slug })` — `gh pr create --title <title> --body ... --base <base> --head <branch> --repo <owner/repo>`. Persists the resulting PR on the session row.

2. `gh pr merge <number> --squash` — github does the merge. CI gates and conflict detection happen on github's side, which is what we want; doing the merge locally is brittle (the worktree's `origin/<base>` ref may not match github's HEAD).

3. After merge succeeds:
   - The orchestrator's restack logic walks all sessions whose `baseBranch === <landed branch>` and tries to rebase them. On conflict, spawns a `rebase-resolver` session and raises a `rebase-conflict` attention flag.
   - DAG nodes referencing the same base get the same treatment.

## Triggering a land

```
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"kind":"land","sessionSlug":"<slug>","strategy":"squash","force":true}' \
  "$ORCH_URL/api/commands"
```

`force: true` skips readiness when CI is still in progress; drop it when you want the merge to gate on green CI.

## What you can verify

After triggering land:

```
# Orchestrator log
tail -25 "$ORCHESTRATOR_LOG" | grep landing

# Session state
curl -s -H "Authorization: Bearer $TOKEN" "$ORCH_URL/api/sessions/<slug>" \
  | python3 -c 'import sys,json; s=json.load(sys.stdin); print("status:", s["status"]); print("pr:", s.get("pr"))'

# GitHub side
gh pr view <number> --json number,state,mergeCommit
gh run list --branch=<branch> --limit 5
```

## Common failures

| symptom | cause | fix |
|---|---|---|
| `failed to push <branch> to origin` | auth credentials didn't reach git over askpass; or branch already exists with diverged history | `gh auth status` to confirm credentials are good; for diverged branch `gh pr close <n> -d` and recreate |
| `gh pr create` fails with "could not find any commits between..." | branch matches base | the agent didn't actually commit; check `<workspace>/<slug>` |
| `gh pr merge` succeeds but local main lags | normal — `git pull --ff-only origin main` |
| CI red, `force: false` blocks land | readiness check failing on quality/ci | either fix the cause (re-dispatch a fix session), or `force: true` if you accept it |
| Test-orchestrator flakes on push event but passes on pull_request | concurrency cancelling the push run | not a real failure; check the pull_request run conclusion instead |

## DAG cascade (auto-restack on parent land)

If the orchestrator supports stacked DAGs, landing a parent should trigger restacking of children:

1. Spawn a multi-node DAG (A→B→C) via the orchestrator's DAG/ship API.
2. Land A (`POST /api/commands {kind:"land", sessionSlug:<A>, strategy:"squash", force:true}`).
3. Watch orchestrator logs: should emit `restacking child <B>` and trigger fetch + rebase in B's worktree.
4. If B has a clean rebase, B's branch is force-pushed and its PR base is updated.
5. On conflict: B gets `attention.kind === 'rebase-conflict'` and a `rebase-resolver` subsession spawns to fix it.

If this doesn't fire, check that the restack manager is actually being called. Most likely cause for "no restack" is that the children's `baseBranch` field on the session row doesn't match the landed parent's branch — verify with whatever query interface your orchestrator exposes (sqlite cli, REST endpoint, etc.).

## CI babysitter + auto-fix-CI

A typical orchestrator polls `gh pr checks <prNumber>` every 30s for sessions with open PRs. On any failed check it raises a `ci_failed` attention and, when an `ciAutoFix` runtime flag is enabled, spawns a `fix-CI` subsession with the failure logs in the prompt.

Toggle it via:

```
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"ciAutoFix": true}' \
  "$ORCH_URL/api/config/runtime"
```

A separate sidecar process commonly runs the same kind of policing as a parallel safety net for environments where the orchestrator's completion handlers are inert (host-sandbox case).
