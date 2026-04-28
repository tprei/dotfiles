---
name: dogfood-loop
description: Drive a running claude-minions engine to fix or extend itself by spawning parallel agent sessions, applying their diffs to main, verifying through Playwright, and (for online repos) pushing/landing PRs via the GitHub App. Use when the user says "dogfood", "use the local engine", or wants to iterate on the orchestrator itself.
model: sonnet
allowed-tools: Read Glob Grep Bash(curl:*) Bash(git:*) Bash(gh:*) Bash(pnpm:*) Bash(pkill:*) Bash(kill:*) Bash(ss:*) Bash(setsid:*) Bash(rm:*) Bash(cp:*) Bash(mkdir:*) Bash(sed:*) Bash(rsync:*) Edit Write mcp__playwright__browser_navigate mcp__playwright__browser_take_screenshot mcp__playwright__browser_evaluate mcp__playwright__browser_click mcp__playwright__browser_snapshot mcp__playwright__browser_resize mcp__playwright__browser_wait_for mcp__playwright__browser_console_messages
user-invocable: true
disable-model-invocation: false
---

# Dogfood loop — claude-minions improving itself

Drive the running orchestrator to fix or extend itself. Spawn parallel agent sessions, apply their diffs to main, verify, optionally push to GitHub via the engine's landing flow, iterate.

## Non-negotiable

This rule applies **only inside the claude-minions repo** (the working directory containing `packages/engine`, `packages/web`, `packages/shared`, and `bin/engine.sh`). It does not apply to dotfiles, the skill itself, or any other repo — those continue to allow direct edits.

EVERY code change to claude-minions goes through a dispatched session. No exceptions:

- Not "small" tweaks (one-line edits, lint fixes, test stubs).
- Not "obvious" CI failures (selector drift, missing exports, port collisions).
- Not "I already know the fix" cases.

If you find yourself about to call Edit/Write directly on `packages/**` inside claude-minions, STOP and dispatch instead.

The exception list is exhaustive — only these paths inside claude-minions may be edited directly on main:

- `.gitignore` additions
- `MEMORY.md` updates
- `docs/dogfood-tasks.md` detour entries

Nothing else.

### Pre-edit gate

Before any Edit/Write into `packages/**` inside claude-minions, ask: **"Did this change come from an applied agent diff?"** If no, stop and dispatch a session. Applied agent diffs come from `cp`/`rsync` out of `.dev-workspace/<slug>/...` per `references/apply-diffs.md` — if the change isn't sourced from a worktree path, it doesn't belong on main.

### Why direct edits poison the loop

- They skip the architectural-lens rejection rules that gate dispatched work.
- They produce diffs the worktree-base mechanism doesn't see, accumulating drift between main and the bases sessions branch from.
- They bypass the regression-test requirement (every dispatched task adds a guard; ad-hoc edits add none).
- The dogfood loop's whole point is the system improving itself. Bypassing it is a lie about what was built.

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

# 2. Bare-clone main must match working-tree main. Stale bare ⇒ every worktree branches from a stale SHA ⇒ every diff reverts recent work.
test "$(git -C .dev-workspace/.repos/self.git rev-parse main)" = "$(git rev-parse main)" \
  || git -C .dev-workspace/.repos/self.git fetch origin main:main --force

# 3. No overlapping scopes across the batch. Two sessions touching the same file ⇒ last-writer-wins regression. Dispatch them sequentially instead.
```

## When to use

- The user says "dogfood", "use it on itself", "run a loop", or wants to iterate on the local orchestrator.
- The engine is running on `127.0.0.1:8787` with `repoId=self` bound to this repo.
- You have ≥ 2 distinct, non-overlapping fixes you can dispatch in parallel.

Skip if the engine isn't running, or if the change crosses too many subsystems for a single session to own end-to-end.

## Quick environment check (run first)

```
test -f .env.local || echo "MISSING .env.local — copy from .env.local.example"
TOKEN=$(grep '^MINIONS_TOKEN=' .env.local | cut -d= -f2)
curl -s -o /dev/null -w "engine HTTP %{http_code}\n" http://127.0.0.1:8787/api/health
curl -s -o /dev/null -w "web HTTP %{http_code}\n"    http://127.0.0.1:5173/
ss -tlnp 2>/dev/null | grep -E "8787|5173|5174"
pgrep -fa "tsx watch.*minions/engine\|@minions/sidecar" | head

# Zombie audit — kill anything from prior sessions that's been alive >4h.
# Stale `pnpm test` runners, orphan dev servers, and synthetic e2e engines
# that didn't clean up will fight your run for ports and memory.
ps -eo pid,etime,cmd | awk '/pnpm.*(test|run dev)/ && !/awk/ { print }' | head
# Format note: etime ≥ "04:00:00" or any "DD-HH:MM:SS" is leaked. `kill -9` it.
```

If engine is down, use `bin/engine.sh` (sources `.env.local`) — see `references/restart-engine.sh`. Boot the web dev with `pnpm --filter @minions/web run dev` if it's not running.

## Loop, in order

1. **Audit**. Use Playwright (or `curl`) to capture broken states — desktop + mobile viewports, dark + light, list/kanban/dag/ship views, chat open + closed. Save screenshots under `.playwright-mcp/`. Don't guess. For chat scroll/resize bugs, query computed styles directly via `browser_evaluate` — chrome headless screenshots can mislead (e.g. body bg may be light per `getComputedStyle` but render dark in the screenshot).

   **For operator-reported bugs, reproduce the failing flow in Playwright before any dispatch.** Take the operator's words ("can't close the chat", "no auto-update") and turn them into a sequence of `browser_click` / `browser_evaluate` calls that demonstrably fails right now. Save that sequence — it's both the dispatch prompt's Do-step and the regression test's setup. If you can't reproduce, ask for clarification before dispatching; you can't fix a flow you haven't seen fail.

2. **Group fixes into focused sessions**. Each session owns one coherent area (e.g. "light mode tokens", "mobile drawer", "chat typography"). 4–6 parallel sessions is healthy. Two sessions touching the same file is a recipe for last-writer-wins regressions — the chat-redesign session in this repo's history reverted a Zustand selector fix from a parallel mobile-shell session for exactly this reason.

3. **Write tight prompts**. See `references/dispatch-prompt-template.md`. Highlights:
   - Name exact files in scope. Forbid touching anything else.
   - Specify the verify step (`pnpm --filter <pkg> run typecheck`) and the explicit commit incantation. The auto-commit completion handler is currently inert under the codex sandbox (`GIT_EDITOR not permitted`) — agents must commit themselves.
   - When a session involves the engine touching infra/code that hot-reloads (`packages/engine/src/**`), warn the agent: "do NOT run pnpm dev; the engine is already running on 8787". Same for the web dev server.
   - For sessions adding **e2e tests / playwright / dev servers**, force a non-default port (e.g. 8801). Otherwise the test engine collides with the operator's running engine and one of them dies.

4. **Dispatch via REST**. `POST http://127.0.0.1:8787/api/sessions` with `{ title, repoId: "self", baseBranch: "main", mode: "task", prompt }`. Capture every slug; print them so the user sees what's running. Use `Authorization: Bearer $TOKEN` from `.env.local`.

5. **Wait for terminal status — in the background, not in your foreground context**. Use Bash `run_in_background: true` with an `until` loop, or spawn an Agent. Foreground polling consumes context proportional to runtime; for any session > 5 min, that compounds across the batch and forces a mid-loop compact. Mark all but the largest sessions for ~30 min cap. Treat `failed turns=0` as "killed mid-bootstrap" and re-dispatch; treat `failed turns>50` as a real attempt that hit a wall (read the last few transcript events to learn why — most often quota or sandbox).

6. **Inspect each diff before applying**. See `references/apply-diffs.md`. Critical: agents capture injected assets (`.cursor/`, `AGENTS.md`, `CLAUDE.md`, `instructions.md`) when they `git add .`. The `.git/info/exclude` approach in the engine doesn't fully prevent this. Filter assets out at apply time.

7. **Apply, verify, commit, push**. The full gate, in order:
   ```
   pnpm install                             # only if package.json changed
   pnpm --filter @minions/shared run build  # types other packages depend on
   pnpm --filter @minions/engine run typecheck
   pnpm --filter @minions/web run typecheck
   pnpm --filter @minions/engine run test
   pnpm --filter @minions/web run build     # web e2e serves dist/, not dev source
   pnpm --filter @minions/web run e2e       # MANDATORY for any web change. Typecheck does not catch selector drift.
   #   Before running e2e, grep for selectors that touch files in this batch:
   #     rg "data-testid|getByRole|getByText|locator\(" packages/web/e2e/*.spec.ts
   #   If any selector references a UI element your batch renamed/removed/restructured, fix the spec first.
   #   Same rule for tests measuring DOM rects: confirm the spec measures the element that's supposed to change,
   #   not a wrapper. (`getBoundingClientRect` on `<main>` rarely tells you what you think it does.)
   pnpm lint
   git add -A && git -c user.email=local@minions -c user.name=local commit -q -m "<subject> (via session <slug>)"
   git push origin main
   gh run watch                             # block until CI terminal. If red: fix BEFORE the next dispatch.
   ```

8. **Recycle the engine** if you touched engine source. tsx watch is unreliable across rapid edits; use `references/restart-engine.sh` (which honors `.env.local`).

9. **Verify the user flow, not the rendered pixels.** Reload the PWA hard (`Cmd/Ctrl+Shift+R` to bust cached vite modules). Then run every check below that matches the change type. A "screenshot looks right" passes happily while the flow is broken — these checks fail loudly when it is.

   **Always (every batch)**:
   - 1440×900 desktop and 390×844 mobile.
   - `browser_console_messages` clean except the manifest-syntax dev warning.
   - For each operator-reported bug in this batch: re-run the exact reproduction sequence from step 1. The flow that failed before must pass now.

   **For any UI surface with controls** (button, link, handle, input, tab):
   - Click every visible control on the changed surface. Each must produce its expected effect: dismiss buttons dismiss, navigation buttons route, toggles toggle, tabs change content. If a button looks like close/cancel/×, click it and assert the panel actually closes.
   - For draggable handles: get `bbox = handle.boundingBox()`, drag from `bbox.x` to `bbox.x ± 200`, then read the bound element's `getBoundingClientRect().width`. Width must change by ≈ 200. Measure the element that's supposed to resize — not `<main>` or some wrapper.
   - For resizable panels: drag the handle to its min and max. Both extremes must produce a visibly different layout (not the same ±60px). If the clamp range is too tight to be useful, that's a bug.

   **For session/transcript views**:
   - Diff the dispatcher against the event-kind union:
     ```
     rg "case \"" packages/web/src/transcript/Transcript.tsx | rg -o '"[a-z_]+"' | sort -u
     rg "kind: \"" packages/shared/src/event.ts | rg -o '"[a-z_]+"' | sort -u
     ```
     Every kind in the union must have a `case` arm. Missing arms render blank — fall-through is silent failure.
   - Open a session that contains at least one of every event kind (seed via `curl /api/commands` if needed). Visually confirm `tool_call`, `tool_result`, `assistant_text`, `user_message`, `status`, `turn_started` each render distinctly.

   **For session-create / `/new` flow**:
   - Open a fresh tab. Submit at `/new`. The chat panel must mount immediately into a spinner state — no blank-flash.
   - Watch for the first SSE event (`turn_started` or `assistant_text`) to render *without reloading the page*. If you have to close+reopen for events to appear, the SSE-store path lost a race with REST backfill.

   **For filter / search / list controls**:
   - Click each filter option in turn. Compare the visible row count to the equivalent `curl '/api/sessions?<filter>'` count. They must match. A filter showing zero rows when curl returns N is a bug, not an empty state.

   **For multi-turn / `waiting_input` features** (think mode, ship stages, reply-mid-turn):
   - In a live session that should accept input, run `await page.locator('textarea').first().isDisabled()` *while the session is mid-turn*. Must be `false`. The mock provider terminates in milliseconds; if the textarea only enables after `turn_completed`, the user can never reply.
   - Type and submit through the textarea, not via `curl /api/commands`. Curl will succeed even when the UI never enabled input, so curl-verification can't surface this class of bug.

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
   - Open a fresh tab on a session that has *zero* prior events. Trigger a turn. Events must appear without any user-driven refresh. If you have to reload to see updates, the streaming path is broken.

   **For mode / stage behavioral contracts** (think, plan, ship stages, dag-task — anything with "this mode must not do X"):
   - **Read-only stages must produce no diff.** For `mode: "think"` and `shipStage: "think"|"plan"`, after the turn ends, the worktree diff must be empty:
     ```
     git -C .dev-workspace/<slug> diff --stat        # MUST be empty
     git -C .dev-workspace/<slug> status --short     # MUST show only injected assets
     ```
     If either shows tracked-file changes, the mode/stage isn't honoring its read-only contract. Bake this into the regression test: dispatch a `mode:think` session that's *asked* to modify a file; assert the diff is empty when the turn completes.
   - **Reply injection must reach the agent.** Don't just assert the reply appears in the transcript — that only proves the event landed. Post a uniquely-tagged reply, then assert the agent acknowledges it in its *next* assistant turn:
     ```
     TAG="reply-probe-$(date +%s)"
     curl -X POST .../api/commands -d "{\"kind\":\"reply\",\"sessionSlug\":\"$SLUG\",\"text\":\"echo back this token: $TAG\"}"
     # poll /api/sessions/$SLUG/transcript until an assistant_text event after the reply contains $TAG
     ```
     If the tag never echoes back, the reply landed in the transcript but the agent didn't see it. That's the injection path silently dropping messages — a transcript-render check would have passed.
   - **For every mode/stage with a constraint, write the constraint as an assertion in the regression test.** "Stage X must not Y" is a behavioral contract. The dispatch-prompt-template's regression-test step must encode the constraint, not just the happy path.

10. **For online closed loop** (push → PR → merge), see `references/landing-flow.md`. The short of it:
    - Agent commits in worktree (manually if auto-commit handler is inert).
    - `POST /api/commands {kind:"land", sessionSlug, strategy:"squash", force:true}` — engine pushes via GH App askpass, opens PR via gh CLI, then `gh pr merge`. `force: true` skips readiness when CI hasn't completed yet.
    - Verify on github: `gh pr view <n> --json state,mergeCommit`.

11. **Save lessons as memory**. When a session pattern fails (agents refusing to commit, sandbox-readonly, parallel-session conflicts, JSON env getting eaten by shell sourcing) write a feedback memory under the project memory dir.

## Hazards (and the fix you reach for)

| symptom | cause | fix |
|---|---|---|
| `EADDRINUSE 8787` on engine restart | tsx watch leaked an orphan listener | `pkill -9 -f "tsx watch.*minions/engine\|@minions/engine.*pnpm"`, then `ss -tlnp | grep 8787` empty before relaunch |
| Sessions failing `turns=0` after engine recycle | killed mid-spawn; resume marker stale (`No deferred tool marker found`) | re-dispatch the session |
| Auto-commit handler audit shows `GIT_EDITOR not permitted` | codex sandbox on subprocess git invocations | rely on agents committing themselves; instructions.md asset already enforces this |
| `core.hooksPath is not permitted without enabling allowUnsafeHooksPath` | same codex sandbox | pre-commit hook is currently inert in worktrees; lint runs in CI |
| `MINIONS_REPOS` JSON gets eaten by `set -a; . .env.local` | brace expansion + double-quote stripping | single-quote the whole JSON value: `MINIONS_REPOS='[{"id":...}]'` |
| Synthetic e2e job collides with operator's engine | shared port :8787 | always use a different port for test engine; `playwright.config.ts` `webServer` env `MINIONS_PORT=8801` etc. |
| Chat doesn't scroll | flexbox missing `min-h-0` chain | look for `flex-1` ancestors without `min-h-0` and add it |
| Chat resize doesn't drag for real users but works in synthetic test | `setPointerCapture` doesn't propagate when cursor leaves the 1px hit target | switch to `document.addEventListener('pointermove'|'pointerup')` for the duration of a drag |
| Light mode toggles class but page still looks dark | tailwind tokens hard-coded; `darkMode: "class"` doesn't help | replace `bg-zinc-*`/`text-zinc-*` with theme tokens that consume CSS variables (`bg-bg`, `text-fg`, etc.) |
| Zustand "result of getSnapshot should be cached" infinite loop | selector returns a new object/Set/Map every render | `useShallow` for multi-key selects, `useMemo` to derive collections from a stable scalar slice |
| Two parallel sessions touched the same file → reverted fix | the agent that finished last won | don't dispatch overlapping scopes; if you must, take diffs from the LATER session and re-apply earlier-session intent on top |
| Duplicate `app.get("/api/...")` registrations after parallel work | two agents wrote sibling `routes.ts` files | `grep -rn 'app\.(get|post|patch|delete)' packages/engine/src/ | grep -v test` and dedupe; only one path is wired in `http/routes/index.ts` |
| CORS works on REST but `/api/events` SSE blocked | Fastify CORS plugin doesn't cover `reply.raw` streams | `packages/engine/src/http/sse.ts` emits ACAO/ACAC/Vary manually — preserve across edits |
| Agents commit `.cursor/`, `AGENTS.md`, `CLAUDE.md`, `instructions.md` | injected assets, agent's `git add .` captures them, exclude file is best-effort | filter at apply time (see `references/apply-diffs.md`) |
| Every dispatched diff comes back stale (regressions revert recent main commits) | bare clone has no fetch refspec; `git fetch --all` is a no-op for `refs/heads/main`, so the bare's main is frozen at engine-boot SHA | run the stale-bare gate (Pre-dispatch gates §2) before every batch. If it fires, the engine's per-worktree force-fetch regressed — re-investigate `packages/engine/src/workspace/worktree.ts` |
| Transcript event renders blank | `Transcript.tsx` dispatcher missing a `case` arm for that kind | diff the dispatcher's cases against the `EventKind` union (§9, "session/transcript views" check) |
| Read-only stage (think/plan) produced a code diff | stage's prompt or tool allowlist isn't enforcing read-only | run §9 "mode/stage behavioral contracts" check; the dispatched-prompt for that stage must explicitly forbid Edit/Write/Bash-write tools, and the regression test must dispatch a stage-think session that's *asked* to modify code and assert the diff is empty |
| Injected reply appears in transcript but agent never acknowledges it | reply event landed in store but never reached the spawned process's stdin / next turn input | run §9 "reply injection" check (unique-tag echo). If the tag never echoes, the bug is in the engine's reply-delivery path, not the UI |

## Useful endpoints to keep in your back pocket

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
| `references/apply-diffs.md` | How to copy a worktree's diff to main, filtering injected assets. |
| `references/known-bugs.md` | Bug patterns this codebase has hit before — quick recognition. |
| `references/landing-flow.md` | Push → PR → merge via the GitHub App + `gh pr merge`. |
| `references/restart-engine.sh` | Idempotent kill + relaunch script (uses `bin/engine.sh` + `.env.local`). |
