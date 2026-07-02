# Prompt template for a single dogfood session

```
{
  "title": "<short, imperative subject>",
  "repoId": "<your-repo-id>",
  "baseBranch": "main",
  "mode": "task",
  "prompt": "<one-paragraph context: why we're doing this, what's currently wrong, including the *exact* user-flow that fails today if this is a bug fix>\n\nFiles in scope (touch only these):\n- <path/a>\n- <path/b>\n\nDo:\n1. <concrete change>\n2. <concrete change>\n3. Add a regression test (REQUIRED — the dogfood loop's value is the guard, not the fix):\n   - Backend / library work: a unit or integration test in the project's test framework, asserting the failing behavior passes.\n   - Frontend / UI work: an end-to-end test (Playwright or equivalent) exercising the user-reported flow.\n   - For mode/stage features (anything with a behavioral constraint): the test MUST encode the contract, not just the happy path. Example: a read-only-mode test dispatches a session that is *asked* to modify code and asserts `git diff --stat` is empty after the turn ends. A reply-injection test posts a uniquely-tagged reply and asserts the next assistant_text contains the tag (proves the agent saw it, not just that the event landed).\n   The test must FAIL on current main and PASS with your fix. Run it both ways to verify.\n\nDon't:\n- Add new files unless listed (the regression test counts as listed).\n- Skip the regression test 'because the change is small' — every dogfood task lands a guard. No exceptions.\n- Refactor adjacent code.\n- Run dev servers (the operator already has those running). Just typecheck and test.\n- Use a default port for any new dev server, test orchestrator, or preview server — pick something distinctive so you don't collide with the operator's live processes.\n\nVerify (in this order):\n1. Project typecheck — iterate until clean.\n2. Project test command (or e2e for UI) — the regression test you added must pass.\n3. Project build for any UI changes.\n4. Project lint.\n\nCommit on the worktree (REQUIRED — auto-commit handlers are often inert under host agentic-CLI sandboxes):\n  git add . && git -c user.email=session@dogfood.local -c user.name=dogfood-session commit -m '<subject>'\n\nIf the commit fails for sandbox reasons (GIT_EDITOR / hooksPath denied), DO NOT use --no-verify. Instead leave the changes uncommitted; the operator will commit on apply.\n"
}
```

## What to leave OUT

- "Use best practices" — say what you actually want.
- "Iterate until perfect" — give the agent one explicit completion bar (typecheck + regression test + commit landed).
- File-tree exploration prompts — the agent has the worktree mounted; let it use Read/Grep on demand.
- `--no-verify` or `allowUnsafe*` — if a hook fails, the underlying issue gets fixed, not bypassed.

## What to leave IN

- Exact file paths (and the explicit "stay in scope" line).
- The exact failing flow if this is a user-reported bug — the regression test needs it verbatim. "Click X, observe Y" beats "fix the chat closing".
- A regression-test requirement under Do (backend: unit/integration; UI: e2e). Every dogfood task lands a guard.
- Acceptable surface for new modules (e.g. "you may create one new helper at `<path>` if needed").
- The verify command, including running the new regression test both with and without the fix.
- The commit incantation, including a dummy author so commits don't pick up the host user's identity.
- A "do not run dev servers" note for sessions that touch packages already under `dev`.

## Sizing the work

- 30–80 turn sessions are the sweet spot. > 120 turns and the agent is usually fighting an unstated constraint or hit a quota wall — read the last 5 transcript events.
- 0 turns ≈ killed mid-spawn. Re-dispatch.
- Strong scope reduces both turns and revert risk.

## When two sessions need to touch the same file

Don't. Sequence them — finish one, apply, then dispatch the other on top of fresh main. Two parallel sessions on the same file is a recipe for last-writer-wins regressions, where the agent that finishes second silently reverts the first.
