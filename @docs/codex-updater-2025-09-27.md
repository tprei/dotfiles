# Codex Updater Fixes — 2025-09-27T09:58:40Z

## What changed
- Track per-session timestamps in `.codex/scripts/codex_pattern_updater.py` so new messages inside existing sessions increment guideline counts.
- Persist `session_progress` in `.codex/automation_state.json` and migrate older state files automatically.
- Adjust PR summaries/commit messages to call out both new and updated sessions.
- Source nvm inside `.codex/scripts/run_codex_update.sh` so cron can launch the Node-based `codex` CLI.

## How to verify
- Append a new entry to an existing `session_id` in `~/.codex/history.jsonl`.
- Run `.codex/scripts/run_codex_update.sh --dry-run` (or let cron execute on the hour).
- Confirm the console log reports the session under “updated” and that `~/.codex/logs/pattern-updater.log` shows refreshed counts without node errors.
