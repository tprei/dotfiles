---
name: dogfood-loop
description: Drive a running agentic orchestrator (a service that spawns parallel coding-agent sessions on a target repo) to fix or extend that repo by dispatching sessions, applying their diffs to the main branch, verifying through tests and UI checks, and (for online repos) pushing/landing PRs. Use when the user says "dogfood", "use the local orchestrator", or wants to iterate on a repo via dispatched sessions rather than direct edits.
model: sonnet
allowed-tools: Read Glob Grep Bash(curl:*) Bash(git:*) Bash(gh:*) Bash(pnpm:*) Bash(npm:*) Bash(yarn:*) Bash(pkill:*) Bash(kill:*) Bash(ss:*) Bash(setsid:*) Bash(rm:*) Bash(cp:*) Bash(mkdir:*) Bash(sed:*) Bash(rsync:*) Edit Write mcp__playwright__browser_navigate mcp__playwright__browser_take_screenshot mcp__playwright__browser_evaluate mcp__playwright__browser_click mcp__playwright__browser_snapshot mcp__playwright__browser_resize mcp__playwright__browser_wait_for mcp__playwright__browser_console_messages
user-invocable: true
disable-model-invocation: false
---

# Dogfood loop — agentic orchestrator improving a repo

Drive a running agentic orchestrator to fix or extend a target repo. Spawn parallel agent sessions, apply their diffs to the main branch, verify, optionally land PRs, iterate.

This skill assumes:
- An orchestrator service is running locally with an HTTP dispatch API (something like `POST /api/sessions { repoId, baseBranch, mode, prompt }` returning a session slug).
- Each session runs in its own git worktree under a known workspace path (e.g. `<workspace>/<slug>/`).
- The orchestrator can be configured against a `repoId` that points at the user's working repo.

Concrete commands below use placeholders like `$ORCH_URL`, `$TOKEN`, `$REPO_ID`, `$WORKSPACE`, `$BUILD`, `$TYPECHECK`, `$TEST`, `$E2E`, `$LINT`. Substitute from the orchestrator's configuration before running.

## Non-negotiable

When dogfooding *the orchestrator on itself* (the working repo IS the orchestrator's source), EVERY code change to that repo goes through a dispatched session. No exceptions:

- Not "small" tweaks (one-line edits, lint fixes, test stubs).
- Not "obvious" CI failures (selector drift, missing exports, port collisions).
- Not "I already know the fix" cases.

If you find yourself about to call Edit/Write directly on source files inside the dogfooded repo, STOP and dispatch instead.

The exception list is exhaustive — only these paths may be edited directly on the main branch:

- `.gitignore` additions
- Local memory / notes files (`MEMORY.md`, scratch task logs)
- Operational doc detour entries

Nothing else.

When dogfooding *another* repo (the orchestrator and the target repo are different codebases), you may still edit the orchestrator directly — the non-negotiable applies only to the target repo being dispatched against.

### Pre-edit gate

Before any Edit/Write into source dirs of the dogfooded repo, ask: **"Did this change come from an applied agent diff?"** If no, stop and dispatch a session. Applied agent diffs come from `cp`/`rsync` out of `<workspace>/<slug>/...` per `references/apply-diffs.md` — if the change isn't sourced from a worktree path, it doesn't belong on main.

### Why direct edits poison the loop

- They skip the architectural-lens rejection rules that gate dispatched work.
- They produce diffs the worktree-base mechanism doesn't see, accumulating drift between main and the bases sessions branch from.
- They bypass the regression-test requirement (every dispatched task adds a guard; ad-hoc edits add none).
- The dogfood loop's whole point is the system improving itself. Bypassing it is a lie about what was built.

### Orchestrator-broken bootstrap exception

There's exactly one situation where direct edits to orchestrator source are permitted: **the orchestrator cannot dispatch a session that reaches `running` status.**

Symptoms that qualify:
- `POST /api/sessions` returns OK but the session sits in `pending` for >60s and gets killed by a stuck-pending sweeper.
- The orchestrator refuses to boot (`SyntaxError`, `EADDRINUSE` you can't kill, immediate OOM).
- Spawn auth is fully broken (every session fails with `Not logged in` or equivalent).
- Sandbox prevents *every* agent from completing (every diff comes back as a patch fallback with the same gitdir-readonly error).

In any of those, fix the orchestrator directly on main. The exception ends as soon as a probe-dispatch succeeds:

```
# Probe: dispatch a tiny task and confirm it reaches `running` and produces tool calls within 60s.
curl -sX POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"probe","repoId":"'"$REPO_ID"'","baseBranch":"main","mode":"task",
       "prompt":"Run the project typecheck and report the exit code. Do not edit any files."}' \
  "$ORCH_URL/api/sessions"
# Then poll /api/sessions/<slug> until status=completed AND turns>0.
```

If the probe succeeds, broken-mode is over and you must dispatch every subsequent change. If it fails the same way the original sessions did, the direct fix wasn't enough — keep iterating directly until the probe passes.

This is a real exception, not a loophole. It applies only to the orchestrator failing to spawn, not to "this specific feature is hard to dispatch" or "this fix is small". The test is mechanical: did the probe succeed?

### Bypass rationalizations to reject

These all rationalize bypassing the dispatch. None justify it. If you catch yourself thinking any of them, dispatch instead:

- "It's small enough to do directly" — the regression budget for a one-line edit equals the budget for a hundred-line one.
- "The fix is obvious" — obvious fixes hide architectural mismatches the loop is built to catch.
- "I already know what changed" — the value of the loop isn't the fix, it's the regression-test guard the dispatch produces.
- "The session would just produce a stale-base diff" — fix the worktree base first (see "Stale-bare sanity check" below), then dispatch.
- "The session is taking too long" — wait, or stop and re-dispatch with tighter scope.
- "I'll fix it in a follow-up" — direct edits compound; the loop never catches up. Track it as a queued task instead.

### Pre-dispatch gates (run all before each batch)

```
# 1. CI on main must be green. Red main makes every dispatched diff inherit the red.
gh run list --branch main --limit 1
# Expect: status "completed" + conclusion "success". Anything else: fix first.

# 2. Bare-clone main (if the orchestrator branches sessions from a local bare) must match
#    working-tree main. Stale bare ⇒ every worktree branches from a stale SHA ⇒ every diff
#    reverts recent work.
BARE="$WORKSPACE/.repos/$REPO_ID.git"   # adjust path to your orchestrator's layout
test "$(git -C "$BARE" rev-parse main)" = "$(git rev-parse main)" \
  || git -C "$BARE" fetch origin main:main --force

# 3. No overlapping scopes across the batch. Two sessions touching the same file ⇒
#    last-writer-wins regression. Dispatch them sequentially instead.

# 4. No silently-shadowed routes / module registrations. If your framework de-dupes by key
#    (Fastify routes, Express handlers, plugin slots), two registrations under the same key
#    silently drop one. Grep for duplicates before adding new endpoints. Example:
#      rg -n "app\.(get|post|patch|delete)\(['\"]/api" src/ | awk -F'"' '{print $2}' \
#        | sort | uniq -d
#    Adapt the grep to your framework. Empty output is the only acceptable result.

# 5. No orchestrator running with an inherited sandbox. If the orchestrator was launched
#    from inside a Claude Code (or other agentic) session, every spawned sub-agent inherits
#    that session's sandbox and can't write to its worktree's gitdir.
ORCH_PID=$(pgrep -f "<your-orchestrator-cmd-pattern>" | head -1)
[ -n "$ORCH_PID" ] && ps -p $(awk '/^PPid:/ {print $2}' /proc/$ORCH_PID/status) -o cmd= \
  | grep -qE 'claude|claude-code|codex' \
  && echo "ORCHESTRATOR INHERITED AGENTIC SANDBOX — sessions can't write to gitdir; ask operator to relaunch from their terminal" \
  && exit 1

# 6. No stuck-pending sessions occupying admission slots.
curl -sH "Authorization: Bearer $TOKEN" "$ORCH_URL/api/sessions" \
  | python3 -c '
import json,sys,datetime
items = json.load(sys.stdin)["items"]
stuck = [s for s in items
         if s["status"] == "pending"
         and (datetime.datetime.now(datetime.timezone.utc)
              - datetime.datetime.fromisoformat(s["createdAt"].replace("Z","+00:00"))).total_seconds() > 120]
for s in stuck: print("STUCK:", s["slug"])
'
# Stop each via POST /api/commands {kind:"stop", sessionSlug:...} (or your orchestrator's
# equivalent) before dispatching new work.
```

## When to use

- The user says "dogfood", "use it on itself", "run a loop", or wants to iterate on a repo via dispatched sessions.
- The orchestrator is running with `$REPO_ID` bound to the target repo.
- You have ≥ 2 distinct, non-overlapping fixes you can dispatch in parallel.

Skip if the orchestrator isn't running, or if the change crosses too many subsystems for a single session to own end-to-end.

## Quick environment check (run first)

```
# Orchestrator + web (if applicable) liveness
curl -s -o /dev/null -w "orchestrator HTTP %{http_code}\n" "$ORCH_URL/api/health"
curl -s -o /dev/null -w "web HTTP %{http_code}\n"          "${WEB_URL:-http://127.0.0.1:5173}/"
ss -tlnp 2>/dev/null | grep -E "<orchestrator-port>|<web-ports>"

# Zombie audit — kill anything from prior sessions that's been alive >4h.
# Stale test runners, orphan dev servers, and synthetic e2e instances that didn't clean up
# will fight your run for ports and memory.
ps -eo pid,etime,cmd | awk '/(test|run dev|tsx watch|vite)/ && !/awk/ { print }' | head
# Format note: etime ≥ "04:00:00" or any "DD-HH:MM:SS" is leaked. `kill -9` it.
```

If the orchestrator is down, restart via the project's own start script (see `references/restart-engine.sh` for a template). Boot the dev server too if relevant.

**Always rebuild any shared/types package the orchestrator consumes at runtime before relaunching after a `git pull`.** Stale `dist/` of a shared package is a frequent boot-fail symptom — surface error is `SyntaxError: The requested module '<pkg>' does not provide an export named '<X>'`. Fix is the rebuild, never reverting the change in main. Bake the rebuild into the start script so the trap doesn't recur.

**The operator launches the orchestrator, not the dogfood loop.** When you (the loop) start the orchestrator via Bash, every spawned sub-agent inherits the surrounding agentic sandbox and can't write to its worktree's gitdir. Run the sandbox-inheritance gate above; if it fires, ask the operator to relaunch in their own terminal.

## Loop, in order

1. **Audit.** Use Playwright (or `curl`) to capture broken states — desktop + mobile viewports, dark + light, every relevant view. Save screenshots under `.playwright-mcp/`. Don't guess. For layout/scroll bugs, query computed styles directly via `browser_evaluate` — chrome headless screenshots can mislead (e.g. body bg may be light per `getComputedStyle` but render dark in the screenshot).

   **For operator-reported bugs, reproduce the failing flow in Playwright before any dispatch.** Take the operator's words ("can't close the chat", "no auto-update") and turn them into a sequence of `browser_click` / `browser_evaluate` calls that demonstrably fails right now. Save that sequence — it's both the dispatch prompt's Do-step and the regression test's setup. If you can't reproduce, ask for clarification before dispatching; you can't fix a flow you haven't seen fail.

   **Operator pastes are primary signal.** When the operator pastes orchestrator logs, screenshots, or transcript fragments mid-loop, treat them as ground truth — not the orchestrator API responses, which can lag or contradict the paste. File the implied bug immediately, before continuing the queued work. Expect the loop to surface orchestrator bugs at roughly a 1:2 ratio with feature ships; budget time accordingly.

2. **Group fixes into focused sessions.** Each session owns one coherent area (e.g. "light mode tokens", "mobile drawer", "chat typography"). 4–6 parallel sessions is healthy. Two sessions touching the same file is a recipe for last-writer-wins regressions — a session reverting another's fix is the most expensive failure mode in this loop.

3. **Write tight prompts.** See `references/dispatch-prompt-template.md`. Highlights:
   - Name exact files in scope. Forbid touching anything else.
   - Specify the verify step (the project's typecheck/test commands) and the explicit commit incantation. Many sandboxes prevent the orchestrator's auto-commit handler from running, so agents must commit themselves.
   - When a session touches infra/code that hot-reloads, warn the agent: "do NOT run dev servers; the operator already has those running. Just typecheck and test."
   - For sessions adding **e2e tests / dev servers**, force a non-default port. Otherwise the test instance collides with the operator's running orchestrator and one of them dies.

4. **Dispatch via REST.** `POST $ORCH_URL/api/sessions` with `{ title, repoId: "$REPO_ID", baseBranch: "main", mode: "task", prompt }`. Capture every slug; print them so the user sees what's running. Use `Authorization: Bearer $TOKEN` from your local config.

5. **Wait for terminal status — in the background, not in your foreground context.** Use Bash `run_in_background: true` with an `until` loop, or spawn an Agent. Foreground polling consumes context proportional to runtime; for any session > 5 min, that compounds across the batch and forces a mid-loop compact. Mark all but the largest sessions for ~30 min cap. Treat `failed turns=0` as "killed mid-bootstrap" and re-dispatch; treat `failed turns>50` as a real attempt that hit a wall (read the last few transcript events to learn why — most often quota or sandbox).

   **Monitor hygiene** (mistakes that make Monitors lie):
   - Cancel old monitors when their target session is stopped — otherwise they fire on dead state and report false bugs.
   - Use Python with `json.load` for any transcript / session inspection inside `until`-loops. `jq` chokes on control characters embedded in transcript event text and exits non-zero; the until-loop dies; the monitor reports failure on a healthy session.
   - For reply-injection checks, search the *entire transcript after the reply timestamp* for the unique tag — do not assume the reply lands at any particular turn number. Replies can drain at turn N or turn N+1 depending on whether the agent is mid-turn at injection time.
   - Treat "out of usage / quota exhausted · resets HH:MM" in any tool output as a hard stop. Don't retry — schedule a wakeup near the reset and re-enter the loop then. Retrying burns budget on dead-on-arrival sessions.

6. **Inspect each diff before applying.** See `references/apply-diffs.md`. Critical: agents capture injected assets (project context files like `AGENTS.md`, `CLAUDE.md`, `.cursor/`, `instructions.md` that the orchestrator drops into worktrees) when they `git add .`. Excluding them via `.git/info/exclude` is best-effort and not always reliable. Filter assets out at apply time.

7. **Apply, verify, commit, push.** The full gate, in order:
   ```
   $INSTALL                                  # only if dependency manifest changed
   $BUILD_SHARED_PACKAGES                    # types other packages depend on, if any
   $TYPECHECK                                # all relevant packages
   $TEST                                     # unit/integration; the regression test must pass
   $WEB_BUILD                                # if your e2e serves built output
   $E2E                                      # MANDATORY for any UI change. Typecheck does not catch selector drift.
   #   Before running e2e, grep for selectors that touch files in this batch:
   #     rg "data-testid|getByRole|getByText|locator\(" e2e/*.spec.ts
   #   If any selector references a UI element your batch renamed/removed/restructured, fix the spec first.
   #   Same rule for tests measuring DOM rects: confirm the spec measures the element that's
   #   supposed to change, not a wrapper. (`getBoundingClientRect` on `<main>` rarely tells you
   #   what you think it does.)
   $LINT
   git add -A && git -c user.email=local@dogfood -c user.name=local commit -q -m "<subject> (via session <slug>)"
   git push origin main
   gh run watch                              # block until CI terminal. If red: fix BEFORE the next dispatch.
   ```

8. **Recycle the orchestrator** if you touched orchestrator source. Watch-mode dev servers are unreliable across rapid edits; use the restart template in `references/restart-engine.sh`.

9. **Verify the user flow, not the rendered pixels.** Reload the app hard (`Cmd/Ctrl+Shift+R` to bust cached modules). Then run every check below that matches the change type. A "screenshot looks right" passes happily while the flow is broken — these checks fail loudly when it is.

   **Always (every batch)**:
   - 1440×900 desktop and 390×844 mobile.
   - `browser_console_messages` clean except known dev-only warnings.
   - For each operator-reported bug in this batch: re-run the exact reproduction sequence from step 1. The flow that failed before must pass now.

   **For any UI surface with controls** (button, link, handle, input, tab):
   - Click every visible control on the changed surface. Each must produce its expected effect: dismiss buttons dismiss, navigation buttons route, toggles toggle, tabs change content. If a button looks like close/cancel/×, click it and assert the panel actually closes.
   - For draggable handles: get `bbox = handle.boundingBox()`, drag from `bbox.x` to `bbox.x ± 200`, then read the bound element's `getBoundingClientRect().width`. Width must change by ≈ 200. Measure the element that's supposed to resize — not a wrapper.
   - For resizable panels: drag the handle to its min and max. Both extremes must produce a visibly different layout (not the same ±60px). If the clamp range is too tight to be useful, that's a bug.

   **For session/transcript views** (anything that renders a discriminated union of event kinds):
   - Diff the dispatcher against the event-kind union. Every kind in the union must have a `case` arm. Missing arms render blank — fall-through is silent failure.
   - Open a session that contains at least one of every event kind (seed via API if needed). Visually confirm each event kind renders distinctly.

   **For session-create / "new session" flow**:
   - Open a fresh tab. Submit a new session. The detail panel must mount immediately into a spinner state — no blank-flash.
   - Watch for the first streaming event to render *without reloading the page*. If you have to close+reopen for events to appear, the streaming-store path lost a race with REST backfill.

   **For filter / search / list controls**:
   - Click each filter option in turn. Compare the visible row count to the equivalent `curl '/api/...?<filter>'` count. They must match. A filter showing zero rows when curl returns N is a bug, not an empty state.

   **For multi-turn / `waiting_input` features** (interactive replies, multi-stage flows):
   - In a live session that should accept input, run `await page.locator('textarea').first().isDisabled()` *while the session is mid-turn*. Must be `false`. Mock providers terminate fast; if the textarea only enables after `turn_completed`, the user can never reply.
   - Type and submit through the UI control, not via a direct API call. Direct API calls succeed even when the UI never enabled input, so they can't surface this class of bug.

   **For any flex/grid layout change**:
   - On the changed surface, run:
     ```js
     [...document.querySelectorAll('*')]
       .filter(c => /auto|scroll/.test(getComputedStyle(c).overflow))
       .map(c => `${c.tagName}.${c.className}: ${getComputedStyle(c).overflow}`)
     ```
     Anything new in the list is a candidate scrollbar — confirm it's intended. Tab strips, header rows, and pill clusters should not scroll.
   - Resize the viewport to 320×568, 768×1024, 1440×900 and re-run. Scrollbars only on intended scroll containers.

   **For SSE / realtime work**:
   - Open a fresh tab on a resource that has *zero* prior events. Trigger an update. Events must appear without any user-driven refresh. If you have to reload to see updates, the streaming path is broken.

   **For mode / stage behavioral contracts** (anything with "this mode must not do X"):
   - **Read-only modes must produce no diff.** After the turn ends, the worktree diff must be empty:
     ```
     git -C "$WORKSPACE/<slug>" diff --stat        # MUST be empty
     git -C "$WORKSPACE/<slug>" status --short     # MUST show only injected assets
     ```
     If either shows tracked-file changes, the mode isn't honoring its read-only contract. Bake this into the regression test: dispatch a read-only-mode session that's *asked* to modify a file; assert the diff is empty when the turn completes.
   - **Reply injection must reach the agent.** Don't just assert the reply appears in the transcript — that only proves the event landed. Post a uniquely-tagged reply, then assert the agent acknowledges it in its *next* assistant turn:
     ```
     TAG="reply-probe-$(date +%s)"
     curl -X POST "$ORCH_URL/api/commands" -d "{\"kind\":\"reply\",\"sessionSlug\":\"$SLUG\",\"text\":\"echo back this token: $TAG\"}"
     # poll /api/sessions/$SLUG/transcript until an assistant_text event after the reply contains $TAG
     ```
     If the tag never echoes back, the reply landed in the transcript but the agent didn't see it. That's the injection path silently dropping messages — a transcript-render check would have passed.
   - **For every mode/stage with a constraint, write the constraint as an assertion in the regression test.** "Mode X must not Y" is a behavioral contract. The dispatch-prompt-template's regression-test step must encode the constraint, not just the happy path.

10. **For online closed loop** (push → PR → merge), see `references/landing-flow.md`. The short of it:
    - Agent commits in the worktree (manually if auto-commit handler is inert).
    - `POST /api/commands {kind:"land", sessionSlug, strategy:"squash", force:true}` — orchestrator pushes via its preferred auth (GitHub App askpass, `gh` stored creds, etc.), opens PR via gh CLI, then `gh pr merge`. `force: true` skips readiness when CI hasn't completed yet.
    - Verify on github: `gh pr view <n> --json state,mergeCommit`.
    - **Stacked PRs auto-close on parent merge** when `--delete-branch` deletes the base. Every multi-node DAG produces this dance unless you flatten the stack to all-target-`main`. See `references/restack-after-merge.md` for the recovery pattern. Prefer flat DAGs in dispatch prompts whenever node N's content doesn't *semantically* depend on node N-1's content; type-only deps belong in a shared package and don't need stacking.

11. **Save lessons as memory.** When a session pattern fails (agents refusing to commit, sandbox-readonly, parallel-session conflicts, env files getting eaten by shell sourcing) write a feedback memory under the project memory dir.

## Hazards (and the fix you reach for)

| symptom | cause | fix |
|---|---|---|
| `EADDRINUSE` on orchestrator restart | watch-mode leaked an orphan listener | `pkill -9 -f "<orchestrator-cmd-pattern>"`, then `ss -tlnp | grep <port>` empty before relaunch |
| Sessions failing `turns=0` after orchestrator recycle | killed mid-spawn; resume marker stale | re-dispatch the session |
| Auto-commit handler audit shows `GIT_EDITOR not permitted` | host agentic-CLI sandbox on subprocess git invocations | rely on agents committing themselves; the dispatch prompt and any injected `instructions.md` asset must enforce this |
| `core.hooksPath is not permitted` errors | same host-sandbox issue | pre-commit hook is currently inert in worktrees; lint runs in CI |
| JSON env vars get eaten by `set -a; . .env.local` | brace expansion + double-quote stripping in shell sourcing | single-quote the whole JSON value, or migrate to a config file the orchestrator reads directly (no shell parsing) |
| Synthetic e2e job collides with operator's orchestrator | shared port | always force a different port for the test orchestrator via `webServer.env` (or equivalent) |
| Chat / panel doesn't scroll | flexbox missing `min-h-0` chain | look for `flex-1` ancestors without `min-h-0` and add it |
| Resize handle doesn't drag for real users but works in synthetic test | `setPointerCapture` doesn't propagate when cursor leaves the 1px hit target | switch to `document.addEventListener('pointermove'\|'pointerup')` for the duration of a drag |
| Light mode toggles class but page still looks dark | tailwind tokens hard-coded; `darkMode: "class"` doesn't help | replace hard-coded color utilities (`bg-zinc-*` etc.) with theme tokens that consume CSS variables |
| State-store "result of getSnapshot should be cached" infinite loop | selector returns a new object/Set/Map every render | use shallow-compare wrapper for multi-key selects, `useMemo` to derive collections from a stable scalar slice |
| Two parallel sessions touched the same file → reverted fix | the agent that finished last won | don't dispatch overlapping scopes; if you must, take diffs from the LATER session and re-apply earlier-session intent on top |
| Duplicate route registrations after parallel work | two agents wrote sibling files registering the same key | grep for duplicate registration keys before each dispatch (pre-dispatch gate §4); dedupe; only one path is wired in the registrar |
| CORS works on REST but SSE blocked | many CORS plugins don't cover raw streamed responses | the SSE handler must emit ACAO/ACAC/Vary headers manually — preserve across edits |
| Agents commit injected assets (`AGENTS.md`, `CLAUDE.md`, `.cursor/`, `instructions.md`) | injected context files; agent's `git add .` captures them; exclude file is best-effort | filter at apply time (see `references/apply-diffs.md`) |
| Every dispatched diff comes back stale (regressions revert recent main commits) | bare clone has no fetch refspec; the bare's main is frozen at orchestrator-boot SHA | run the stale-bare gate (Pre-dispatch gates §2) before every batch. If it fires, the orchestrator's per-worktree force-fetch regressed |
| Transcript event renders blank | dispatcher missing a `case` arm for that kind | diff the dispatcher's cases against the event-kind union (§9, "session/transcript views" check) |
| Read-only stage produced a code diff | stage's prompt or tool allowlist isn't enforcing read-only | run §9 "mode/stage behavioral contracts" check; the dispatched-prompt for that stage must explicitly forbid Edit/Write/Bash-write tools, and the regression test must dispatch a read-only-mode session that's *asked* to modify code and assert the diff is empty |
| Injected reply appears in transcript but agent never acknowledges it | reply event landed in store but never reached the spawned process's stdin / next turn input | run §9 "reply injection" check (unique-tag echo). If the tag never echoes, the bug is in the orchestrator's reply-delivery path, not the UI |
| Orchestrator fails to boot after `git pull` with `does not provide an export named '<X>'` | stale `dist/` of a shared package | rebuild shared packages before relaunch (bake into start script) |
| Orchestrator OOMs at default heap during heavy enumeration endpoint | endpoint enumerated all rows + ran sync `du`-like work synchronously | pin `NODE_OPTIONS=--max-old-space-size=8192` (or equivalent); paginate the endpoint |
| Every session fails with `Not logged in · Please run /login` | per-session HOME isolation hides operator's credentials | symlink the operator's auth files into each session's per-session home dir |
| Agent stalls on Bash prompts under acceptEdits permissionMode | acceptEdits auto-confirms file writes but still prompts for shell | per-session settings.json must include `{"permissions":{"allow":["Bash(*)"]}}` |
| Every session's `git commit` returns "Read-only file system"; agents leave patch fallbacks | orchestrator inherited host agentic-CLI sandbox from its launching shell | operator must launch the orchestrator from their own terminal, outside any agentic CLI session; pre-dispatch gate detects parent-process |
| `gh pr edit --base` errors with `projectCards` GraphQL deprecation | gh CLI mutation requests a deprecated field | upgrade gh ≥ 2.55, or use `gh api -X PATCH /repos/:owner/:repo/pulls/:n -f base=<branch>` |
| Endpoint 404s despite source being present | two sibling files register the same route key; second registration silently dropped | run pre-dispatch gate §4; pick canonical, delete duplicate, fix import in the registrar |
| Sessions stuck `pending` exhaust admission slots | spawn hangs without timeout, slot never freed | run pre-dispatch gate §6 (sweep stuck-pending > 120s, stop each); orchestrator-side fix is a 30-60s spawn timeout that flips to `failed` with `manual_intervention` |
| Out-of-quota signal mid-batch | API quota exhausted | stop dispatching, schedule wakeup near the announced reset time, do not retry |
| Stacked child PR auto-closes when parent merges with `--delete-branch` | GitHub closes children whose base was deleted; restacker raced or hit projectCards error | follow `references/restack-after-merge.md` recovery; prefer flat DAGs (all nodes target `main`) for future dispatches |
| Retry / cancel button POST returns "Body cannot be empty when content-type is set to 'application/json'" | strict body parsers reject empty bodies with JSON content-type | web client must send `{}` for body-less posts |

## Useful endpoints to keep in your back pocket

A typical orchestrator exposes a shape like the following — adapt to your service's actual surface:

```
GET  /api/health                                  liveness
GET  /api/version                                 features list + repos
GET  /api/doctor                                  aggregate diagnostics in one round-trip
GET  /api/sessions?status=running&limit=20        filter+pagination
GET  /api/sessions/<slug>                         single session
GET  /api/sessions/<slug>/transcript              all events
GET  /api/sessions/<slug>/diff                    workspace diff
GET  /api/sessions/<slug>/pr                      PR preview
GET  /api/audit/events?limit=50                   audit trail (e.g. completion handlers)
GET  /api/config/runtime                          runtime overrides + schema
PATCH /api/config/runtime                         live-toggle (e.g. ciAutoFix:true)
POST /api/sessions                                spawn one
POST /api/sessions/variants                       spawn N + judge
POST /api/commands                                discriminated union (reply/stop/land/...)
```

## Reference files

| File | Contents |
|------|----------|
| `references/dispatch-prompt-template.md` | Prompt skeleton ready to paste into a `POST /api/sessions` body. |
| `references/apply-diffs.md` | How to copy a worktree's diff to main, filtering injected assets, plus patch-fallback recovery. |
| `references/known-bugs.md` | Categories of bug pattern that recur in dogfood loops — quick recognition. |
| `references/landing-flow.md` | Push → PR → merge via the orchestrator's landing API + `gh pr merge`. |
| `references/restack-after-merge.md` | Recovery dance for child PRs that auto-close when their stacked parent merges. |
| `references/restart-engine.sh` | Idempotent kill + relaunch script template. |
