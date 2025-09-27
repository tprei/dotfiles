# Codex Pattern Updater Notes

- Last updated: 2025-09-27T11:08:34Z
- Author: Codex assistant (session)

## LLM backend
- Discovery now defaults to a direct Anthropic API call (`CODEX_PATTERN_PROVIDER=claude`). Export `ANTHROPIC_API_KEY` (or `CLAUDE_API_KEY`) in the shell before running; the script will short-circuit with a hint if no key is available.
- Override the model with `CODEX_PATTERN_CLAUDE_MODEL` (default: `claude-sonnet-4-20250514`). Optional knobs: `CODEX_PATTERN_CLAUDE_MAX_TOKENS`, `CODEX_PATTERN_CLAUDE_TEMPERATURE`, and `CODEX_PATTERN_CLAUDE_TOP_P`.
- To temporarily fall back to the Codex/OpenAI path, export `CODEX_PATTERN_PROVIDER=codex`. Both providers require outbound network access.

## Running the updater
1. Export the Anthropic key (e.g. `export ANTHROPIC_API_KEY=...`).
2. Run `scripts/codex_pattern_updater.py --dry-run`. The script prints the session IDs it considered, then posts the summarization prompt to Claude via HTTPS.
3. Remove `--dry-run` to update `AGENTS.md` and `automation_state.json` once you’re satisfied with the preview.

## Diagnostics
- If you see `LLM discovery skipped: ANTHROPIC_API_KEY (or CLAUDE_API_KEY) not set`, make sure the key is exported in the same shell and that your account has API access (Claude Code desktop subscriptions still require API credit for headless calls).
- For malformed JSON or other Claude errors, the script prints a truncated snippet of the API response to help you debug the prompt output. Messages about credit or quota come directly from Anthropic.
- The dry-run output now always includes the list of new and updated session IDs, plus either `Discovered dynamic patterns: ...` or `No dynamic patterns discovered in latest sessions.`
- `AGENTS.md` size limits continue to be irrelevant—the file is still well below the markdown ceiling.
