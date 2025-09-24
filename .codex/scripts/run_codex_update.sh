#!/usr/bin/env bash
set -euo pipefail

CODEX_BIN="/home/prei/.nvm/versions/node/v20.14.0/bin/codex"

"${CODEX_BIN}" -a on-request exec \
  --sandbox workspace-write \
  --cd /home/prei/dotfiles \
  "Run python3 .codex/scripts/codex_pattern_updater.py --branch codex/autotune --base-branch master --state .codex/automation_state.json --codex .codex/AGENTS.md and exit when finished."
