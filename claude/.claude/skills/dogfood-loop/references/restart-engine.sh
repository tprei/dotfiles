#!/usr/bin/env bash
# Idempotent engine restart for the claude-minions dogfood loop.
# Prefers bin/engine.sh + .env.local. Falls back to plain pnpm if .env.local missing.
# Run from the repo root: ./scripts/restart-engine.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd 2>/dev/null || echo "$(pwd)")"
cd "$ROOT"

PORT=${MINIONS_PORT:-8787}

# Kill any existing engine listening on PORT, plus any stray tsx watch
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  PIDS=$(ss -tlnp 2>/dev/null | grep ":$PORT " | sed -E 's/.*pid=([0-9]+).*/\1/' | sort -u)
  for p in $PIDS; do
    kill -9 "$p" 2>/dev/null || true
  done
fi
pkill -9 -f "tsx watch.*minions/engine\|@minions/engine.*pnpm" 2>/dev/null || true
sleep 3

if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: port $PORT still bound after pkill — investigate" >&2
  ss -tlnp 2>/dev/null | grep ":$PORT " >&2
  exit 1
fi

LOG=${ENGINE_LOG:-/tmp/engine.log}

if [ -x bin/engine.sh ] && [ -f .env.local ]; then
  setsid bin/engine.sh > "$LOG" 2>&1 < /dev/null &
  disown
else
  # Fallback when there's no .env.local — uses sane defaults for a self-bound dogfood repo
  WORKSPACE=${MINIONS_WORKSPACE:-$ROOT/.dev-workspace}
  MINIONS_TOKEN=${MINIONS_TOKEN:-devtoken} \
  MINIONS_PORT=$PORT \
  MINIONS_HOST=${MINIONS_HOST:-127.0.0.1} \
  MINIONS_WORKSPACE=$WORKSPACE \
  MINIONS_PROVIDER=${MINIONS_PROVIDER:-claude-code} \
  MINIONS_LOG_LEVEL=${MINIONS_LOG_LEVEL:-info} \
  MINIONS_CORS_ORIGINS=${MINIONS_CORS_ORIGINS:-'http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174'} \
  MINIONS_REPOS=${MINIONS_REPOS:-'[{"id":"self","label":"claude-minions","remote":"'"$ROOT"'","defaultBranch":"main"}]'} \
  setsid pnpm --filter @minions/engine run dev > "$LOG" 2>&1 < /dev/null &
  disown
fi

# Give it ~6s to bind
for i in 1 2 3 4 5 6; do
  if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "engine listening on :$PORT (log: $LOG)"
    exit 0
  fi
  sleep 1
done

echo "ERROR: engine failed to bind $PORT — see $LOG" >&2
tail -30 "$LOG" >&2
exit 1
