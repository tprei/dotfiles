# OMP usage Telegram report

## Goal

Add an OMP usage reporter that behaves like `tools/.local/bin/claude-usage-check`: it prints machine-readable usage for every provider OMP can report, refreshes one pinned Telegram message as a readable PNG photo, and runs from a five-minute systemd user timer.

## Approach

Use the installed `omp usage --json --redact` command as the provider integration boundary. OMP already owns OAuth refresh, account selection, provider usage requests, account identity handling, and provider-specific windows. Do not install or invoke the standalone `codex` CLI, and do not duplicate provider token handling in this repository.

The new reporter reuses the existing Telegram bot token and chat ID from `~/.config/claude-usage/config`, so the OMP and Claude reports stay in the same conversation. It keeps only its own pinned-message state under `~/.config/codex-usage/state.json`, allowing the Claude and OMP reports to coexist as separate messages. The service sets the absolute OMP path through `OMP_BIN` because systemd user services do not inherit the interactive Bun path. Telegram mode renders the report with the system ffmpeg into a PNG photo that replaces the message in place; the service sets `FFMPEG_BIN=/usr/bin/ffmpeg`, and a missing or failing ffmpeg is a transient exit-code-2 failure, never a text fallback.

## Files and exact changes

### `tools/.local/bin/codex-usage-check`

Create an executable Python 3 script with these entry points:

- `run_omp_usage() -> dict`: execute `[OMP_BIN, "usage", "--json", "--redact"]` with captured text output and a 60-second timeout; reject non-zero exit status, invalid JSON, non-object output, or an absent/non-list `reports` field with a user-facing `UsageError`. Keep every report returned by OMP and require at least one report with a provider value. If no report exists, raise `UsageError` that tells the user to authenticate a provider with OMP. Convert `FileNotFoundError` and `TimeoutExpired` into explicit tool errors without shell execution.
- `format_message(payload: dict) -> str`: render `<b>OMP usage</b>` with the UTC date, group reports by provider, render an account block for each report, include each optional plan line, every report limit, a ten-cell Unicode bar, percentage, reset estimate, and status marker. Use `limits[].amount.usedFraction`, `limits[].label` or `limits[].window.label`, `limits[].window.resetsAt`, and `limits[].status`. Clamp percentages to 0–100, show `?` for missing usage, and HTML-escape dynamic provider, account, plan, label, and error text before sending them to Telegram. Render every provider OMP returns, including OpenAI Codex, Anthropic, Google, OpenCode, and ZAI when authenticated. Append missing window labels such as `5 Hour`, `Weekly`, or `Monthly`, and usage units such as `requests` or `tokens`, so similarly named provider meters remain distinct. Render each limit row in a fixed-width HTML code span with a padded label column, keeping reset estimates aligned without relying on tab stops.
- `fmt_reset(value: object) -> str`, `fmt_reset_estimate(value: object) -> str`, and `bar(percent: float | None) -> str`: format the image header's update time and reset estimates in UTC, using relative labels such as `~in 5 minutes` for valid future resets, `~now` for elapsed resets, and no label for unknown timestamps; render the same filled/empty bar style as the Claude reporter.
- `plain_image_text(html_text: str) -> str` and `image_line_color(line: str) -> str`: strip the formatted HTML report into fixed-width plain image text that keeps the Unicode bars, percentages, reset times, and padded label columns, and classify healthy, warning, exhausted, unknown, and non-row lines for image colors.
- `render_image(text: str) -> bytes`: render the plain text to PNG bytes by running the ffmpeg binary resolved from `FFMPEG_BIN` (default `ffmpeg` on `PATH`; the service pins `/usr/bin/ffmpeg`) with one drawtext filter per non-empty line, each fetched provider logo SVG centered inside an inset logo slot beside its known provider heading, colored status rows, and the fixed-width font resolved from `OMP_USAGE_FONT` (default `/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf`); raise exit code 1 when ffmpeg is missing and exit code 2 when rendering times out or ffmpeg exits non-zero.
- `build_image() -> tuple[bytes, int]`: fetch usage, sort each report's limits by earliest valid reset time with unknown resets last, add the OMP `generatedAt` time to the image header, and return the rendered PNG bytes with the exit code for Telegram mode, rendering the warning image when the usage fetch fails transiently.
- `load_config() -> dict | None`, `load_state() -> dict`, and `save_state(state: dict) -> None`: read the existing Claude Telegram config at `~/.config/claude-usage/config`, store only the OMP message ID in `~/.config/codex-usage/state.json`, enforce directory mode `0700` and state file mode `0600`, and use atomic replacement for state writes. Do not create or migrate a second Telegram config.
- `tg_call(bot_token: str, method: str, params: dict) -> dict`, `tg_upload(bot_token: str, method: str, fields: dict[str, object], file_field: str, filename: str, media: bytes) -> dict`, `tg_send_photo(config: dict, image: bytes) -> int`, `tg_edit_photo(config: dict, message_id: int, image: bytes) -> None`, `tg_pin(cfg: dict, message_id: int) -> None`, and `update_pinned(cfg: dict, image: bytes) -> bool`: keep `tg_call` for the JSON methods (`getMe`, `pinChatMessage`) and post every photo request as `multipart/form-data`. `tg_upload` is the shared multipart poster, `tg_send_photo` sends the PNG via `sendPhoto`, and `tg_edit_photo` updates the saved message via `editMessageMedia` whose media JSON must reference the upload as `attach://photo`. Edit the saved message in place and re-pin it after a successful edit; when the stored `message_id` still points at an old text message, Telegram rejects the edit with HTTP 400, so send a fresh photo message, persist the new ID before pinning, then pin it. Return `False` for transport failures.
- `setup_telegram() -> int`: validate the existing Claude Telegram config with `getMe` and refresh an OMP confirmation message in the same chat. If the Claude config is absent, tell the user to run `claude-usage-check --setup-telegram`; do not ask for a second token or chat ID. Return `1` for missing/invalid configuration and `2` for transient Telegram failures.
- `main(argv: list[str]) -> int`: support `--setup-telegram`, `--telegram`, and the no-flag JSON mode. Return `0` on success, `1` on auth/config/tool failure, and `2` on transient OMP, network, rendering, formatting, or Telegram failure. In Telegram mode, replace a failed usage fetch with a pinned warning image instead of failing silently.

Use only the Python standard library plus the system ffmpeg binary for image rendering. Invoke OMP and ffmpeg without `shell=True`, never log bearer tokens, and do not add a fallback OpenAI endpoint, standalone Codex auth implementation, or text-message fallback in Telegram mode.

### `tools/.local/share/codex-usage/logos/`

Bundle the fetched provider logo SVGs used by the renderer:

- `openai.svg`: OpenAI blossom mark.
- `google.svg`: Google G mark.
- `opencode.svg`: OpenCode mark.
- `zai.svg`: Z.ai mark.
- `anthropic.svg`: Claude mark from Anthropic.

Resolve the directory from the script's repository path so Telegram updates never depend on a live logo download.

### `tools/.config/systemd/user/codex-usage-report.service`

Create a oneshot user service matching the Claude service's restart policy:

- Description identifies the OMP provider usage pinned report.
- `ExecStart=/home/prei/.local/bin/codex-usage-check --telegram`.
- Set `OMP_BIN=/home/prei/.bun/bin/omp` and a PATH containing `/home/prei/.bun/bin`, `/home/prei/.local/bin`, `/usr/local/bin`, `/usr/bin`, and `/bin`.
- Set `FFMPEG_BIN=/usr/bin/ffmpeg` so Telegram mode renders the PNG with the system ffmpeg.
- Use `Restart=on-failure`, `RestartPreventExitStatus=1`, and `RestartSec=60`.

### `tools/.config/systemd/user/codex-usage-report.timer`

Create a timer matching the Claude cadence: `OnBootSec=1min`, `OnUnitActiveSec=5min`, `RandomizedDelaySec=20s`, and `WantedBy=timers.target`.

### `README.md`

Extend the Tools section with the OMP-backed provider reporter, its reuse of `~/.config/claude-usage/config`, separate `~/.config/codex-usage/state.json`, the timer cadence, and the `systemctl --user daemon-reload` plus `enable --now codex-usage-report.timer` commands. State that it reports every provider OMP can report, including OpenAI Codex, when that provider is authenticated, and that its limit rows identify the provider window and unit. State that the existing Claude Telegram setup supplies the same bot and conversation, so no second BotFather setup is needed. State that the current machine already has OMP's Codex OAuth account, so installing the standalone `codex` command is not required; users without an OMP Codex account must log in through OMP first. State that Telegram mode renders the report as a readable PNG image with the system ffmpeg — required for Telegram mode — and edits it as a Telegram photo in place, leaving the Claude bot/chat config and the separate OMP state file unchanged.

## Verification

After implementation, run the reporter without Telegram and confirm it emits valid JSON containing one or more OMP usage reports, including the `openai-codex` report on this machine, and usage limits. Run `python3 -m py_compile tools/.local/bin/codex-usage-check`, inspect both unit files with `systemd-analyze verify` if available, and perform a dry-run systemd reload/status check without enabling unrelated services. Do not run Telegram setup or send a message unless credentials are already configured.

## Non-goals

- No standalone `codex` installation.
- No direct OpenAI token refresh or undocumented endpoint code in dotfiles.
- No shared-state migration or changes to the existing Claude reporter.
- No new compatibility aliases, suppressed diagnostics, or advisory validation gates.
- No text-message fallback in Telegram mode; ffmpeg rendering failures are transient exit-code-2 errors, while a missing ffmpeg binary is an exit-code-1 tool failure.
