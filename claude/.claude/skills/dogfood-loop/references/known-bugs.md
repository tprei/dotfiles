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
