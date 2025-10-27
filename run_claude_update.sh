#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/prei/dotfiles"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
SCRIPT_PATH="${PROJECT_ROOT}/claude_pattern_updater.py"
STATE_PATH="${PROJECT_ROOT}/.claude/automation_state.json"
CLAUDE_GUIDANCE_PATH="${PROJECT_ROOT}/.claude/CLAUDE.md"
CLAUDE_PROJECTS_PATH="${HOME}/.claude/projects"
CLAUDE_HISTORY_PATH="${HOME}/.claude/history.jsonl"
BRANCH="claude/pattern-updates"
BASE_BRANCH="master"

# Load environment variables from .env file for OpenAI API access
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  echo "Loading environment from .env file..."
  # Export each line from .env that's not a comment or empty
  while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue

    # Export the variable
    export "$line"
  done < "${PROJECT_ROOT}/.env"
  echo "Environment loaded successfully."
else
  echo "Warning: .env file not found at ${PROJECT_ROOT}/.env"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found on PATH" >&2
  exit 1
fi

# Ensure common CLI tools (git, node-based binaries, etc.) are discoverable in cron.
NVM_DIR="${HOME}/.nvm"
if [[ -s "${NVM_DIR}/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  source "${NVM_DIR}/nvm.sh"
  nvm use --silent v20.14.0 >/dev/null 2>&1 || true
fi

export PATH="/home/prei/.nvm/versions/node/v20.14.0/bin:${PATH:-/usr/bin}"

if ! command -v node >/dev/null 2>&1; then
  echo "node binary not found on PATH; Claude API calls may fail" >&2
fi

cd "${PROJECT_ROOT}"

"${PYTHON_BIN}" "${SCRIPT_PATH}" \
  --agent claude \
  --branch "${BRANCH}" \
  --base-branch "${BASE_BRANCH}" \
  --claude-state "${STATE_PATH}" \
  --claude-output "${CLAUDE_GUIDANCE_PATH}" \
  --claude-projects "${CLAUDE_PROJECTS_PATH}" \
  --claude-history "${CLAUDE_HISTORY_PATH}"