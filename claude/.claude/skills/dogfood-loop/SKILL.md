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
```

If engine is down, use `bin/engine.sh` (sources `.env.local`) — see `references/restart-engine.sh`. Boot the web dev with `pnpm --filter @minions/web run dev` if it's not running.

## Loop, in order

1. **Audit**. Use Playwright (or `curl`) to capture broken states — desktop + mobile viewports, dark + light, list/kanban/dag/ship views, chat open + closed. Save screenshots under `.playwright-mcp/`. Don't guess. For chat scroll/resize bugs, query computed styles directly via `browser_evaluate` — chrome headless screenshots can mislead (e.g. body bg may be light per `getComputedStyle` but render dark in the screenshot).

2. **Group fixes into focused sessions**. Each session owns one coherent area (e.g. "light mode tokens", "mobile drawer", "chat typography"). 4–6 parallel sessions is healthy. Two sessions touching the same file is a recipe for last-writer-wins regressions — the chat-redesign session in this repo's history reverted a Zustand selector fix from a parallel mobile-shell session for exactly this reason.

3. **Write tight prompts**. See `references/dispatch-prompt-template.md`. Highlights:
   - Name exact files in scope. Forbid touching anything else.
   - Specify the verify step (`pnpm --filter <pkg> run typecheck`) and the explicit commit incantation. The auto-commit completion handler is currently inert under the codex sandbox (`GIT_EDITOR not permitted`) — agents must commit themselves.
   - When a session involves the engine touching infra/code that hot-reloads (`packages/engine/src/**`), warn the agent: "do NOT run pnpm dev; the engine is already running on 8787". Same for the web dev server.
   - For sessions adding **e2e tests / playwright / dev servers**, force a non-default port (e.g. 8801). Otherwise the test engine collides with the operator's running engine and one of them dies.

4. **Dispatch via REST**. `POST http://127.0.0.1:8787/api/sessions` with `{ title, repoId: "self", baseBranch: "main", mode: "task", prompt }`. Capture every slug; print them so the user sees what's running. Use `Authorization: Bearer $TOKEN` from `.env.local`.

5. **Wait for terminal status**. Poll `GET /api/sessions/<slug>` until `status` ∉ `{running, pending, waiting_input}`. A Bash `until` loop with `sleep 30` is fine. Mark all but the largest sessions for ~30 min cap. Treat `failed turns=0` as "killed mid-bootstrap" and re-dispatch; treat `failed turns>50` as a real attempt that hit a wall (read the last few transcript events to learn why — most often quota or sandbox).

6. **Inspect each diff before applying**. See `references/apply-diffs.md`. Critical: agents capture injected assets (`.cursor/`, `AGENTS.md`, `CLAUDE.md`, `instructions.md`) when they `git add .`. The `.git/info/exclude` approach in the engine doesn't fully prevent this. Filter assets out at apply time.

7. **Apply, verify, commit, push**.
   ```
   pnpm install                             # only if package.json changed
   pnpm --filter @minions/shared run build  # types other packages depend on
   pnpm --filter @minions/engine run typecheck
   pnpm --filter @minions/web run typecheck
   pnpm --filter @minions/engine run test
   pnpm lint
   git add -A && git -c user.email=local@minions -c user.name=local commit -q -m "<subject> (via session <slug>)"
   git push origin main
   ```

8. **Recycle the engine** if you touched engine source. tsx watch is unreliable across rapid edits; use `references/restart-engine.sh` (which honors `.env.local`).

9. **Re-verify in Playwright**. Reload the PWA (hard reload — `Cmd/Ctrl+Shift+R` — to bust the user's cached vite modules). Reproduce the originally-broken view. 1440×900 desktop, 390×844 mobile. Confirm no console errors beyond the manifest-syntax dev warning.

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
