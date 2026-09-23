---
name: dogfood-loop
description: Drive a running agentic orchestrator (a service that spawns parallel coding-agent sessions on a target repo) to fix or extend that repo by dispatching sessions, applying their diffs to the main branch, verifying through tests and UI checks, and (for online repos) pushing/landing PRs. Use when the user says "dogfood", "use the local orchestrator", or wants to iterate on a repo via dispatched sessions rather than direct edits.
---

# Dogfood loop

Drive a running orchestrator to fix or extend a target repo: dispatch parallel sessions, apply their diffs to main, verify, optionally land PRs, iterate.

Assumes a local orchestrator with an HTTP dispatch API (`POST /api/sessions { repoId, baseBranch, mode, prompt }` returns a slug), one git worktree per session (`$WORKSPACE/<slug>/`), and a `repoId` bound to the target repo. Placeholders (`$ORCH_URL`, `$TOKEN`, `$REPO_ID`, `$WORKSPACE`, `$BUILD`, `$TYPECHECK`, `$TEST`, `$E2E`, `$LINT`) come from the orchestrator's config.

Use when the user says "dogfood", "use it on itself", or "run a loop", the orchestrator is up with `$REPO_ID` bound, and you have 2 or more non-overlapping fixes. Skip when the orchestrator is down or a change spans too many subsystems for one session.

## Dispatch-only rule

When the target repo is the orchestrator's own source, every change goes through a dispatched session: small tweaks, obvious CI fixes, and fixes you already know included. Before any edit to its source, ask "did this come from an applied agent diff (copied from `$WORKSPACE/<slug>/` per `references/apply-diffs.md`)?" If not, dispatch.

Direct edits on main are allowed only for `.gitignore` additions, local memory or notes (`MEMORY.md`, scratch logs), and operational doc detour entries. When the orchestrator and target are different repos, the rule covers only the target.

Direct edits poison the loop: they skip the architectural rejection rules, drift main from the bases sessions branch from, add no regression guard, and misrepresent what the system built.

Reject these rationalizations: "it's small", "the fix is obvious", "I know what changed" (the guard is the value), "it'd be a stale-base diff" (fix the base, then dispatch), "it's taking too long" (wait, or re-dispatch narrower), "I'll follow up" (queue it).

Bootstrap exception: edit orchestrator source directly only when no session can reach `running`: sessions sit `pending` over 60s and get swept; boot fails (`SyntaxError`, unkillable `EADDRINUSE`, instant OOM); every spawn fails auth (`Not logged in`); or every diff returns as a patch fallback with the same readonly-gitdir error. It ends the moment this probe passes (status `completed` and `turns>0`):

```
curl -sX POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"probe","repoId":"'"$REPO_ID"'","baseBranch":"main","mode":"task",
       "prompt":"Run the project typecheck and report the exit code. Do not edit any files."}' \
  "$ORCH_URL/api/sessions"
# poll /api/sessions/<slug>
```

## Environment check

```
curl -s -o /dev/null -w "orchestrator HTTP %{http_code}\n" "$ORCH_URL/api/health"
curl -s -o /dev/null -w "web HTTP %{http_code}\n"          "${WEB_URL:-http://127.0.0.1:5173}/"
ss -tlnp 2>/dev/null | grep -E "<orchestrator-port>|<web-ports>"
# Zombies: etime >= 04:00:00 or DD-HH:MM:SS is leaked; kill -9 it.
ps -eo pid,etime,cmd | awk '/(test|run dev|tsx watch|vite)/ && !/awk/ { print }' | head
```

- Restart a down orchestrator with the project's start script (template: `references/restart-engine.sh`).
- After `git pull`, rebuild shared packages the orchestrator imports at runtime. `does not provide an export named '<X>'` means stale `dist/`; rebuild, never revert. Bake the rebuild into the start script.
- The operator launches the orchestrator, not you. Launched from an agentic shell, every sub-agent inherits its sandbox and can't write its gitdir.

## Pre-dispatch gates (every batch)

```
# 1. Main CI green (completed + success). Red main poisons every diff.
gh run list --branch main --limit 1

# 2. Bare clone main == working main, or every session reverts recent work.
BARE="$WORKSPACE/.repos/$REPO_ID.git"
test "$(git -C "$BARE" rev-parse main)" = "$(git rev-parse main)" \
  || git -C "$BARE" fetch origin main:main --force

# 3. No two sessions in a batch touch the same file; sequence them instead.

# 4. No duplicate route or plugin registrations (frameworks silently drop one). Output must be empty:
rg -n "app\.(get|post|patch|delete)\(['\"]/api" src/ | awk -F'"' '{print $2}' | sort | uniq -d

# 5. Orchestrator not launched from an agentic CLI:
ORCH_PID=$(pgrep -f "<your-orchestrator-cmd-pattern>" | head -1)
[ -n "$ORCH_PID" ] && ps -p $(awk '/^PPid:/ {print $2}' /proc/$ORCH_PID/status) -o cmd= \
  | grep -qE 'claude|claude-code|codex' \
  && echo "ORCHESTRATOR INHERITED AGENTIC SANDBOX: ask operator to relaunch from their terminal" && exit 1

# 6. Stop sessions pending > 120s (POST /api/commands {kind:"stop", sessionSlug}):
curl -sH "Authorization: Bearer $TOKEN" "$ORCH_URL/api/sessions" | python3 -c '
import json,sys,datetime
now=datetime.datetime.now(datetime.timezone.utc)
for s in json.load(sys.stdin)["items"]:
    if s["status"]=="pending" and (now-datetime.datetime.fromisoformat(s["createdAt"].replace("Z","+00:00"))).total_seconds()>120:
        print("STUCK:", s["slug"])'
```

## Loop

1. Audit with Playwright or `curl`: desktop and mobile, dark and light, every relevant view; screenshots in `.playwright-mcp/`. For layout bugs, read computed styles with `browser_evaluate`; headless screenshots can mislead. Reproduce every operator-reported bug as a failing click/evaluate sequence before dispatch; that sequence becomes the prompt's Do step and the regression test's setup. Can't reproduce: ask. Operator pastes (logs, screenshots, transcripts) are ground truth over API responses; file the implied bug immediately. Expect about one orchestrator bug per two features.
2. Group fixes into 4 to 6 sessions, each owning one coherent area. Overlapping files cause last-writer-wins reverts, the most expensive failure here.
3. Write tight prompts from `references/dispatch-prompt-template.md`: exact files in scope, the verify commands, an explicit commit command (sandboxes often break auto-commit), "don't run dev servers" when code hot-reloads, and a non-default port for any e2e or dev server.
4. Dispatch: `POST $ORCH_URL/api/sessions` with `{ title, repoId, baseBranch: "main", mode: "task", prompt }` and `Authorization: Bearer $TOKEN`. Print every slug.
5. Wait in the background (async shell `until` loop or an agent), never by foreground polling; cap most sessions around 30 minutes. `failed turns=0` means killed at bootstrap: re-dispatch. `failed turns>50` hit a wall: read the last transcript events (usually quota or sandbox). Monitor hygiene:
   - Cancel monitors for stopped sessions.
   - Parse transcripts with Python `json.load`; `jq` dies on control characters and fakes a failure.
   - Check reply injection by searching the whole transcript after the reply timestamp for the tag.
   - "Out of usage / resets HH:MM" is a hard stop: schedule a wakeup near reset, don't retry.
6. Inspect each diff before applying (`references/apply-diffs.md`). Agents' `git add .` captures injected assets (`AGENTS.md`, `CLAUDE.md`, `.cursor/`, `instructions.md`); `.git/info/exclude` is unreliable, so filter at apply time.
7. Apply, verify, commit, push:
   ```
   $INSTALL                 # only if the manifest changed
   $BUILD_SHARED_PACKAGES
   $TYPECHECK
   $TEST                    # the regression test must pass
   $WEB_BUILD               # if e2e serves built output
   $E2E                     # mandatory for UI changes; typecheck misses selector drift
   #   First: rg "data-testid|getByRole|getByText|locator\(" e2e/*.spec.ts and fix specs
   #   touching renamed or removed UI. Rect assertions must measure the changing element, not a wrapper.
   $LINT
   git add -A && git -c user.email=local@dogfood -c user.name=local commit -q -m "<subject> (via session <slug>)"
   git push origin main
   gh run watch             # red CI: fix before the next dispatch
   ```
8. Recycle the orchestrator if its source changed; watch mode is unreliable across rapid edits (`references/restart-engine.sh`).
9. Verify the flow, not the pixels, after a hard reload (`Ctrl+Shift+R`):
   - Always: 1440×900 and 390×844; console clean except known dev warnings; every reported bug's reproduction now passes.
   - Controls: click every control on the changed surface and assert its effect (close buttons close). Drag handles ±200 px and assert the bound element's `getBoundingClientRect().width` changes by about 200. Resizable panels at min and max must differ visibly.
   - Event-union views: every event kind has a `case` arm (missing arms render blank); seed a session with every kind and check each renders.
   - New session: the detail panel mounts into a spinner immediately, and the first streamed event renders without a reload.
   - Filters: each option's row count matches the equivalent `curl '/api/...?<filter>'`.
   - Multi-turn input: mid-turn, `await page.locator('textarea').first().isDisabled()` is `false`; submit through the UI, not the API.
   - Flex and grid: list scroll containers with `[...document.querySelectorAll('*')].filter(c => /auto|scroll/.test(getComputedStyle(c).overflow)).map(c => `${c.tagName}.${c.className}: ${getComputedStyle(c).overflow}`)` at 320×568, 768×1024, and 1440×900; only intended containers scroll (not tab strips, headers, or pill rows).
   - Realtime: on a resource with zero events, a triggered update appears without refresh.
   - Read-only modes: `git -C "$WORKSPACE/<slug>" diff --stat` is empty and `status --short` shows only injected assets. The regression test asks a read-only session to modify a file and asserts no diff.
   - Reply injection: post `echo back this token: $TAG` via `POST $ORCH_URL/api/commands {"kind":"reply","sessionSlug":"$SLUG","text":...}` with `TAG="reply-probe-$(date +%s)"` and assert a later `assistant_text` contains it. Presence in the transcript alone proves nothing.
   - Every "mode X must not Y" constraint is an assertion in its regression test.
10. Online repos: land via `references/landing-flow.md`. `POST /api/commands {kind:"land", sessionSlug, strategy:"squash", force:true}` pushes, opens the PR, and merges (`force` skips readiness while CI runs); confirm with `gh pr view <n> --json state,mergeCommit`. Stacked children auto-close when `--delete-branch` removes their base; recover with `references/restack-after-merge.md`. Prefer flat DAGs targeting `main` unless a node semantically depends on its parent; shared types go in a shared package, not a stack.
11. Record failed session patterns (refusing to commit, readonly sandbox, parallel conflicts, env files eaten by shell sourcing) as feedback memory in the project memory dir.

## Hazards

| Symptom | Cause | Fix |
|---|---|---|
| `EADDRINUSE` on restart | watch mode leaked a listener | `pkill -9 -f "<orchestrator-cmd-pattern>"`; `ss -tlnp \| grep <port>` empty before relaunch |
| `turns=0` failures after recycle | killed mid-spawn | re-dispatch |
| `GIT_EDITOR not permitted` in auto-commit audit | host sandbox on subprocess git | agents commit themselves; prompt and injected `instructions.md` enforce it |
| `core.hooksPath is not permitted` | same sandbox | pre-commit is inert in worktrees; lint runs in CI |
| JSON env vars mangled by `set -a; . .env.local` | brace expansion and quote stripping | single-quote the JSON, or read a config file without shell parsing |
| Synthetic e2e kills the operator's orchestrator | shared port | force a separate port via `webServer.env` |
| Chat or panel won't scroll | `flex-1` ancestors missing `min-h-0` | add `min-h-0` down the chain |
| Resize handle fails for users, passes in tests | `setPointerCapture` lost off the 1 px target | `document` `pointermove`/`pointerup` listeners during drag |
| Light mode toggles but stays dark | hard-coded color utilities (`bg-zinc-*`) | theme tokens backed by CSS variables |
| "getSnapshot should be cached" loop | selector returns a new object, Set, or Map | shallow-compare multi-key selects; `useMemo` from a stable scalar |
| Parallel sessions reverted a fix | last writer won | no overlapping scopes; else apply the later diff and re-apply the earlier intent |
| Duplicate registrations, endpoint 404s | sibling files register the same key | gate 4; keep one, fix the registrar import |
| CORS fine on REST, SSE blocked | CORS plugins skip raw streams | SSE handler emits ACAO, ACAC, and Vary itself |
| Injected assets committed | `git add .` | filter at apply time |
| Every diff reverts recent main | bare clone has no refspec, frozen at boot SHA | gate 2; the per-worktree force-fetch regressed |
| Blank transcript event | missing `case` arm | diff cases against the union |
| Read-only stage produced a diff | prompt or tool allowlist doesn't enforce it | forbid write tools in that stage's prompt; regression test asserts an empty diff |
| Reply shows in transcript, agent ignores it | never reached process stdin or next turn | tag echo check; bug is in reply delivery, not UI |
| Boot fails after pull: `does not provide an export named '<X>'` | stale shared `dist/` | rebuild shared packages in the start script |
| OOM on a heavy enumeration endpoint | enumerates all rows with sync `du`-like work | `NODE_OPTIONS=--max-old-space-size=8192`; paginate |
| Every session `Not logged in · Please run /login` | per-session HOME hides credentials | symlink operator auth files into each session home |
| Agent stalls on Bash under acceptEdits | acceptEdits still prompts for shell | per-session `settings.json`: `{"permissions":{"allow":["Bash(*)"]}}` |
| `git commit`: "Read-only file system", patch fallbacks | orchestrator inherited a host sandbox | operator relaunches from their terminal; gate 5 detects it |
| `gh pr edit --base` fails on `projectCards` | deprecated GraphQL field | gh ≥ 2.55, or `gh api -X PATCH /repos/:owner/:repo/pulls/:n -f base=<branch>` |
| Pending sessions exhaust admission slots | spawn hangs without timeout | gate 6; orchestrator fix: 30 to 60 s spawn timeout flipping to `failed` with `manual_intervention` |
| Out of quota mid-batch | quota exhausted | stop, schedule a wakeup near reset, don't retry |
| Stacked child PR auto-closes | base deleted on parent merge | `references/restack-after-merge.md`; prefer flat DAGs |
| Retry or cancel POST: "Body cannot be empty..." | strict JSON body parser | client sends `{}` |

## Endpoints

Typical shape; adapt to the service:

```
GET   /api/health                            liveness
GET   /api/version                           features + repos
GET   /api/doctor                            aggregate diagnostics
GET   /api/sessions?status=running&limit=20  filter + pagination
GET   /api/sessions/<slug>[/transcript|/diff|/pr]
GET   /api/audit/events?limit=50             audit trail
GET   /api/config/runtime                    runtime overrides + schema
PATCH /api/config/runtime                    live toggle (ciAutoFix:true)
POST  /api/sessions                          spawn one
POST  /api/sessions/variants                 spawn N + judge
POST  /api/commands                          reply | stop | land | ...
```

## References

- `references/dispatch-prompt-template.md`: session prompt skeleton.
- `references/apply-diffs.md`: copying a worktree diff to main, asset filtering, patch-fallback recovery.
- `references/known-bugs.md`: recurring bug patterns.
- `references/landing-flow.md`: push, PR, and merge via the landing API.
- `references/restack-after-merge.md`: recovering auto-closed stacked children.
- `references/restart-engine.sh`: idempotent kill and relaunch template.
