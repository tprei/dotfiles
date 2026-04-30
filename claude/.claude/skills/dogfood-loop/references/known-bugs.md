# Known bug patterns to recognize fast

These are things this codebase has hit at least once. When an agent's output triggers any of these, recognize the pattern and reach for the fix below before re-dispatching.

> **READ THIS FIRST.** This file mixes two kinds of advice:
> - **Idiomatic** — patterns that are correct in any TS/JS codebase. Generalize freely.
> - **Workaround** — scar tissue specific to this repo or its codex sandbox environment. Don't propagate them. Don't ask agents to copy them into new code without flagging that they're band-aids. Each such entry is marked **(workaround)**.

## Anti-patterns we ALREADY have and will NOT add more of

When an agent's diff would introduce one of these, reject it and re-dispatch with a tighter prompt:

- `cp` from worktree to main as the canonical "deploy" path — **dev-loop only**. Online repos go through `landing.land` which uses `gh pr merge`. Don't write code that ships changes via `cp`.
- Hardcoding port numbers in test configs. Use OS-allocated free ports (`net.createServer().listen(0)` or `get-port`) when there's any chance of running alongside another service. Port `8801` survives only because the operator's engine is on `8787`.
- Shell-sourced env files (`set -a; . .env.local`). The engine now ships its own `dotenv.ts` loader (no shell parsing, no quote-eating). New code should depend on that, not on bash sourcing.
- JSON in env vars. Use a config file under `<workspace>` (`repos.json` is the precedent). `MINIONS_REPOS` is a deprecated fallback that prints a warning.
- `pkill -9` followed by `setsid pnpm run dev`. That's the dogfood hot-loop survival kit, not a deploy pattern. Production uses systemd / docker (`docker-compose.yml`).
- `force: true` on `landing.land` as a default. Only when a smoke test deliberately wants to bypass CI. The dogfood-loop default is `force: false` so readiness gates work.
- `--no-verify` / `allowUnsafe*` / `--allow-empty` to slide past hooks or sandboxes. Fix the underlying issue or surface it.
- Filtering injected assets at apply time as a "feature". That's a leak — the asset-injection design needs to be bind-mount or content-addressable, not "copy + hope". Treat the current filter as transitional.
- `__dirname` / `__filename` / `require()` — this repo is `"type": "module"`. Use `import.meta.url`.
- New components with `bg-zinc-*` / `text-zinc-*` / `border-zinc-*` utilities — they break light mode. Use theme tokens (`bg-bg`, `text-fg`, etc.) which consume CSS variables.
- New Zustand selectors that return new object/array/Set/Map literals — they cause infinite render loops. Use `useShallow` for multi-key, `useMemo` for derived collections.
- `tsx watch` for production. tsx is a dev tool. Production uses `node dist/cli.js` (built via `pnpm --filter @minions/engine run build`).

When you see these in an agent's output, that's the signal: re-dispatch with a fix-the-root-cause prompt rather than landing the patch.

## React / Zustand

### "result of getSnapshot should be cached" → infinite render loop

A selector returns a new reference every call:

```tsx
// BAD
const features = useVersionStore(s => new Set(s.byConnection.get(activeId)?.features ?? []));
const { connections, activeId } = useConnectionStore(s => ({ connections: s.connections, activeId: s.activeId }));
```

Fix:

```tsx
// derive collections from a stable scalar slice
const featureList = useVersionStore(s => activeId ? s.byConnection.get(activeId)?.features : undefined);
const features = useMemo(() => new Set<string>(featureList ?? []), [featureList]);

// multi-key shallow
import { useShallow } from "zustand/react/shallow";
const { connections, activeId } = useConnectionStore(useShallow(s => ({ connections: s.connections, activeId: s.activeId })));
```

## Flexbox

### Panel won't scroll, expanded to content size

A `flex-1 overflow-y-auto` child in a `flex flex-col` parent expands to its scroll height when an ancestor doesn't constrain height. Look up the ancestry: every flex parent on the path from root → scroller needs `h-full` (top-level) and every intermediate flex item needs `min-h-0` (and `min-w-0` for horizontal flow). The scroller itself needs `flex-1 min-h-0 overflow-y-auto`.

Diagnostic via Playwright:

```js
const all = document.querySelectorAll("*");
for (const el of all) {
  const cs = getComputedStyle(el);
  if ((cs.overflowY === "auto" || cs.overflowY === "scroll") && el.scrollHeight > el.clientHeight + 50) {
    console.log("scroller", el.className, el.clientHeight, el.scrollHeight, el.scrollHeight > el.clientHeight);
  }
}
```

## Pointer events

### Resize handle works in dispatch test, doesn't drag for real users

Symptom: `setPointerCapture` + React `onPointerMove` only catches events while the cursor is over the handle. The handle is 1–6px wide; once the cursor moves a few px it's outside.

Fix: in `onPointerDown`, register `document.addEventListener("pointermove", ...)` and `document.addEventListener("pointerup", ...)` for the duration of the drag, remove them on up. Document-level listeners catch movement regardless of where the cursor is.

`packages/web/src/components/ResizeHandle.tsx` already uses this pattern — preserve it.

## Theme

### Light mode toggles class but page renders dark

Tailwind tokens are hard-coded RGB in `tailwind.config.js`; `darkMode: "class"` only flips utility variants, not the base palette. Body's `bg-zinc-950 text-zinc-100` overrides everything.

Fix lives in this repo:
- `packages/web/src/index.css` declares `:root` (light) and `.dark` (dark) CSS variables.
- `packages/web/tailwind.config.js` colors consume `rgb(var(--bg) / <alpha-value>)` etc.
- `packages/web/index.html` body class is `antialiased bg-bg text-fg`.
- `packages/web/src/hooks/useTheme.ts` toggles `.dark` on `documentElement`.

If a new component is added with `bg-zinc-*` / `text-zinc-*` / `border-zinc-*`, sweep with `sed` and replace with theme tokens (`bg-bg-elev`, `text-fg-muted`, etc.).

Note: chrome headless screenshots can render dark even when `getComputedStyle(document.body).backgroundColor` is light. Trust computed styles over screenshots.

## Engine routes

### Endpoint returns 404 even though the file is there

Multiple agents wrote sibling `routes.ts` files for the same endpoint; the registrar in `packages/engine/src/http/routes/index.ts` only imports one of them. Check:

```
grep -rn 'app\.(get|post|patch|delete)' packages/engine/src/ | grep -v test
```

Pick the canonical one, delete the duplicate, fix the `import` in `http/routes/index.ts`. The orchestrator's repo history shows this happened with `/api/sessions` (Engine A vs Engine B) and `/api/sessions/variants` (Engine A stub vs Engine D real impl).

### CORS blocks `/api/events` SSE despite `@fastify/cors` registered

The Fastify CORS plugin doesn't intercept `reply.raw.write(...)` streams. SSE handler in `packages/engine/src/http/sse.ts` must set `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`, `Vary: Origin` on the raw response manually. Preserve this across edits.

## Storage / sqlite

### `node --test src/**/*.test.ts` fails on Ubuntu (works on macOS)

Ubuntu bash has no globstar by default; the literal `**` is passed to node as a path. Use:

```
"test": "node --import tsx --test --test-reporter=spec"
```

(no path argument — node auto-discovers `*.test.*` under cwd).

## Workspace / git

### Repos config — use `repos.json`, not `MINIONS_REPOS` env

The engine reads `<workspace>/repos.json` at boot. The old `MINIONS_REPOS` env JSON still works but logs a warning. **(idiomatic fix; do this in new code.)**

```json
[
  { "id": "self", "label": "claude-minions",
    "remote": "https://github.com/tprei/claude-minions.git", "defaultBranch": "main" }
]
```

If you see an agent introducing JSON-as-env-var anywhere, redirect them to a config file.

### `MINIONS_WORKSPACE=./.dev-workspace` resolves under `packages/engine`

Because pnpm runs the script with `cwd=packages/engine`. Use absolute path. **(workaround — pnpm filter cwd surprise.)**

```
MINIONS_WORKSPACE=$(pwd)/.dev-workspace   # in .env.local, with $(pwd) expanded BEFORE saving
```

### `gitignore` patterns shadow source dirs

`workspace/` (unanchored) matches `packages/engine/src/workspace/` source. Always anchor: `/workspace/`, `/.dev-workspace/`. Same for `/secrets/`, `/data/`, `/.env.deploy`.

### Land step `fatal: invalid upstream 'origin/main'`

The worktree's `origin` is the local bare clone, not GitHub. The bare may not have `origin/main` cached. For online repos, `landing/index.ts` uses `gh pr merge` instead of local rebase + push — don't undo that.

## ESM-only repo gotchas

This repo is `"type": "module"` everywhere. CommonJS-style globals don't exist:

| Don't write | Do write |
|---|---|
| `__dirname` | `path.dirname(fileURLToPath(import.meta.url))` |
| `__filename` | `fileURLToPath(import.meta.url)` |
| `require("foo")` | `import foo from "foo"` |
| `module.exports = {...}` | `export default {...}` |

The `playwright.config.ts` initially shipped with `cwd: __dirname` — CI failed with `ReferenceError: __dirname is not defined in ES module scope`. Fix:

```ts
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
// then use `here` wherever you would have used __dirname
```

Tell agents that produce config files: "this repo is ESM, no `__dirname` / `__filename` / `require` — use `import.meta.url`".

## Codex sandbox restrictions (workaround — environmental, not the codebase's fault)


The user's terminal runs under a codex CLI layer that blocks specific git invocations. Both surface as engine warnings, both are currently UNFIXABLE from inside the engine:

| Operation | Sandbox error |
|---|---|
| `git config core.hooksPath .githooks` from `workspace/worktree.ts` | `Configuring core.hooksPath is not permitted without enabling allowUnsafeHooksPath` — pre-commit hook is INERT in agent worktrees |
| `git commit` via simple-git from `completion/handlers/autoCommit.ts` | `Use of "GIT_EDITOR" is not permitted without enabling allowUnsafeEditor` — auto-commit handler fails silently into audit log |

Workarounds:
- Lint runs in CI anyway (no need for pre-commit).
- Agents commit themselves (the asset-injected `instructions.md` mandates it).
- When auditing for missed commits, check `audit_events` for `session.auto-commit` rows with `committed: false` and commit on behalf if needed.

## Process / port collisions (workaround — dev hot-loop concerns)


### Two vite procs from sibling repos fighting for 5173

`pgrep -fa vite` shows multiple — kill the wrong-repo one with its full pid, not a pattern match.

### Synthetic e2e job kills the operator's running engine

The agent's `playwright.config.ts` defaulted `MINIONS_PORT=8787`. CI is fine; locally the test engine binds the same port the operator is using, the existing engine fails health, the test crashes too. Force `MINIONS_PORT=8801` (or any other) in the playwright `webServer.env`.

### Agent worktree tries to `pnpm dev` and the engine becomes unstable

Sessions that touch dev-server-relevant files sometimes execute `pnpm dev` thinking they're verifying. They aren't — the operator already has dev running. Tell the agent NOT to run pnpm dev / dev:engine / dev:web in the prompt.

## Engine boot / restart hazards

### Engine fails to start with `does not provide an export named '<X>'` after `git pull`

`@minions/shared` is consumed by engine + web at type level *and* at runtime via `dist/`. A pull that adds a new shared export leaves `dist/` stale until rebuilt. Symptom on engine boot:

```
SyntaxError: The requested module '@minions/shared' does not provide an export named 'CLEANUP_DEFAULT_LIMIT'
```

Always rebuild `shared` after pulling, before relaunching:

```
pnpm -C packages/shared build
./bin/engine.sh
```

Bake this into `bin/engine.sh` itself (a `pnpm -C packages/shared build` line at the top) so the trap doesn't fire again. **(workaround until shared/ is built on-demand by engine bootstrap.)**

### Engine OOM during `/api/cleanup/candidates` with `olderThanDays=0`

Cleanup endpoint enumerated all sessions and ran `du -sb` synchronously per worktree. With hundreds of sessions, V8 hits its 4GB default heap and dies with "Ineffective mark-compacts near heap limit". Two layers of fix:

- Pin `NODE_OPTIONS=--max-old-space-size=8192` in `bin/engine.sh` as a safety belt.
- The `/api/cleanup/candidates` endpoint must paginate (`limit`+`cursor`, default 100, max 500) and **never** run `du -sb` in the list endpoint — that work belongs to the bounded `/api/cleanup/preview` endpoint that operates on a selected subset.

When you see the engine die mid-request and the operator says "I clicked Cleanup", this is the cause.

### `Not logged in · Please run /login` from agents after HOME isolation

The per-session settings.json fix (`writeSessionSettings.ts`) sets `HOME=<sessionHomeDir>` so minions don't read the operator's `~/.claude/settings.json`. Side effect: minions also can't see `~/.claude/credentials.json`, so claude-code refuses to spawn with a `Not logged in` banner.

Fix: symlink the operator's auth files into each per-session `<homeDir>/.claude/`:

```ts
const SHARED_AUTH_FILES = ["credentials.json", ".credentials.json"];
for (const f of SHARED_AUTH_FILES) {
  const src = path.join(os.homedir(), ".claude", f);
  if (await exists(src)) await fs.symlink(src, path.join(claudeDir, f));
}
```

Symlinks (not copies) so `/login` flows through to the operator's identity.

### `permissionMode: acceptEdits` agent stalls on Bash prompts

The acceptEdits tier auto-confirms file writes but still prompts for shell commands. With `--print`, the prompt has nothing to confirm against and the call denies. Per-session settings.json must also include:

```json
{ "permissions": { "allow": ["Bash(*)"] } }
```

Sandbox already scopes *where* writes go; permissions.allow scopes *what tools* the agent can invoke without a confirm round-trip.

### Engine inherits the launching shell's sandbox

If the engine is started from inside a Claude Code session (e.g. via the dogfood-loop's Bash tool), every spawned minion inherits Claude Code's sandbox. The minion's worktree is writable but the worktree's gitdir (`.dev-workspace/.repos/self.git/worktrees/<slug>/`) is *not*, so `git add` / `git commit` fail with "Read-only file system" and the agent leaves a `/tmp/claude/*.patch` instead.

Detection:

```
PPID_OF_ENGINE=$(cat /proc/$(pgrep -f 'tsx.*engine' | head -1)/status | awk '/^PPid:/ {print $2}')
ps -p $PPID_OF_ENGINE -o cmd=    # claude / claude-code → sandbox inherited
```

There is no in-skill workaround. **The operator must launch `./bin/engine.sh` from their own terminal**, outside any Claude Code session. The dogfood-loop should refuse to dispatch when the engine PID's parent is a claude process and ask the operator to relaunch.

### `gh pr edit --base` fails with `projectCards` GraphQL deprecation

```
GraphQL: Projects (classic) is being deprecated ... (repository.pullRequest.projectCards)
```

This is GitHub-side; not the engine's bug. The `gh` CLI tries to read projectCards in its mutation response and the API now refuses. Two recoveries:

- Upgrade `gh` to ≥ 2.55 (mutation no longer requests projectCards).
- Or update the base via REST directly: `gh api -X PATCH /repos/<owner>/<repo>/pulls/<n> -f base=<branch>`.

Matters because the engine's `RestackManager` uses `gh pr edit --base` to bump auto-restacked children's bases when their parent merges. When this errors, children's PR bases stay pointing at the deleted parent branch and GitHub auto-closes them. See `references/restack-after-merge.md` for the recovery dance this triggers.

### Two `registerXxxRoutes` files, second silently dropped by Fastify

Pattern: `packages/engine/src/http/routes/dags.ts` (older) and `packages/engine/src/dag/routes.ts` (newer with the `retry` endpoint) both call `registerDagRoutes(app)`. Fastify de-dupes by route key on a duplicate registration and the *second* registration's routes simply don't exist — `POST /api/dags/:dagId/nodes/:nodeId/retry` returns 404 even though the source is right there.

Detection:

```
rg -n "app\.(get|post|patch|delete)\(['\"]/api" packages/engine/src/ \
  | grep -v test \
  | awk -F'"' '{print $2}' \
  | sort | uniq -d
```

Anything output = silent shadow. Fix: pick one canonical file, delete the other, ensure `http/routes/index.ts` imports the correct one. Add this grep to pre-dispatch gates whenever a batch adds new endpoints — multiple parallel sessions adding sibling `routes.ts` files is exactly how this re-occurs.

### Sessions stuck in `pending` consume admission slots forever

Sessions sometimes get stuck at `pending` because `provider.spawn` (via `findClaudeBinary` → `which claude`) hangs without a timeout. The session never transitions to `running`, `listAdmittedSession` counts it toward the slot cap, and admission denies new dispatches forever.

Mitigations now in the engine:
- A 30-60s timeout wrapping `provider.spawn` flips the session to `failed` with `manual_intervention` attention.
- A periodic sweeper logs sessions in `pending > 60s` for review.

But the underlying spawn flakiness can recur. Pre-batch sweep:

```bash
TOKEN=$(grep '^MINIONS_TOKEN=' .env.local | cut -d= -f2)
NOW=$(date +%s)
curl -sH "Authorization: Bearer $TOKEN" http://127.0.0.1:8787/api/sessions \
  | python3 -c "
import json,sys,datetime
items = json.load(sys.stdin)['items']
for s in items:
    if s['status'] != 'pending': continue
    age = (datetime.datetime.now(datetime.timezone.utc)
           - datetime.datetime.fromisoformat(s['createdAt'].replace('Z','+00:00'))).total_seconds()
    if age > 120:
        print(s['slug'], int(age))
"
```

Stop each (`POST /api/commands {kind:'stop', sessionSlug:...}`) before dispatching new work.

### "You're out of extra usage · resets HH:MM (TZ)" mid-batch

API quota for the engine's claude-code integration. Recognize the line in any tool output and stop dispatching immediately. Resuming earlier than the reset just burns retry budget on dead-on-arrival sessions. Schedule a wakeup near the reset time and re-enter the loop then.

### Session status visible as `cancelled` after PR merge despite work shipping

`ci/prLifecycle.ts` used to call `sessions.stop()` on PR-merged → clobbered the already-`completed` status to `cancelled`. The fix gates the stop on `status !== 'completed'`. If you see this regress, it's `prLifecycle.ts` again — the call path must check terminal-status before transitioning.

### DAG aggregator reports `failed` when all nodes landed

DAG status is computed from node statuses. If `landed` isn't treated as success in the rollup, a fully shipped DAG shows `status: failed` cosmetically. Symptom: every node has PR merged, DAG card still shows failure. Check the aggregator at `packages/engine/src/dag/index.ts` — `landed` must count as terminal-success, same as if the DAG had no children.

### `failedReason: "session terminated with status: running"` on DAG node

A race in the dag-terminal handler — it reads `session.status` before the registry's terminal-status update has committed. The reason string is impossible (`running` isn't terminal) and a giveaway. Fix: handler must read the post-update status, or wait on the registry's terminal event instead of polling. Until fixed, retry the node — the second pass usually wins the race.

### `Body cannot be empty when content-type is set to 'application/json'`

Fastify's body parser rejects POST requests with a JSON content-type and an empty body. Web client posts `{}`-less; route registration declares the body is JSON. Either (a) make the route's body schema optional with `.nullable()`, (b) have the web client always send `{}`, or (c) drop the Content-Type header for body-less posts. Pick (b) — it's the smallest change and matches Fastify's expectations.
