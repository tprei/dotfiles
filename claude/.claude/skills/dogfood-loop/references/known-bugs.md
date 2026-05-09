# Bug-pattern categories that recur in dogfood loops

These are the categories of bug that show up again and again when an agentic orchestrator dispatches parallel coding sessions. When an agent's output triggers any of these, recognize the pattern and reach for the fix below before re-dispatching.

> **READ THIS FIRST.** This file mixes two kinds of advice:
> - **Idiomatic** — patterns that are correct in any TS/JS codebase. Generalize freely.
> - **Workaround** — scar tissue specific to a particular orchestrator or sandbox environment. Don't propagate them. Don't ask agents to copy them into new code without flagging that they're band-aids. Each such entry is marked **(workaround)**.

## Anti-patterns to reject in agent diffs

When an agent's diff would introduce one of these, reject it and re-dispatch with a tighter prompt:

- `cp` from worktree to main as the canonical "deploy" path — that's a **dev-loop only** mechanism. Online repos go through the orchestrator's landing flow (push branch + open PR + `gh pr merge`). Don't write code that ships changes via `cp`.
- Hardcoding port numbers in test configs. Use OS-allocated free ports (`net.createServer().listen(0)` or a `get-port`-style helper) when there's any chance of running alongside another service.
- Shell-sourced env files (`set -a; . .env.local`). Prefer a dotenv loader the orchestrator runs in-process (no shell parsing, no quote-eating).
- JSON in env vars. Use a config file under the workspace instead. Env-JSON is fragile under shell sourcing.
- `pkill -9` followed by `setsid <dev-cmd>`. That's the dogfood hot-loop survival kit, not a deploy pattern. Production should use systemd / docker / equivalent.
- `force: true` on the orchestrator's land command as a default. Only when a smoke test deliberately wants to bypass CI. The dogfood-loop default should be `force: false` so readiness gates work.
- `--no-verify` / `allowUnsafe*` / `--allow-empty` to slide past hooks or sandboxes. Fix the underlying issue or surface it.
- Filtering injected assets at apply time as a "feature". That's a leak — the asset-injection design should be bind-mount or content-addressable, not "copy + hope". Treat the current filter as transitional.
- `__dirname` / `__filename` / `require()` in an ESM-only project (`"type": "module"`). Use `import.meta.url`.
- New components with hard-coded color utilities (`bg-zinc-*` / `text-zinc-*` / `border-zinc-*` etc.) — they break theme switching. Use theme tokens that consume CSS variables.
- New state-store selectors that return new object/array/Set/Map literals — they cause infinite render loops. Use a shallow-compare wrapper for multi-key selects, `useMemo` for derived collections.
- Watch-mode dev tools (`tsx watch`, `nodemon`) for production. Production should use the built output (`node dist/...` after a build step).

When you see these in an agent's output, that's the signal: re-dispatch with a fix-the-root-cause prompt rather than landing the patch.

## React / state-store patterns

### "result of getSnapshot should be cached" → infinite render loop

A selector returns a new reference every call:

```tsx
// BAD
const features = useStore(s => new Set(s.byConnection.get(activeId)?.features ?? []));
const { connections, activeId } = useStore(s => ({ connections: s.connections, activeId: s.activeId }));
```

Fix:

```tsx
// derive collections from a stable scalar slice
const featureList = useStore(s => activeId ? s.byConnection.get(activeId)?.features : undefined);
const features = useMemo(() => new Set<string>(featureList ?? []), [featureList]);

// multi-key shallow
import { useShallow } from "zustand/react/shallow";  // or your store's equivalent
const { connections, activeId } = useStore(useShallow(s => ({ connections: s.connections, activeId: s.activeId })));
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

## Theme

### Light mode toggles class but page renders dark

Tailwind tokens are hard-coded RGB; `darkMode: "class"` only flips utility variants, not the base palette. Body's `bg-zinc-950 text-zinc-100` overrides everything.

Pattern that works:
- `:root` (light) and `.dark` (dark) declare CSS variables in the global stylesheet.
- Tailwind config colors consume `rgb(var(--bg) / <alpha-value>)` etc.
- Body class is the theme tokens (`bg-bg`, `text-fg`).
- A theme hook toggles `.dark` on `documentElement`.

If a new component is added with hard-coded color utilities, sweep with `sed` and replace with theme tokens.

Note: chrome headless screenshots can render dark even when `getComputedStyle(document.body).backgroundColor` is light. Trust computed styles over screenshots.

## HTTP framework / routes

### Endpoint returns 404 even though the file is there

Multiple agents wrote sibling files registering the same route key; the registrar only imports one of them. Many frameworks (Fastify is a notable example) silently drop the second registration for a duplicate key. Check:

```
rg -n "app\.(get|post|patch|delete)\(['\"]/api" <src-dir> | grep -v test
```

Pick the canonical one, delete the duplicate, fix the `import` in the registrar.

### CORS works on REST but SSE blocked

Many CORS plugins don't intercept raw response streams (e.g. `reply.raw.write(...)` in Fastify). The SSE handler must set `Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`, `Vary: Origin` on the raw response manually. Preserve this across edits.

## Test runners

### Glob argument fails on Linux but works on macOS

Bash on Linux often has globstar disabled by default; the literal `**` is passed to the runner as a path. Either enable globstar (`shopt -s globstar`) or rely on the test runner's auto-discovery (no path argument).

## Workspace / git

### Stale bare clone causes every dispatched diff to revert recent work

If the orchestrator branches sessions from a local bare clone, the bare may not auto-fetch when main advances. Symptom: every dispatched diff comes back missing recent commits because the worktree branched from a stale SHA. Pre-dispatch gate:

```
test "$(git -C "$BARE" rev-parse main)" = "$(git rev-parse main)" \
  || git -C "$BARE" fetch origin main:main --force
```

If this fires repeatedly, the orchestrator's per-worktree force-fetch logic regressed.

### `gitignore` patterns shadow source dirs

Unanchored entries like `workspace/` match any path containing that directory name (including `<src>/workspace/` source). Always anchor: `/workspace/`, `/.dev-workspace/`. Same for `/secrets/`, `/data/`, `/.env.deploy`.

### Land step `fatal: invalid upstream 'origin/main'`

When the worktree's `origin` is a local bare clone (not GitHub directly), the bare may not have `origin/main` cached. For online repos, the orchestrator's landing flow should use `gh pr merge` instead of local rebase + push — local rebase is brittle when the bare's `origin/<base>` ref doesn't match GitHub's HEAD.

## ESM-only repo gotchas

Projects with `"type": "module"` everywhere lack CommonJS-style globals:

| Don't write | Do write |
|---|---|
| `__dirname` | `path.dirname(fileURLToPath(import.meta.url))` |
| `__filename` | `fileURLToPath(import.meta.url)` |
| `require("foo")` | `import foo from "foo"` |
| `module.exports = {...}` | `export default {...}` |

A common failure mode: `playwright.config.ts` shipped with `cwd: __dirname` — CI fails with `ReferenceError: __dirname is not defined in ES module scope`. Fix:

```ts
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
// then use `here` wherever you would have used __dirname
```

Tell agents that produce config files: "this repo is ESM, no `__dirname` / `__filename` / `require` — use `import.meta.url`".

## Host agentic-CLI sandbox restrictions (workaround — environmental, not the codebase's fault)

When the orchestrator runs under a host agentic CLI's sandbox (Claude Code, codex CLI, etc.), specific git invocations are blocked:

| Operation | Sandbox error |
|---|---|
| `git config core.hooksPath .githooks` from a worktree-prep step | `Configuring core.hooksPath is not permitted without enabling allowUnsafeHooksPath` — pre-commit hook is INERT in agent worktrees |
| `git commit` via simple-git from an auto-commit completion handler | `Use of "GIT_EDITOR" is not permitted without enabling allowUnsafeEditor` — auto-commit handler fails silently into audit log |

Workarounds:
- Lint runs in CI anyway (no need for pre-commit).
- Agents commit themselves (the asset-injected `instructions.md` should mandate it).
- When auditing for missed commits, check the orchestrator's audit log for auto-commit rows with `committed: false` and commit on behalf if needed.

## Process / port collisions (workaround — dev hot-loop concerns)

### Two dev-server procs from sibling repos fighting for the same port

Patterns like `pgrep -fa vite` show multiple — kill the wrong-repo one with its full pid, not a pattern match.

### Synthetic e2e job kills the operator's running orchestrator

The agent's `playwright.config.ts` defaulted to the orchestrator's standard port. CI is fine; locally the test orchestrator binds the same port the operator is using, the existing instance fails health, the test crashes too. Force a distinctive port in the test runner's `webServer.env`.

### Agent worktree tries to `dev` and the orchestrator becomes unstable

Sessions that touch dev-server-relevant files sometimes execute `dev` thinking they're verifying. They aren't — the operator already has dev running. Tell the agent NOT to run `dev` in the prompt.

## Orchestrator boot / restart hazards

### Orchestrator fails to start with `does not provide an export named '<X>'` after `git pull`

A shared package consumed at runtime (via its `dist/`) goes stale when types change but the build hasn't been rerun. Always rebuild shared packages after pulling, before relaunching:

```
<rebuild-shared-packages>
<start-orchestrator>
```

Bake this into the start script itself so the trap doesn't fire again. **(workaround until shared/ is built on-demand by orchestrator bootstrap.)**

### Orchestrator OOMs at default heap during heavy enumeration endpoint

A cleanup or audit endpoint enumerated all sessions and ran sync `du`-like work per worktree. With hundreds of sessions, V8 hits its 4GB default heap and dies. Two layers of fix:

- Pin `NODE_OPTIONS=--max-old-space-size=8192` in the start script as a safety belt.
- The endpoint must paginate (`limit`+`cursor`, default 100, max 500) and **never** run sync filesystem-walking work in the list endpoint — that work belongs to a bounded preview endpoint that operates on a selected subset.

### `Not logged in · Please run /login` from agents after HOME isolation

If per-session settings.json sets `HOME=<sessionHomeDir>` so sessions don't read the operator's `~/.claude/settings.json`, sessions also can't see `~/.claude/credentials.json`, so the agentic CLI refuses to spawn with a `Not logged in` banner.

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

### Orchestrator inherits the launching shell's sandbox

If the orchestrator is started from inside an agentic CLI session (e.g. via the dogfood-loop's Bash tool), every spawned sub-agent inherits that CLI's sandbox. The session's worktree is writable but the worktree's gitdir is *not*, so `git add` / `git commit` fail with "Read-only file system" and the agent leaves a `/tmp/<scratch>/*.patch` instead.

Detection:

```
PPID_OF_ORCH=$(cat /proc/$(pgrep -f '<orchestrator-cmd-pattern>' | head -1)/status | awk '/^PPid:/ {print $2}')
ps -p $PPID_OF_ORCH -o cmd=    # claude / claude-code / codex → sandbox inherited
```

There is no in-skill workaround. **The operator must launch the orchestrator from their own terminal**, outside any agentic CLI session. The dogfood-loop should refuse to dispatch when the orchestrator's parent process is an agentic CLI and ask the operator to relaunch.

### `gh pr edit --base` fails with `projectCards` GraphQL deprecation

```
GraphQL: Projects (classic) is being deprecated ... (repository.pullRequest.projectCards)
```

This is GitHub-side; not the orchestrator's bug. The `gh` CLI tries to read projectCards in its mutation response and the API now refuses. Two recoveries:

- Upgrade `gh` to ≥ 2.55 (mutation no longer requests projectCards).
- Or update the base via REST directly: `gh api -X PATCH /repos/<owner>/<repo>/pulls/<n> -f base=<branch>`.

Matters because the orchestrator's restack flow uses `gh pr edit --base` to bump auto-restacked children's bases when their parent merges. When this errors, children's PR bases stay pointing at the deleted parent branch and GitHub auto-closes them. See `restack-after-merge.md` for the recovery dance this triggers.

### Two registration files, second silently dropped by the framework

Pattern: two parallel sessions add sibling files registering the same route/plugin/handler key. Many frameworks de-dupe by key on a duplicate registration and the *second* registration silently doesn't exist — the endpoint returns 404 even though the source is right there.

Detection (adapt to your framework):

```
rg -n "app\.(get|post|patch|delete)\(['\"]/api" <src-dir> \
  | grep -v test \
  | awk -F'"' '{print $2}' \
  | sort | uniq -d
```

Anything output = silent shadow. Fix: pick one canonical file, delete the other, ensure the registrar imports the correct one. Add this grep to pre-dispatch gates whenever a batch adds new endpoints.

### Sessions stuck in `pending` consume admission slots forever

Sessions sometimes get stuck at `pending` because `provider.spawn` (e.g. via `which <cli>` lookup) hangs without a timeout. The session never transitions to `running`, the admission tracker counts it toward the slot cap, and admission denies new dispatches forever.

Mitigations on the orchestrator side:
- A 30-60s timeout wrapping `provider.spawn` flips the session to `failed` with `manual_intervention` attention.
- A periodic sweeper logs sessions in `pending > 60s` for review.

But the underlying spawn flakiness can recur. Pre-batch sweep:

```bash
NOW=$(date +%s)
curl -sH "Authorization: Bearer $TOKEN" "$ORCH_URL/api/sessions" \
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

Stop each via the orchestrator's stop command before dispatching new work.

### "out of usage / quota exhausted · resets HH:MM" mid-batch

API quota for the agentic CLI is exhausted. Recognize the line in any tool output and stop dispatching immediately. Resuming earlier than the reset just burns retry budget on dead-on-arrival sessions. Schedule a wakeup near the reset time and re-enter the loop then.

### Session status regresses from `completed` to `cancelled` after PR merge

If the post-merge handler unconditionally calls `sessions.stop()` for a merged PR, it can clobber an already-`completed` status to `cancelled`. The fix: gate the stop on `status !== 'completed'` (or whatever your terminal-status set is). The transition path must check terminal-status before transitioning.

### DAG aggregator reports `failed` when all nodes landed

DAG status is computed from node statuses. If `landed` isn't treated as success in the rollup, a fully shipped DAG shows `status: failed` cosmetically. Symptom: every node has PR merged, DAG card still shows failure. The aggregator must count `landed` as terminal-success.

### `failedReason: "session terminated with status: running"` on DAG node

A race in the dag-terminal handler — it reads `session.status` before the registry's terminal-status update has committed. The reason string is impossible (`running` isn't terminal) and a giveaway. Fix: handler must read the post-update status, or wait on the registry's terminal event instead of polling. Until fixed, retry the node — the second pass usually wins the race.

### `Body cannot be empty when content-type is set to 'application/json'`

Strict body parsers (Fastify is one example) reject POST requests with a JSON content-type and an empty body. Web client posts `{}`-less; route registration declares the body is JSON. Either (a) make the route's body schema optional with `.nullable()`, (b) have the web client always send `{}`, or (c) drop the Content-Type header for body-less posts. Pick (b) — it's the smallest change and matches the parser's expectations.
