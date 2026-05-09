# Re-stacking child PRs after a parent merges

When a DAG ships a stack of PRs (A ← B ← C, each PR's `base` set to the previous worktree branch), merging the parent typically triggers two things on GitHub:

1. The parent's branch is deleted (the `--delete-branch` flag on `gh pr merge`).
2. Every child whose `base` was the deleted branch is **auto-closed** by GitHub. Not "stays open with broken base" — closed, with state `CLOSED`.

This is the single biggest source of friction in a stacked-DAG dogfood loop. The orchestrator's restack manager is supposed to bump the bases first, but racing with `gh pr merge --delete-branch` is unreliable, and `gh pr edit --base` sometimes 4xx's with a `projectCards` GraphQL deprecation error (see `known-bugs.md`).

Net effect: every merged parent leaves you with N auto-closed children to recover by hand.

## Recovery pattern (one child)

```bash
CHILD_BRANCH=$(gh pr view <closed-pr> --repo <owner>/<repo> --json headRefName -q .headRefName)

cd /tmp && rm -rf restack-$CHILD_BRANCH
git clone --quiet -b "$CHILD_BRANCH" "https://github.com/<owner>/<repo>.git" "restack-$CHILD_BRANCH"
cd restack-$CHILD_BRANCH

git fetch origin main
# `--onto main` rebases the child's commits straight onto current main, dropping the parent's commits
# (those landed via the squash-merge). <old-parent-base> is the SHA the child branched from.
OLD_PARENT_BASE=$(git merge-base HEAD origin/main)
git rebase --onto origin/main "$OLD_PARENT_BASE"

# Resolve any conflicts (see "Common conflict shapes" below). Continue rebasing until clean.

git push --force-with-lease origin "$CHILD_BRANCH"
gh pr create --repo <owner>/<repo> --base main --head "$CHILD_BRANCH" \
  --title "<original title> (re-stack)" \
  --body "Re-open after parent merged. Original PR <closed-pr> auto-closed when its base branch was deleted."
```

The `restack-$CHILD_BRANCH` work-tree under `/tmp` keeps the recovery isolated from your live worktrees. Delete it on success.

## Recovery pattern (many children in one shot)

When a parent had 3+ stacked children, do them in parallel:

```bash
PARENT_BASE=<sha-the-children-branched-from>
for branch in $CHILD_BRANCHES; do
  (
    cd /tmp && rm -rf "restack-$branch"
    git clone --quiet -b "$branch" "$REMOTE" "restack-$branch"
    cd "restack-$branch"
    git fetch origin main
    git rebase --onto origin/main "$PARENT_BASE" 2>&1 | tee rebase.log
  ) &
done
wait
```

Then walk each clone, resolve conflicts manually (the loop above leaves rebase incomplete on conflict), `git push --force-with-lease`, and `gh pr create` for each.

## Common conflict shapes

The conflicts here aren't random — they cluster around files that several children all touched. Two patterns recur regardless of the codebase:

### Multiple parallel sessions added fields to the same data structure

Pattern:

```
<<<<<<< HEAD
        someField: actualValue,
=======
        someField: 0,
>>>>>>> <other-session> (session:n6jjf5l3ec ...)
```

Always keep the populated value, drop the placeholder. Same with imports — keep both, dedupe.

### Children added complementary helpers in the same module

When two children both add to a registrar/dispatcher/coordinator, the `<<<<<<< HEAD ... =======` chunks usually wrap *complementary* helpers. Keep both — they don't overlap functionally.

If a conflict is non-trivial (>30 lines, behavioral overlap, types changed shape), close the child PR with a comment ("non-trivial conflict — re-open via fresh dispatch") and re-dispatch the work as a fresh task on top of new main. The closed PR's branch is fine to delete; the dispatch will produce a new branch.

## Prevention: prefer flat DAGs

When writing the dispatch prompt for a multi-node ship, set every node's `baseBranch` to `main`. The DAG scheduler's stack-merge story exists, but it's strictly cheaper to land 4 PRs against `main` than to debug 4 cascading auto-closes.

The exception: ships where node N's *content* genuinely depends on node N-1's content (not just type signatures, but actual semantic prerequisites). Type-only dependencies should be in a shared package and don't require stacking.

## Prevention: --admin for the parent merge

When merging a parent that has children open, the safer order is:

```bash
gh pr merge <parent> --squash --delete-branch=false --admin   # leave the branch
# rebase children onto main first, push, update their bases via gh pr edit --base main
# only then delete the parent branch
git push origin --delete <parent-branch>
```

This avoids the auto-close burst entirely. Trade-off: more steps, but no recovery dance.
