# Applying a session's diff to main

A finished session leaves its work in `.dev-workspace/<slug>/` either as a worktree commit (`git log main..HEAD` non-empty) or as uncommitted modifications (`git status -- M`). Sometimes both — the agent commits a partial change and leaves more uncommitted afterwards. Treat them uniformly.

## Inspect

```
WT=.dev-workspace/<slug>
git -C $WT log --oneline main..HEAD | head
git -C $WT diff main..HEAD --stat
git -C $WT status --short | grep -v '^??'           # tracked changes
git -C $WT status --short | grep '^??' | head        # untracked (mostly assets, see below)
```

## Files agents commit-by-accident

The engine's asset injector copies these into every worktree:

```
AGENTS.md
CLAUDE.md
instructions.md
.cursor/
```

It also writes them to `<gitdir>/info/exclude`, but `git add .` from the agent re-includes them under the codex sandbox in some cases. **Always filter these out at apply time** — they are not part of the change, they're agent context.

## Apply pattern

For mostly file-by-file diffs (which is what almost every session produces here):

```
WT=.dev-workspace/<slug>

# Files the agent committed
git -C $WT diff main..HEAD --name-only | while read f; do
  case "$f" in
    AGENTS.md|CLAUDE.md|instructions.md|.cursor/*) continue ;;
  esac
  cp "$WT/$f" "$f"
done

# Files the agent left uncommitted
git -C $WT status --short | awk '$1 ~ /^[MARC]/ {print $2}' | while read f; do
  case "$f" in
    AGENTS.md|CLAUDE.md|instructions.md|.cursor/*) continue ;;
  esac
  cp "$WT/$f" "$f"
done

# New files the agent added (untracked, but check before blanket-copying)
git -C $WT status --short | awk '$1 == "??" {print $2}' | while read f; do
  case "$f" in
    AGENTS.md|CLAUDE.md|instructions.md|.cursor/*) continue ;;
    .bashrc|.zshrc|.profile|.gitconfig|.mcp.json|.idea*|.bash_profile|.zprofile|.ripgreprc|.gitmodules|.vscode*) continue ;;  # claude scratch dotfiles
    *) cp "$WT/$f" "$f" 2>/dev/null || true ;;
  esac
done
```

For sessions that produce a large multi-package change (new package, sweeping rename), `rsync` is more reliable:

```
rsync -a --exclude=node_modules --exclude=dist \
      --exclude=AGENTS.md --exclude=CLAUDE.md --exclude=instructions.md --exclude='.cursor/' \
      $WT/packages/<new-pkg>/ packages/<new-pkg>/
```

## Verify

```
pnpm install                             # only if package.json or pnpm-lock changed
pnpm --filter @minions/shared run build  # if shared types changed
pnpm --filter @minions/engine run typecheck
pnpm --filter @minions/web run typecheck
pnpm --filter @minions/engine run test
pnpm lint
pnpm --filter @minions/web run build     # for web changes
```

Reject the diff and re-dispatch (or fix small drift inline) when:

- Typecheck fails on a renamed shared type — usually means the agent didn't read `packages/shared/src` and invented a parallel type. Re-dispatch with the canonical type explicitly.
- Lint shows new errors (warnings are fine — eslint config sets most rules to `warn`).
- Tests regress.
- Engine fails to start with the new code (read `/tmp/engine.log`).

## Commit

One commit per dogfood batch. Subject names what landed; body lists the source sessions:

```
git add -A
git -c user.email=local@minions -c user.name=local commit -q -m "<subject>

- <fix area> (via session <slug>)
- <fix area> (via session <slug>)
"
git push origin main
```

The `local@minions` author ID makes operator-applied commits distinguishable from agent self-commits (which use `engine@minions.local`).

## Don't

- Don't `git apply` a diff captured via `git format-patch` — it loses the index state and chokes on concurrent edits.
- Don't `cherry-pick` from the worktree branch onto main directly — main has been advancing while the session ran, and the cherry-pick may include parts of the worktree's bootstrap state.
- Don't skip the typecheck-and-test pass thinking "lint covers it". Lint doesn't catch type drift.
