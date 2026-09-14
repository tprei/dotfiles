#!/bin/sh
# Rebuild the patched OMP runtime after a global OMP update wiped the link.
# Reads PIN in this directory for the upstream commit and patch file.
# Refuses to overwrite an existing nonempty source dir. Needs curl, tar,
# git, bun, cargo. Run from anywhere.
set -eu

RUNTIME_DIR=$(dirname "$0")
PATCH="$RUNTIME_DIR/0001-Prevent-main-sessions-from-using-disabled-providers.patch"
UPSTREAM=00085d4e7dfdcfbf302c122fa2682b410a0f43d1
TARBALL="https://codeload.github.com/can1357/oh-my-pi/tar.gz/$UPSTREAM"
SRC=${OMP_SRC:-/home/mbn/src/oh-my-pi}
WORKTREE=${OMP_WORKTREE:-/home/mbn/.worktrees/oh-my-pi-main-driver-no-agy}

[ -f "$PATCH" ] || { echo "missing $PATCH" >&2; exit 1; }
if [ -e "$SRC" ] && [ -n "$(ls -A "$SRC")" ]; then
  echo "refusing to overwrite nonempty $SRC" >&2; exit 1
fi

mkdir -p "$SRC"
curl --fail --location "$TARBALL" -o /tmp/oh-my-pi-"$UPSTREAM".tar.gz
tar -xzf /tmp/oh-my-pi-"$UPSTREAM".tar.gz -C "$SRC" --strip-components=1
git -C "$SRC" init -b upstream-v18.1.18 >/dev/null 2>&1 || true
git -C "$SRC" add -A
git -C "$SRC" commit -m "Upstream OMP v18.1.18 baseline 00085d4" || true
git -C "$SRC" worktree add -b main-driver-no-agy "$WORKTREE" 2>/dev/null || \
  git -C "$SRC" worktree add "$WORKTREE" main-driver-no-agy
git -C "$WORKTREE" am "$PATCH"
bun --cwd="$WORKTREE" install --frozen-lockfile
bun --cwd="$WORKTREE" run build:native
bun --cwd="$WORKTREE/packages/coding-agent" link
sh "$WORKTREE/scripts/link-omp.sh"
realpath /home/mbn/.bun/bin/omp
echo "restart open OMP sessions to load the rebuilt runtime"
