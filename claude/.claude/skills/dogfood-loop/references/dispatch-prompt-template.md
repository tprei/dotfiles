# Prompt template for a single dogfood session

```
{
  "title": "<short, imperative subject>",
  "repoId": "self",
  "baseBranch": "main",
  "mode": "task",
  "prompt": "<one-paragraph context: why we're doing this, what's currently wrong>\n\nFiles in scope (touch only these):\n- <path/a>\n- <path/b>\n\nDo:\n1. <concrete change>\n2. <concrete change>\n\nDon't:\n- Add new files unless listed.\n- Add tests unless they cover non-trivial logic introduced here.\n- Refactor adjacent code.\n- Run `pnpm dev`, `pnpm dev:engine`, or `pnpm dev:web` — the operator already has those running. Just typecheck.\n- Use a default port for any new dev server, test engine, or vite preview — pick something distinctive (e.g. 8801) so we don't collide with the operator's live engine on 8787.\n\nVerify: pnpm --filter <package> run typecheck. Iterate until clean. Then `pnpm --filter @minions/web run build` if you changed web sources.\n\nCommit on the worktree (REQUIRED — the orchestrator's auto-commit handler is currently inert under the codex sandbox):\n  git add . && git -c user.email=engine@minions.local -c user.name=minions-engine commit -m '<subject>'\n\nIf the commit fails for sandbox reasons (GIT_EDITOR / hooksPath denied), DO NOT use --no-verify. Instead leave the changes uncommitted; the operator will commit on apply.\n"
}
```

## What to leave OUT

- "Use best practices" — say what you actually want.
- "Add tests" — only when tests carry non-trivial behavior. Otherwise tests are a fixed-cost tax.
- "Iterate until perfect" — give the agent one explicit completion bar (typecheck clean, commit landed).
- File-tree exploration prompts — the agent has the worktree mounted; let it use Read/Grep on demand.
- `--no-verify` or `allowUnsafe*` — if a hook fails, the underlying issue gets fixed, not bypassed.

## What to leave IN

- Exact file paths (and the explicit "stay in scope" line).
- Acceptable surface for new modules (e.g. "you may create one new helper at `<path>` if needed").
- The verify command.
- The commit incantation, including the dummy author so commits don't pick up the host user's identity.
- A "do not run dev servers" note for sessions that touch packages already under `pnpm dev`.

## Sizing the work

- 30–80 turn sessions are the sweet spot. > 120 turns and the agent is usually fighting an unstated constraint or hit a quota wall — read the last 5 transcript events.
- 0 turns ≈ killed mid-spawn. Re-dispatch.
- Strong scope reduces both turns and revert risk.

## When two sessions need to touch the same file

Don't. Sequence them — finish one, apply, then dispatch the other on top of fresh main. Two parallel sessions on `views/sidebar.tsx` already reverted a Zustand selector fix in this repo's history.
