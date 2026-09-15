#!/bin/sh
# Rebuild the patched OMP runtime after a global OMP update wiped the link.
# Reads PIN in this directory for the upstream commit and local patch commits.
# Refuses to overwrite an existing nonempty source dir. Needs curl, tar,
# git, bun, cargo. Run from anywhere.
set -eu

LOCAL_REPO=${OMP_PATCH_REPO:-/home/mbn/src/oh-my-pi}
UPSTREAM=23a5b9ae38864d3f785dc6cbc96eb6d674a1d32d
TARBALL="https://codeload.github.com/can1357/oh-my-pi/tar.gz/$UPSTREAM"
SRC=${OMP_SRC:-/home/mbn/src/oh-my-pi}
WORKTREE=${OMP_WORKTREE:-/home/mbn/.worktrees/oh-my-pi-main-driver-no-agy}
PATCH_COMMITS="df104c3eed1c7b54d2edfe6a6a210102fa25ef82 fb1d6f5cf9f8ee9114707bffbcb589af457db866"

if [ -e "$SRC" ] && [ -n "$(ls -A "$SRC")" ]; then
  echo "refusing to overwrite nonempty $SRC" >&2
  exit 1
fi
mkdir -p "$SRC"

curl --fail --location "$TARBALL" -o /tmp/oh-my-pi-"$UPSTREAM".tar.gz
tar -xzf /tmp/oh-my-pi-"$UPSTREAM".tar.gz -C "$SRC" --strip-components=1
git -C "$SRC" init -b upstream-v18.1.22 >/dev/null 2>&1 || true
git -C "$SRC" add -A
git -C "$SRC" commit -m "Upstream OMP v18.1.22 baseline 23a5b9a" || true
git -C "$SRC" fetch "$LOCAL_REPO" main-driver-no-agy
git -C "$SRC" worktree add -b main-driver-no-agy "$WORKTREE" 2>/dev/null || \
  git -C "$SRC" worktree add "$WORKTREE" main-driver-no-agy
for commit in $PATCH_COMMITS; do
  git -C "$WORKTREE" cherry-pick "$commit"
done
bun --cwd="$WORKTREE" install --frozen-lockfile
bun --cwd="$WORKTREE" run build:native
bun --cwd="$WORKTREE/packages/coding-agent" link
sh "$WORKTREE/scripts/link-omp.sh"
realpath /home/mbn/.bun/bin/omp
echo "restart open OMP sessions to load the rebuilt runtime"
