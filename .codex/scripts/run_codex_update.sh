#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/prei/dotfiles"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
SCRIPT_PATH="${PROJECT_ROOT}/.codex/scripts/codex_pattern_updater.py"
STATE_PATH="${PROJECT_ROOT}/.codex/automation_state.json"
CODEX_PATH="${PROJECT_ROOT}/.codex/AGENTS.md"
BRANCH="codex/autotune"
BASE_BRANCH="master"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found on PATH" >&2
  exit 1
fi

# Ensure common CLI tools (git, node-based binaries, etc.) are discoverable in cron.
export PATH="/home/prei/.nvm/versions/node/v20.14.0/bin:${PATH:-/usr/bin}"

cd "${PROJECT_ROOT}"

"${PYTHON_BIN}" "${SCRIPT_PATH}" \
  --branch "${BRANCH}" \
  --base-branch "${BASE_BRANCH}" \
  --state "${STATE_PATH}" \
  --codex "${CODEX_PATH}"
