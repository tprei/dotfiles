# Weekly/monthly limit reset messages for codex-usage-check

## Goal

`codex-usage-check --telegram` (systemd timer, every 5 min) currently maintains three pinned Telegram images. When a long-window limit (weekly or monthly, never the 5-hour windows) rolls over to a fresh window, send a one-off, notifying, good-looking Telegram photo message with the provider logo, the fresh free capacity, and the closed window's final usage. The `tools/.local/share/codex-usage/` modules are pure collectors; the feature belongs in `tools/.local/bin/codex-usage-check`, which owns Telegram delivery and `~/.config/codex-usage/state.json`.

## Constraints

- No fallbacks, no shims, no suppressions, no comment narration in code.
- Reuse existing helpers: `usable_reports`, `reset_datetime`, `to_percent`, `bar`, `fmt_reset`, `provider_display`, `plain_image_text`, `render_image`, `tg_upload`, `load_state`, `save_state`. Do not fork the ffmpeg boilerplate.
- Existing behavior of the three pinned images must not change (exit codes included).
- No new dependencies; stdlib only.
- 5h windows (and any window under 3.5 days) are never announced.

## Design

Detection is state-based: compare the previous run's stored per-limit observation with the current payload. A reset event requires both signals (fixed-cadence windows jump `resetsAt` forward and `usedFraction` drops):

1. `new resets_at_ms > old resets_at_ms + 60s`, and
2. `old_used - new_used >= RESET_DROP` (existing constant, 0.02).

Noise floor: the closed window must have ended at `>= 5%` used; unused windows resetting are non-events. First run (no stored watch) only records a baseline, never announces. If the Telegram send fails, the watch is not persisted so the next run retries.

### New constants (insert after `FORECAST_STATE_KEY`, line ~108)

```python
RESET_WATCH_STATE_KEY = "reset_watch"
RESET_FORWARD_TOLERANCE_MS = 60_000
RESET_WATCH_TTL_MS = 40 * 86_400_000
RESET_ANNOUNCE_MIN_USED = 0.05
WEEKLY_WINDOW_MS = 302_400_000
MONTHLY_WINDOW_MS = 1_728_000_000
```

### Files touched

- `tools/.local/bin/codex-usage-check` — all logic below.
- `tools/tests/test_codex_usage_tokens.py` — new test classes plus one patcher in `PublishImagesTests.setUp`.
- `README.md` — extend the `codex-usage-check` paragraph (one or two sentences).

### Step-by-step changes in `tools/.local/bin/codex-usage-check`

1. Constants above.

2. `tg_send_photo` gains an optional HTML caption (only call site adds it later; existing call sites unchanged):

```python
def tg_send_photo(config: dict, image: bytes, caption: str | None = None) -> int:
    fields: dict[str, object] = {"chat_id": config["chat_id"]}
    if caption is not None:
        fields["caption"] = caption
        fields["parse_mode"] = "HTML"
    payload = tg_upload(
        config["bot_token"],
        "sendPhoto",
        fields,
        "photo",
        "omp-usage.png",
        image,
    )
```

(rest of the function unchanged.)

3. New section inserted after `build_image` (before `token_display_name`, line ~1193). Full code:

```python
class WindowReset(TypedDict):
    provider: str
    kind: str
    label: str
    amount_text: str
    closed_used: float
    closed_at_ms: int
    resets_at_ms: int
    fresh_used: float


def long_window_kind(limit: dict) -> str | None:
    window = limit.get("window")
    window = window if isinstance(window, dict) else {}
    duration = window.get("durationMs")
    if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0:
        if duration < WEEKLY_WINDOW_MS:
            return None
        return "monthly" if duration >= MONTHLY_WINDOW_MS else "weekly"
    text = " ".join(
        part.casefold()
        for part in (window.get("id"), window.get("label"), limit.get("label"))
        if isinstance(part, str)
    )
    if "month" in text or "1mo" in text or "30d" in text:
        return "monthly"
    if "week" in text or "7 day" in text or "7d" in text:
        return "weekly"
    return None


def window_amount_text(amount: dict) -> str:
    unit = amount.get("unit")
    used = amount.get("used")
    limit = amount.get("limit")
    if unit in ("percent", None) or isinstance(used, bool) or isinstance(limit, bool):
        return ""
    if not isinstance(used, int) or not isinstance(limit, int):
        return ""
    return f"{used:,}/{limit:,} {unit}"


def tracked_window_limits(payload: dict, now_ms: int) -> dict[str, dict]:
    tracked: dict[str, dict] = {}
    for report in usable_reports(payload):
        provider = report["provider"]
        limits = report.get("limits")
        if not isinstance(limits, list):
            continue
        for index, limit in enumerate(limits):
            if not isinstance(limit, dict):
                continue
            kind = long_window_kind(limit)
            if kind is None:
                continue
            window = limit.get("window")
            window = window if isinstance(window, dict) else {}
            moment = reset_datetime(window.get("resetsAt"))
            amount = limit.get("amount")
            amount = amount if isinstance(amount, dict) else {}
            used_percent = to_percent(amount.get("usedFraction"))
            if moment is None or used_percent is None:
                continue
            limit_id = str(limit.get("id") or "limit")
            label = window.get("label") or limit.get("label")
            tracked[f"{provider}:{index}:{limit_id}"] = {
                "provider": provider,
                "kind": kind,
                "label": label.strip() if isinstance(label, str) and label.strip() else "long window",
                "amount_text": window_amount_text(amount),
                "resets_at_ms": int(moment.timestamp() * 1000),
                "used": used_percent / 100.0,
                "seen_at_ms": now_ms,
            }
    return tracked


def detect_window_resets(previous: dict, current: dict) -> list[WindowReset]:
    resets: list[WindowReset] = []
    for key, entry in current.items():
        old = previous.get(key)
        if not isinstance(old, dict):
            continue
        old_resets = old.get("resets_at_ms")
        old_used = old.get("used")
        if isinstance(old_resets, bool) or not isinstance(old_resets, int):
            continue
        if isinstance(old_used, bool) or not isinstance(old_used, (int, float)):
            continue
        if entry["resets_at_ms"] <= old_resets + RESET_FORWARD_TOLERANCE_MS:
            continue
        closed_used = float(old_used)
        if closed_used < RESET_ANNOUNCE_MIN_USED:
            continue
        if closed_used - entry["used"] < RESET_DROP:
            continue
        kind = old.get("kind")
        label = old.get("label")
        resets.append({
            "provider": entry["provider"],
            "kind": kind if isinstance(kind, str) and kind else entry["kind"],
            "label": label if isinstance(label, str) and label.strip() else entry["label"],
            "amount_text": old.get("amount_text") if isinstance(old.get("amount_text"), str) else "",
            "closed_used": closed_used,
            "closed_at_ms": old_resets,
            "resets_at_ms": entry["resets_at_ms"],
            "fresh_used": entry["used"],
        })
    resets.sort(key=lambda item: (item["provider"], item["label"]))
    return resets


def merged_watch(previous: dict, current: dict, now_ms: int) -> dict:
    merged: dict[str, dict] = {}
    for key, entry in previous.items():
        if not isinstance(entry, dict):
            continue
        seen_at = entry.get("seen_at_ms")
        if isinstance(seen_at, int) and not isinstance(seen_at, bool) and now_ms - seen_at >= RESET_WATCH_TTL_MS:
            continue
        merged[key] = entry
    merged.update(current)
    return merged


def persist_watch(merged: dict) -> bool:
    state = load_state()
    if state.get(RESET_WATCH_STATE_KEY) == merged:
        return True
    state[RESET_WATCH_STATE_KEY] = merged
    try:
        save_state(state)
    except OSError as error:
        print(f"codex-usage-check: failed to persist reset watch: {error}", file=sys.stderr)
        return False
    return True


def reset_caption(resets: list[WindowReset]) -> str:
    kinds = {reset["kind"] for reset in resets}
    if kinds == {"weekly"}:
        title = "Weekly limit reset"
    elif kinds == {"monthly"}:
        title = "Monthly limit reset"
    else:
        title = "Limit resets"
    lines = [f"🎉 <b>{title}</b>"]
    grouped: dict[str, list[WindowReset]] = {}
    for reset in resets:
        grouped.setdefault(reset["provider"], []).append(reset)
    for provider in sorted(grouped):
        lines.append("")
        lines.append(f"<b>{provider_display(provider)}</b>")
        for reset in grouped[provider]:
            usage = f" ({escape(reset['amount_text'])})" if reset["amount_text"] else ""
            lines.append(
                f"{escape(reset['label'])} · closed at <b>{reset['closed_used'] * 100:.1f}%</b> used{usage} · "
                f"fresh window resets <b>{escape(fmt_reset(reset['resets_at_ms']))}</b>"
            )
    return "\n".join(lines)


def reset_image_text(resets: list[WindowReset]) -> str:
    blocks = []
    for reset in resets:
        free_percent = 100.0 - reset["fresh_used"] * 100.0
        blocks.append(
            "\n".join(
                [
                    unescape(provider_display(reset["provider"])),
                    f"{reset['label']} · fresh window",
                    f"{bar(free_percent)} {free_percent:.0f}% free · resets {fmt_reset(reset['resets_at_ms'])}",
                    f"closed at {reset['closed_used'] * 100:.1f}% used · {fmt_reset(reset['closed_at_ms'])}",
                ]
            )
        )
    return "\n\n".join(blocks)


def build_reset_image(resets: list[WindowReset]) -> bytes:
    try:
        return render_image(plain_image_text(reset_image_text(resets)))
    except UsageError:
        raise
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        raise UsageError(f"failed to render reset image: {error}", 2) from error


def announce_window_resets(config: dict, payload: dict) -> int:
    now_ms = time.time_ns() // 1_000_000
    current = tracked_window_limits(payload, now_ms)
    watch = load_state().get(RESET_WATCH_STATE_KEY)
    watch = watch if isinstance(watch, dict) else {}
    resets = detect_window_resets(watch, current)
    merged = merged_watch(watch, current, now_ms)
    if resets:
        try:
            tg_send_photo(config, build_reset_image(resets), reset_caption(resets))
        except UsageError as error:
            print(f"codex-usage-check: failed to send limit reset message: {error}", file=sys.stderr)
            return 2
        except (OSError, TimeoutError, TelegramError) as error:
            print(f"codex-usage-check: failed to send limit reset message: {error}", file=sys.stderr)
            return 2
    if not persist_watch(merged):
        return 2
    return 0
```

Note: `urllib.error.HTTPError` subclasses `OSError`, so the catch above covers it.

Rationale for image-line shapes: `image_line_color` colors a line starting with `BAR_FILLED` green only when the `%` is not immediately followed by ` ·` (that path means an active limit row). `99% free · resets …` puts no `·` right after the percent, so the fresh-capacity bar renders green.

4. Hook into `publish_images` (after the forecast block, before the final code aggregation, line ~1879):

```python
    reset_code = 0
    if payload is not None:
        reset_code = announce_window_resets(config, payload)
    for code in (limits_code, token_code, forecast_code, reset_code):
```

(the existing `for code in (limits_code, token_code, forecast_code):` line is replaced by the tuple including `reset_code`; early `return 1` on code 1 stays.)

### Tests (`tools/tests/test_codex_usage_tokens.py`)

Add a payload/limit helper near other helpers, plus:

- `LongWindowKindTests` (pure):
  - `604800000` ms → `"weekly"`; `2592000000` → `"monthly"`.
  - `durationMs` `null` with window label `Monthly` → `"monthly"` (opencode-go case); null duration with no monthly/weekly text → `None`.
  - `18000000` (5h) and `86400000` (1 day) → `None`.
- `DetectWindowResetsTests` (pure):
  - forward jump + drop → one event with `closed_used` from the old entry and `fresh_used` from the new.
  - forward jump without drop (0.95 → 0.94) → `[]`.
  - drop without forward jump (same resetsAt) → `[]`.
  - drift within 60s tolerance → `[]`.
  - closed below 5% floor → `[]`.
  - unknown key → `[]`; result sorted by (provider, label).
- `ResetMessageTests` (pure): caption contains `Weekly limit reset`, provider display, `closed at <b>100.0%</b> used`, `fresh window resets`; image text contains `· fresh window`, `% free`, no `<b>`; monthly-only set titles `Monthly limit reset`; mixed titles `Limit resets`.
- `ResetAnnouncementTests` (patch `CODEX_STATE_PATH` to a temp dir like `ReporterTelegramStateTests`, mock `tg_send_photo`):
  - first run with a weekly limit: exit 0, no send, `state["reset_watch"]` populated with the current observation.
  - stored watch with `used: 1.0` and past `resets_at_ms`, payload with the same key at `usedFraction: 0.0` and `resetsAt` +7 days: exit 0, `tg_send_photo` called once, caption argument contains the provider, image argument is `bytes`, watch updated to the new `resets_at_ms`.
  - send raises `TelegramError`: exit 2, watch unchanged on disk; running announce again with the same payload sends again (retry).
  - below-floor rollover: exit 0, no send, watch still updated.
  - 5h-only payload: no send, empty watch.
  - stale entry older than 40 days absent from payload is pruned on save.
- `PublishImagesTests.setUp`: add `mock.patch.object(reporter, "announce_window_resets", return_value=0)` patcher (start/stop like the others) so tests stay hermetic, and assert in `test_publishes_every_image_in_order_with_independent_state_keys` that it was called once with the config and payload.

Run: `cd tools/tests && python3 -m unittest test_codex_usage_tokens` — all pass, zero failures.

### README

Append to the `codex-usage-check` paragraph (line ~158): when a weekly or monthly window rolls over and the closed window ended at ≥5% used, the same run also sends a one-off reset photo (provider logo, fresh free capacity, closed window's final usage) with an HTML caption; 5h windows are excluded, and the per-limit reset watch lives under `reset_watch` in the same state file.

## Verification

1. `cd tools/tests && python3 -m unittest test_codex_usage_tokens` → OK.
2. Smoke render (no Telegram): a short python snippet importing the reporter, building `WindowReset` dicts for two providers, writing `reset_image_text` output and `render_image(...)` PNG to `/tmp/reset-preview.png`, then read the PNG to confirm ffmpeg produced a valid image.
3. Live dry check: `codex-usage-check` JSON mode still works (exit 0).


## Post-review revisions

An adversarial review after implementation changed four details:

- Watch keys are `provider:report_index:limit_id` (account-scoped, matching `format_message`'s account enumeration), and a `limit_id` that appears in more than one report of the same provider is not tracked at all: the payload has no stable account identifier, so ambiguous ids are skipped rather than risked as fabricated announcements.
- `reset_caption` caps itself at 1024 characters (Telegram's caption limit) with a trailing `+N more` line, preventing a deterministic Telegram 400 that the retry path would re-trigger every run.
- `window_amount_text` accepts float amounts (`940.0` renders as `940`, `12.5` stays `12.5`).
- `tracked_window_limits` prefers the limit label over the window label (live payloads carry distinguishable limit labels like `Claude 7 Day (Fable)`), and `persist_watch` skips writing an empty `reset_watch` key when nothing is tracked.