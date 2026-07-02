#!/usr/bin/env bash
# Idempotent orchestrator restart for a dogfood loop.
#
# This is a TEMPLATE. Copy into your project and replace the placeholders
# (ORCHESTRATOR_PATTERN, START_CMD, PORT, ENV_FILE, etc.) with values that
# match your orchestrator. The structure — kill anything on the port, kill
# stray watch-mode processes, wait for socket free, relaunch under setsid,
# wait for bind — applies to most node/python/go orchestrators.
#
# Run from the repo root: ./scripts/restart-engine.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd 2>/dev/null || echo "$(pwd)")"
cd "$ROOT"

# --- Configure these for your project ---------------------------------------
PORT="${ORCH_PORT:-8787}"                                # orchestrator HTTP port
ORCHESTRATOR_PATTERN='tsx watch.*<your-orch-pkg>'         # pgrep pattern for stray watchers
ENV_FILE="${ENV_FILE:-.env.local}"                        # optional dotenv
LOG="${ORCH_LOG:-/tmp/orchestrator.log}"
START_CMD_PRIMARY="bin/engine.sh"                         # preferred start script (sources $ENV_FILE)
START_CMD_FALLBACK='pnpm --filter @your-org/orchestrator run dev'   # used when $ENV_FILE missing
# ----------------------------------------------------------------------------

# Kill any existing orchestrator listening on PORT, plus any stray watch-mode procs
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  PIDS=$(ss -tlnp 2>/dev/null | grep ":$PORT " | sed -E 's/.*pid=([0-9]+).*/\1/' | sort -u)
  for p in $PIDS; do
    kill -9 "$p" 2>/dev/null || true
  done
fi
pkill -9 -f "$ORCHESTRATOR_PATTERN" 2>/dev/null || true
sleep 3

if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
  echo "ERROR: port $PORT still bound after pkill — investigate" >&2
  ss -tlnp 2>/dev/null | grep ":$PORT " >&2
  exit 1
fi

if [ -x "$START_CMD_PRIMARY" ] && [ -f "$ENV_FILE" ]; then
  setsid "$START_CMD_PRIMARY" > "$LOG" 2>&1 < /dev/null &
  disown
else
  # Fallback when there's no $ENV_FILE — set sane defaults inline
  setsid sh -c "$START_CMD_FALLBACK" > "$LOG" 2>&1 < /dev/null &
  disown
fi

# Give it ~6s to bind
for i in 1 2 3 4 5 6; do
  if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "orchestrator listening on :$PORT (log: $LOG)"
    exit 0
  fi
  sleep 1
done

echo "ERROR: orchestrator failed to bind $PORT — see $LOG" >&2
tail -30 "$LOG" >&2
exit 1
