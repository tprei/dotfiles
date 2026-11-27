from __future__ import annotations

import base64
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from token_usage import DAY_MS, DayTotal, ProviderTotal, TokenSnapshot


@dataclass(frozen=True, slots=True)
class Pace:
    verdict: str
    projected_percent: float | None
    rate: str
    detail: str
    exhaust_in_ms: int | None = None
    spark: tuple[float | None, ...] = ()


@dataclass(frozen=True, slots=True)
class QuotaWindow:
    label: str
    used_percent: float | None
    reset_ms: int | None
    status: str | None
    pace: Pace | None
    window_ms: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderQuota:
    provider: str
    account: str
    plan: str
    windows: list[QuotaWindow]


@dataclass(frozen=True, slots=True)
class Dashboard:
    now_ms: int
    quota_updated_ms: int | None
    quotas: list[ProviderQuota]
    quota_issue: str | None
    tokens: TokenSnapshot | None
    history_sources: list[str]
    history_partial: bool
    recent: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class ResetEvent:
    provider: str
    label: str
    kind: str
    closed_used_percent: float
    closed_at_ms: int
    fresh_used_percent: float
    resets_at_ms: int
    amount_text: str


@dataclass(frozen=True, slots=True)
class _Run:
    text: str
    color: str
    weight: int = 500
    size: int | None = None


@dataclass(frozen=True, slots=True)
class _Chip:
    text: str
    tone: str
    icon: str
    note: str


_WIDTH = 1600
_MARGIN = 56
_RIGHT = _WIDTH - _MARGIN
_PAD = 32
_GAP = 24
_SECTION_GAP = 32
_RADIUS = 24

_CARD_TOP = 84
_ROW_HEIGHT = 64
_BAR_HEIGHT = 12
_PACE_WIDTH = 210
_USED_INSET = 232
_GAUGE_INSET = 338
_WARM_PERCENT = 75.0
_BURNING_PERCENT = 90.0
_HOT_TOKEN_SHARE = 0.4

_TILES_WIDTH = 944
_LEGEND_GAP = 40
_TILE_HEIGHT = 84
_CHART_HEIGHT = 228
_PILL_HEIGHT = 44
_PILL_GAP = 10

_FORECAST_ROW = 104
_COMPACT_ROW = 56
_SPARK_OFFSET = 330
_SPARK_WIDTH = 460
_SPARK_HEIGHT = 72
_SPARK_FUTURE = 64
_NUMBERS_OFFSET = 830

_RESET_WIDTH = 1200
_RESET_CARD = 184
_RING_RADIUS = 54

_TITLE = 30
_HEAD = 22
_BODY = 22
_SMALL = 18
_TINY = 17
_MICRO = 16

_UI_FONT = "Bricolage Grotesque, DejaVu Sans, sans-serif"
_MONO_FONT = "JetBrains Mono, DejaVu Sans Mono, monospace"

_INK = "#0A0F1F"
_PANEL = "#121A2E"
_TRACK = "#232E47"
_WHITE = "#F5F7FF"
_MUTED = "#B3BDD6"
_CORAL = "#FF8A8F"
_AMBER = "#FFC75F"
_MINT = "#7EF0CC"
_PERIWINKLE = "#AEB9FF"
_VIOLET = "#A78BFA"
_CYAN = "#67E8F9"
_PINK = "#F9A8D4"
_SLATE = "#8394BC"
_FLAME_RED = "#EF4444"
_FLAME_ORANGE = "#FF8A3D"
_FLAME_YELLOW = "#FDE047"
_RAINBOW = ("#F87171", "#FB923C", "#FACC15", "#4ADE80", "#60A5FA", "#A78BFA")

_PROVIDER_STYLE = {
    "openai-codex": ("OpenAI Codex", "#ECECEC"),
    "google-antigravity": ("Google Antigravity", "#3186FF"),
    "opencode-go": ("OpenCode Go", "#AEAEAE"),
    "zai": ("ZAI", "#858BAC"),
    "anthropic": ("Anthropic", "#D97757"),
    "openai": ("OpenAI", "#ECECEC"),
    "openrouter": ("OpenRouter", "#22D3EE"),
}
_PROVIDER_ALIASES = {"antigravity-cli": "google-antigravity"}
_LOGO_DIR = Path(__file__).parent / "logos"
_LOGOS = {
    "openai-codex": ("openai.svg", True),
    "openai": ("openai.svg", True),
    "anthropic": ("anthropic.svg", False),
    "zai": ("zai.svg", False),
    "google-antigravity": ("google.svg", False),
    "opencode-go": ("opencode.svg", True),
}
_CHIPS = {
    "EXHAUSTED": ("Exhausted", _CORAL, "lock"),
    "RUN OUT": ("Runs out", _CORAL, "alert"),
    "GATED": ("Gated", _AMBER, "lock"),
    "HOT": ("Hot", _AMBER, "bolt"),
    "WARNING": ("Near limit", _AMBER, "bolt"),
    "ON PACE": ("On pace", _PERIWINKLE, "check"),
    "SPARE": ("Spare", _MINT, "leaf"),
}
_ALERTS = {
    "EXHAUSTED": "Exhausted",
    "GATED": "Capped by a longer window",
    "HOT": "Running hot",
    "WARNING": "Near limit",
}
_RISK_ORDER = {"EXHAUSTED": 0, "RUN OUT": 1, "GATED": 2, "HOT": 3, "WARNING": 4}
_FLAME_PATH = (
    "M12 2.5c.5 3 2.3 4.6 3.9 6.3 1.6 1.7 3.1 3.6 3.1 6.2a7 7 0 0 1-14 0c0-2.9 1.5-4.9 3.1-6.2"
    ".2 1.9.9 3.2 2.1 3.8-.4-3.4.3-7 1.8-10.1z"
)
_ICONS = {
    "clock": ('<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3 2"/>', True),
    "bolt": ('<path d="M13.5 2 4.5 13.6h6.3L9.6 22l9.4-11.9h-6.4z"/>', False),
    "lock": ('<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3"/>', True),
    "check": ('<path d="M5 12.5l4.5 4.5L19 7.5"/>', True),
    "leaf": ('<path d="M5.5 18.5C4.5 10.5 10 4.8 19.5 4.5c.3 9.6-5.4 14.9-14 14z"/><path d="M5.5 18.5 13 11"/>', True),
    "alert": ('<path d="M12 3.8 2.8 19.5h18.4z"/><path d="M12 9.8v4.4M12 16.9v.1"/>', True),
    "chart": ('<path d="M5 19.5v-6M10 19.5V9M15 19.5v-4.5M20 19.5V5"/>', True),
    "arrow": ('<path d="M4 12h15M13 6l6 6-6 6"/>', True),
    "refresh": ('<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4v4.5H15"/>', True),
    "calendar": ('<rect x="4" y="5.5" width="16" height="15" rx="2.5"/><path d="M4 10.5h16M8.5 3.5v4M15.5 3.5v4"/>', True),
    "spark": (
        '<path d="M12 1.5c.9 5.6 4.9 9.6 10.5 10.5-5.6.9-9.6 4.9-10.5 10.5-.9-5.6-4.9-9.6-10.5-10.5'
        ' 5.6-.9 9.6-4.9 10.5-10.5z"/>',
        False,
    ),
}
_ADVANCE_REGULAR = (
    225, 242, 312, 595, 592, 928, 712, 172, 248, 247, 407, 470, 155, 320, 200, 257, 622, 288, 560,
    585, 597, 572, 613, 502, 622, 613, 193, 182, 440, 480, 440, 417, 910, 655, 622, 645, 647, 560,
    538, 670, 662, 237, 315, 625, 475, 838, 700, 683, 593, 695, 620, 610, 548, 665, 643, 945, 625,
    595, 562, 293, 335, 287, 528, 583, 283, 537, 580, 537, 582, 547, 365, 565, 565, 223, 248, 528,
    223, 865, 565, 578, 580, 580, 380, 518, 365, 560, 545, 813, 530, 550, 483, 300, 222, 298, 495,
)
_ADVANCE_BOLD = (
    215, 270, 353, 613, 602, 953, 718, 188, 268, 268, 443, 477, 185, 328, 232, 270, 625, 317, 575,
    597, 618, 582, 618, 517, 628, 622, 233, 218, 462, 488, 462, 417, 947, 678, 637, 650, 653, 573,
    545, 678, 672, 258, 333, 645, 478, 865, 723, 687, 608, 698, 638, 618, 562, 672, 658, 965, 655,
    620, 570, 303, 350, 302, 545, 550, 283, 555, 598, 547, 598, 555, 385, 572, 587, 247, 260, 555,
    245, 892, 587, 583, 598, 598, 407, 528, 380, 580, 558, 837, 557, 563, 503, 302, 235, 302, 502,
)
_MONO_ADVANCE = 0.6
_STALE_MS = 5 * 60_000
_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_LONG_DASH = re.compile(r"\s*[–—]\s*")
_PERIOD = re.compile(r"(\d+)\s*(hours?|days?|minutes?)", re.IGNORECASE)
_UNIT_SUFFIX = re.compile(r"\s*\((?:tokens|requests|credits)\)\s*$", re.IGNORECASE)
_UNIT_IN_PARENS = re.compile(r",\s*(?:tokens|requests|credits)(?=\))", re.IGNORECASE)


def provider_name(provider: str) -> str:
    key = _PROVIDER_ALIASES.get(provider, provider)
    if key in _PROVIDER_STYLE:
        return _PROVIDER_STYLE[key][0]
    words = key.replace("-", " ").replace("_", " ").split()
    return " ".join(word[:1].upper() + word[1:] for word in words) or provider


def _provider_color(provider: str) -> str:
    key = _PROVIDER_ALIASES.get(provider, provider)
    if key in _PROVIDER_STYLE:
        return _PROVIDER_STYLE[key][1]
    return _SLATE


@cache
def _logo(provider: str) -> tuple[str, bool] | None:
    spec = _LOGOS.get(_PROVIDER_ALIASES.get(provider, provider))
    if spec is None:
        return None
    filename, mono = spec
    encoded = base64.b64encode((_LOGO_DIR / filename).read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}", mono


def _mix(color: str, other: str, amount: float) -> str:
    first = int(color[1:], 16)
    second = int(other[1:], 16)
    channels = []
    for shift in (16, 8, 0):
        a = (first >> shift) & 0xFF
        b = (second >> shift) & 0xFF
        channels.append(round(a + (b - a) * amount))
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _copy(value: str) -> str:
    return " ".join(_LONG_DASH.sub(" · ", _INVALID_XML.sub("", value)).split())


def _advance(char: str, weight: int) -> float:
    code = ord(char)
    if 32 <= code < 127:
        table = _ADVANCE_BOLD if weight >= 600 else _ADVANCE_REGULAR
        return table[code - 32] / 1000
    if char == "·":
        return 0.228 if weight >= 600 else 0.185
    if char == "…":
        return 0.737 if weight >= 600 else 0.667
    if unicodedata.combining(char):
        return 0.0
    return 1.0


def _width(value: str, size: int, weight: int = 500, *, mono: bool = False) -> float:
    text = _copy(value)
    if mono:
        return len(text) * _MONO_ADVANCE * size
    return sum(_advance(char, weight) for char in text) * size


def _fit(value: str, size: int, width: float, weight: int = 500) -> str:
    text = _copy(value)
    if _width(text, size, weight) <= width:
        return text
    limit = width / size - _advance("…", weight)
    kept = ""
    used = 0.0
    for char in text:
        used += _advance(char, weight)
        if used > limit:
            break
        kept += char
    return kept.rstrip(" ·") + "…"


class _Svg:
    def __init__(self) -> None:
        self.defs: list[str] = []
        self.backdrop: list[str] = []
        self.parts: list[str] = []
        self._ids = 0
        self._rainbow = False

    def _id(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}{self._ids}"

    def clip(self, x: float, y: float, width: float, height: float, radius: float) -> str:
        clip_id = self._id("c")
        self.defs.append(
            f'<clipPath id="{clip_id}"><rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" rx="{radius:g}"/></clipPath>'
        )
        return clip_id

    def raw(self, markup: str) -> None:
        self.parts.append(markup)

    def text(
        self,
        x: float,
        y: float,
        value: str,
        size: int,
        color: str = _WHITE,
        *,
        weight: int = 500,
        anchor: str = "start",
        mono: bool = False,
    ) -> None:
        family = f' font-family="{_MONO_FONT}"' if mono else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}"{family} font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{escape(_copy(value))}</text>'
        )

    def runs(self, x: float, y: float, runs: list[_Run], size: int, *, gap: int = 10, anchor: str = "start") -> None:
        spans = []
        for index, run in enumerate(runs):
            offset = f' dx="{gap}"' if index else ""
            run_size = f' font-size="{run.size}"' if run.size else ""
            spans.append(
                f'<tspan{offset}{run_size} fill="{run.color}" font-weight="{run.weight}">{escape(_copy(run.text))}</tspan>'
            )
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}">{"".join(spans)}</text>'
        )

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: str,
        radius: float = 0,
        *,
        opacity: float = 1.0,
        stroke: str | None = None,
        stroke_opacity: float = 1.0,
        stroke_width: float = 1.5,
    ) -> None:
        extra = f' fill-opacity="{opacity:g}"' if opacity != 1.0 else ""
        if stroke is not None:
            extra += f' stroke="{stroke}" stroke-opacity="{stroke_opacity:g}" stroke-width="{stroke_width:g}"'
        self.parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" rx="{radius:g}" fill="{fill}"{extra}/>'
        )

    def circle(
        self,
        x: float,
        y: float,
        radius: float,
        fill: str,
        *,
        opacity: float = 1.0,
        stroke: str | None = None,
        stroke_width: float = 1.5,
    ) -> None:
        extra = f' fill-opacity="{opacity:g}"' if opacity != 1.0 else ""
        if stroke is not None:
            extra += f' stroke="{stroke}" stroke-width="{stroke_width:g}"'
        self.parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:g}" fill="{fill}"{extra}/>')

    def rule(self, x1: float, y: float, x2: float, color: str, opacity: float, *, dashed: bool = False) -> None:
        dash = ' stroke-dasharray="2 7" stroke-linecap="round"' if dashed else ""
        self.parts.append(
            f'<path d="M{x1:.2f} {y:.2f}H{x2:.2f}" stroke="{color}" stroke-opacity="{opacity:g}" stroke-width="1.5"{dash}/>'
        )

    def icon(self, name: str, x: float, y: float, size: float, color: str) -> None:
        markup, stroked = _ICONS[name]
        paint = (
            f'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'
            if stroked
            else f'fill="{color}"'
        )
        self.parts.append(f'<g transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})" {paint}>{markup}</g>')

    def badge(self, x: float, y: float, provider: str | None, *, icon: str | None = None, color: str = _SLATE) -> None:
        center_x = x + 22
        center_y = y + 22
        self.circle(center_x, center_y, 22, color, opacity=0.16, stroke=_mix(color, _PANEL, 0.45))
        if icon is not None:
            self.icon(icon, center_x - 12, center_y - 12, 24, color)
            return
        logo = _logo(provider) if provider is not None else None
        if logo is None:
            self.circle(center_x, center_y, 7, color)
            return
        href, mono = logo
        tint = ' filter="url(#mono)"' if mono else ""
        self.parts.append(
            f'<image x="{center_x - 13:.1f}" y="{center_y - 13:.1f}" width="26" height="26" href="{href}"{tint}/>'
        )

    def logo_mark(self, x: float, y: float, size: float, provider: str) -> None:
        logo = _logo(provider)
        if logo is None:
            self.circle(x + size / 2, y + size / 2, 7, _provider_color(provider))
            return
        href, mono = logo
        tint = ' filter="url(#mono)"' if mono else ""
        self.parts.append(f'<image x="{x:.1f}" y="{y:.1f}" width="{size:g}" height="{size:g}" href="{href}"{tint}/>')

    def flame(self, x: float, y: float, size: float) -> None:
        inner = "translate(12 22) scale({scale}) translate(-12 -22)"
        self.parts.append(
            f'<g transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})">'
            f'<path d="{_FLAME_PATH}" fill="{_FLAME_RED}"/>'
            f'<path d="{_FLAME_PATH}" fill="{_FLAME_ORANGE}" transform="{inner.format(scale=0.7)}"/>'
            f'<path d="{_FLAME_PATH}" fill="{_FLAME_YELLOW}" transform="{inner.format(scale=0.4)}"/>'
            "</g>"
        )

    def rainbow_stroke(self) -> str:
        if not self._rainbow:
            stops = "".join(
                f'<stop offset="{index / (len(_RAINBOW) - 1):g}" stop-color="{color}"/>'
                for index, color in enumerate(_RAINBOW)
            )
            self.defs.append(f'<linearGradient id="opportunity" x2="100%" y2="100%">{stops}</linearGradient>')
            self._rainbow = True
        return "url(#opportunity)"

    def rainbow_outline(self, x: float, y: float, width: float, height: float, radius: float, opacity: float) -> None:
        self.rect(x, y, width, height, "none", radius, stroke=self.rainbow_stroke(), stroke_opacity=opacity, stroke_width=2)

    def card(self, x: float, y: float, width: float, height: float, accent: str, *, rainbow: bool = False) -> None:
        if rainbow:
            border = self.rainbow_stroke()
            opacity = 0.9
            stroke_width = 2.5
        else:
            border = accent
            opacity = 0.42
            stroke_width = 1.5
        self.backdrop.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{_RADIUS}" fill="{_PANEL}"'
            f' stroke="{border}" stroke-opacity="{opacity:g}" stroke-width="{stroke_width:g}"/>'
        )

    def finish(self, height: int, *, width: int = _WIDTH, title: str, desc: str) -> bytes:
        height += height % 2
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f"<title>{escape(title)}</title><desc>{escape(desc)}</desc>"
            '<defs>'
            '<filter id="mono" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
            'values="0 0 0 0 .96 0 0 0 0 .97 0 0 0 0 1 0 0 0 1 0"/></filter>'
            + "".join(self.defs)
            + "</defs>"
            f'<rect width="100%" height="100%" fill="{_INK}"/>'
            + "".join(self.backdrop)
            + f'<g font-family="{_UI_FONT}">'
            + "".join(self.parts)
            + "</g></svg>"
        ).encode("utf-8")


def _utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


def _date(ms: int) -> str:
    moment = _utc(ms)
    return f"{moment:%b} {moment.day}"


def _stamp(ms: int) -> str:
    return f"{_date(ms)}, {_utc(ms):%H:%M} UTC"


def _duration(ms: int) -> str:
    minutes = (ms + 59_999) // 60_000
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h" if hours else f"{days}d"


def _percent(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".") + "%"


def _tokens(value: int | float) -> str:
    for threshold, suffix in ((1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if value >= threshold * 0.9995:
            amount = value / threshold
            decimals = 2
            if amount >= 99.95:
                decimals = 0
            elif amount >= 9.995:
                decimals = 1
            text = f"{amount:.{decimals}f}"
            if decimals:
                text = text.rstrip("0").rstrip(".")
            return text + suffix
    return str(round(value))


def _usd(value: float) -> str:
    if 0 < value < 0.01:
        return "<$0.01"
    return f"${value:,.2f}"


def _joined(*values: str) -> str:
    return " · ".join(value for value in values if value)


def _account_labels(quotas: list[ProviderQuota]) -> list[str]:
    providers = Counter(quota.provider for quota in quotas)
    names = Counter((quota.provider, quota.account) for quota in quotas)
    seen: Counter[str] = Counter()
    labels = []
    for quota in quotas:
        seen[quota.provider] += 1
        account = quota.account
        if providers[quota.provider] > 1 and (not account or names[quota.provider, account] > 1):
            account = _joined(f"Account {seen[quota.provider]}", account)
        labels.append(account)
    return labels


def _verdict(window: QuotaWindow) -> str:
    if window.status == "exhausted" or (window.used_percent is not None and window.used_percent >= 99.95):
        return "EXHAUSTED"
    if window.pace is not None and window.pace.verdict in _CHIPS:
        return window.pace.verdict
    if window.status == "warning":
        return "WARNING"
    return "NO DATA"


def _clean_label(label: str, provider: str) -> str:
    text = _UNIT_IN_PARENS.sub("", _UNIT_SUFFIX.sub("", _copy(label)))
    prefix = provider_name(provider) + " "
    if text.casefold().startswith(prefix.casefold()) and len(text) > len(prefix):
        text = text[len(prefix):]
    return text or "Quota window"


def _window_label(window: QuotaWindow, provider: str) -> str:
    return _clean_label(window.label, provider)


def _short_label(quota: ProviderQuota, window: QuotaWindow) -> str:
    name = "Codex" if quota.provider == "openai-codex" else provider_name(quota.provider)
    period = _PERIOD.fullmatch(window.label)
    label = period[1] + period[2][0].lower() if period is not None else _window_label(window, quota.provider)
    return _joined(name, label)


def _before_reset(window: QuotaWindow, now_ms: int, exhaust_in_ms: int) -> str:
    if window.reset_ms is None:
        return ""
    before_reset_ms = window.reset_ms - now_ms - exhaust_in_ms
    if before_reset_ms > 0:
        return f"{_duration(before_reset_ms)} before reset"
    if before_reset_ms == 0:
        return "At reset"
    return ""


def _chip(window: QuotaWindow, now_ms: int) -> _Chip | None:
    verdict = _verdict(window)
    if verdict not in _CHIPS:
        return None
    text, tone, icon = _CHIPS[verdict]
    note = ""
    pace = window.pace
    if verdict == "RUN OUT" and pace is not None and pace.exhaust_in_ms is not None:
        text = f"Runs out {_duration(pace.exhaust_in_ms)}"
        note = _before_reset(window, now_ms, pace.exhaust_in_ms)
    elif verdict == "GATED" and pace is not None:
        note = _copy(pace.detail).partition(" · ")[0]
    return _Chip(text, tone, icon, note)


def _projection(window: QuotaWindow) -> float | None:
    if window.pace is None or window.used_percent is None:
        return None
    projected = window.pace.projected_percent
    return projected if projected is not None and abs(projected - window.used_percent) >= 1.0 else None


def _heat(window: QuotaWindow) -> int:
    verdict = _verdict(window)
    used = window.used_percent
    if verdict == "EXHAUSTED" or (used is not None and used >= _BURNING_PERCENT):
        return 2
    if verdict in ("HOT", "RUN OUT") or (used is not None and used >= _WARM_PERCENT):
        return 1
    return 0


def _opportunity(window: QuotaWindow, now_ms: int) -> int:
    used = window.used_percent
    if used is None or _heat(window):
        return 0
    pace = window.pace
    if pace is not None and pace.verdict != "NO DATA":
        if pace.verdict != "SPARE":
            return 0
    else:
        if window.window_ms is None or window.reset_ms is None:
            return 0
        elapsed = min(max(100 * (1 - (window.reset_ms - now_ms) / window.window_ms), 0.0), 100.0)
        if used > elapsed - 40:
            return 0
    if window.reset_ms is None or used > 50:
        return 1
    remaining = window.reset_ms - now_ms
    closing = remaining <= DAY_MS or (window.window_ms is not None and remaining <= 0.2 * window.window_ms)
    return 2 if closing else 1


def _countdown(window: QuotaWindow, now_ms: int) -> str:
    if window.reset_ms is None:
        return ""
    return "Due" if window.reset_ms <= now_ms else _duration(window.reset_ms - now_ms)


def _title_bar(svg: _Svg, left: list[_Run], right: list[_Run], right_x: float) -> int:
    svg.icon("spark", _MARGIN, 44, 34, _VIOLET)
    svg.runs(_MARGIN + 48, 72, left, 20, gap=18)
    if right:
        svg.runs(right_x, 71, right, _SMALL, gap=16, anchor="end")
    return 104


def _history_runs(dashboard: Dashboard, sources: list[str]) -> list[_Run]:
    runs: list[_Run] = []
    if dashboard.quotas and not dashboard.history_sources:
        runs.append(_Run("No pace history", _AMBER, 700))
    elif dashboard.quotas and dashboard.history_partial:
        runs.append(_Run("Partial pace history", _AMBER, 700))
    if sources:
        runs.append(_Run(" + ".join(sources), _MUTED))
    return runs


def _header(svg: _Svg, dashboard: Dashboard) -> int:
    left = [_Run("OMP usage", _WHITE, 800, _TITLE), _Run(_stamp(dashboard.now_ms), _MUTED)]
    updated = dashboard.quota_updated_ms
    if updated is not None and dashboard.now_ms - updated >= _STALE_MS:
        left.append(_Run(f"quotas {_duration(dashboard.now_ms - updated)} old", _AMBER, 700))
    elif updated is None and dashboard.quotas:
        left.append(_Run("quota time unknown", _MUTED))
    token_sources = dashboard.tokens["sources_ok"] if dashboard.tokens is not None else []
    sources = list(dict.fromkeys([*dashboard.history_sources, *token_sources]))
    return _title_bar(svg, left, _history_runs(dashboard, sources), _RIGHT)


def _alerts(svg: _Svg, dashboard: Dashboard, accounts: list[str], y: int) -> int:
    windows = [(quota, window, account) for quota, account in zip(dashboard.quotas, accounts) for window in quota.windows]
    chips: list[tuple[str, str, str, str]] = []
    risk = min(
        (item for item in windows if _verdict(item[1]) in _RISK_ORDER),
        key=lambda item: _RISK_ORDER[_verdict(item[1])], default=None,
    )
    if risk is not None:
        quota, window, account = risk
        verdict = _verdict(window)
        _, tone, icon = _CHIPS[verdict]
        title = _ALERTS.get(verdict, "Runs out")
        if verdict == "RUN OUT" and window.pace is not None and window.pace.exhaust_in_ms is not None:
            title = f"Runs out in {_duration(window.pace.exhaust_in_ms)}"
        used = _percent(window.used_percent) + " used" if window.used_percent is not None else ""
        chips.append((tone, icon, title, _joined(_short_label(quota, window), used, account)))
    next_reset = min(
        ((quota, window, account, window.reset_ms) for quota, window, account in windows
         if window.reset_ms is not None and window.reset_ms > dashboard.now_ms),
        key=lambda item: item[3], default=None,
    )
    if next_reset is not None:
        quota, window, account, reset_ms = next_reset
        title = "Next reset in " + _duration(reset_ms - dashboard.now_ms)
        chips.append((_PERIWINKLE, "clock", title, _joined(_short_label(quota, window), account)))
    if not chips:
        return y
    width = (_RIGHT - _MARGIN - _GAP) / 2
    for index, (tone, icon, title, context) in enumerate(chips):
        x = _MARGIN + index * (width + _GAP)
        svg.rect(x, y, width, 64, tone, 20, opacity=0.1, stroke=tone, stroke_opacity=0.4)
        svg.circle(x + 36, y + 32, 20, tone, opacity=0.2)
        svg.icon(icon, x + 24, y + 20, 24, tone)
        title_text = _fit(title, _BODY, width - 96, 700)
        runs = [_Run(title_text, tone, 700)]
        room = width - 72 - _width(title_text, _BODY, 700) - 14 - 28
        if context and room > 60:
            runs.append(_Run(_fit(context, 20, room), _MUTED, 500, 20))
        svg.runs(x + 72, y + 40, runs, _BODY, gap=14)
    return y + 64 + _SECTION_GAP


def _card_height(quota: ProviderQuota) -> int:
    rows = _ROW_HEIGHT * len(quota.windows) if quota.windows else 40
    return _CARD_TOP + rows + 16


def _pill(svg: _Svg, x: float, y: float, chip: _Chip, room: float) -> None:
    text = _fit(chip.text, _SMALL, room - 52, 700)
    width = 56 + _width(text, _SMALL, 700)
    svg.rect(x, y, width, 34, chip.tone, 17, opacity=0.15, stroke=chip.tone, stroke_opacity=0.32)
    svg.icon(chip.icon, x + 13, y + 8, 18, chip.tone)
    svg.text(x + 39, y + 23, text, _SMALL, chip.tone, weight=700)


def _opportunity_row(svg: _Svg, left: float, right: float, y: float, height: int, opportunity: int) -> None:
    if opportunity:
        opacity = 0.92 if opportunity == 2 else 0.7
        svg.rainbow_outline(left - 12, y + 2, right - left + 24, height - 4, 12, opacity)


def _quota_row(svg: _Svg, x: float, right: float, y: float, window: QuotaWindow, provider: str, now_ms: int) -> None:
    gauge_end = right - _GAUGE_INSET
    used_x = right - _USED_INSET
    pace_x = right - _PACE_WIDTH
    used = window.used_percent
    verdict = _verdict(window)
    chip = _chip(window, now_ms)
    heat = _heat(window)
    reset = _countdown(window, now_ms)
    reset_width = 0.0
    if reset:
        reset_width = _width(reset, _SMALL) + 26
        svg.icon("clock", gauge_end - reset_width, y + 8, 18, _MUTED)
        svg.text(gauge_end, y + 23, reset, _SMALL, _MUTED, anchor="end")
    label_room = gauge_end - x - reset_width - 18
    svg.text(x, y + 24, _fit(_window_label(window, provider), _BODY, label_room), _BODY)
    bar_y = y + 36
    bar_width = gauge_end - x
    svg.rect(x, bar_y, bar_width, _BAR_HEIGHT, _TRACK, _BAR_HEIGHT / 2)
    fill_end = x
    if used is not None and used > 0:
        fill_width = max(_BAR_HEIGHT, bar_width * min(used, 100.0) / 100)
        fill_end = x + fill_width
        ink = _FLAME_ORANGE if heat else _provider_color(provider)
        svg.rect(x, bar_y, fill_width, _BAR_HEIGHT, ink, _BAR_HEIGHT / 2)
    projected = _projection(window)
    tone = chip.tone if chip is not None else _MUTED
    marker = fill_end
    if projected is not None:
        marker = x + bar_width * min(max(projected, 0.0), 100.0) / 100
        if marker > fill_end:
            start = max(x, fill_end - _BAR_HEIGHT / 2)
            svg.rect(start, bar_y, marker - start, _BAR_HEIGHT, tone, _BAR_HEIGHT / 2, opacity=0.3)
    if projected is not None:
        svg.circle(marker, bar_y + _BAR_HEIGHT / 2, 7, tone, stroke=_PANEL, stroke_width=3)
    if used is None:
        svg.rect(used_x - 22, y + 27, 22, 3, _MUTED, 1.5)
    else:
        used_color = _WHITE
        if verdict == "EXHAUSTED":
            used_color = _CORAL
        elif window.status == "warning":
            used_color = _AMBER
        used_text = _percent(used)
        svg.text(used_x, y + 37, used_text, 24, used_color, weight=700, anchor="end", mono=True)
        glyph_x = used_x - _width(used_text, 24, mono=True) - 6
        if heat == 2:
            svg.flame(glyph_x - 24, y + 14, 24)
        elif heat == 1:
            svg.flame(glyph_x - 18, y + 19, 18)
    if chip is None:
        return
    if chip.note:
        _pill(svg, pace_x, y, chip, _PACE_WIDTH)
        svg.text(pace_x + 14, y + 54, _fit(chip.note, _TINY, _PACE_WIDTH - 14), _TINY, _MUTED)
    else:
        _pill(svg, pace_x, y + 11, chip, _PACE_WIDTH)


def _card_header(svg: _Svg, left: float, right: float, y: float, quota: ProviderQuota, account: str) -> None:
    svg.badge(left, y + 24, quota.provider, color=_provider_color(quota.provider))
    plan = quota.plan[:1].upper() + quota.plan[1:]
    if plan.casefold() == provider_name(quota.provider).casefold():
        plan = ""
    detail = _joined(plan, account)
    name = _fit(provider_name(quota.provider), _HEAD, right - left - 58, 700)
    runs = [_Run(name, _WHITE, 700)]
    room = right - left - 58 - _width(name, _HEAD, 700) - 12
    if detail and room > 40:
        runs.append(_Run(_fit(detail, 20, room), _MUTED, 500, 20))
    svg.runs(left + 58, y + 54, runs, _HEAD, gap=12)


def _provider_card(
    svg: _Svg, x: float, y: float, width: float, height: float, quota: ProviderQuota, account: str, now_ms: int
) -> None:
    opportunities = [_opportunity(window, now_ms) for window in quota.windows]
    rainbow = bool(opportunities) and all(opportunities)
    svg.card(x, y, width, height, _provider_color(quota.provider), rainbow=rainbow)
    left = x + _PAD
    right = x + width - _PAD
    _card_header(svg, left, right, y, quota, account)
    row_y = y + _CARD_TOP
    if not quota.windows:
        svg.text(left, row_y + 24, "No windows reported", 20, _MUTED)
    for window, opportunity in zip(quota.windows, opportunities):
        if not rainbow:
            _opportunity_row(svg, left, right, row_y - 5, _ROW_HEIGHT, opportunity)
        _quota_row(svg, left, right, row_y, window, quota.provider, now_ms)
        row_y += _ROW_HEIGHT


def _unavailable_card(svg: _Svg, y: float, message: str) -> int:
    svg.card(_MARGIN, y, _RIGHT - _MARGIN, 92, _SLATE)
    svg.badge(_MARGIN + _PAD, y + 24, None, icon="alert", color=_SLATE)
    svg.text(_MARGIN + _PAD + 58, y + 54, _fit(message, _BODY, _RIGHT - _MARGIN - 2 * _PAD - 58), _BODY, _MUTED)
    return int(y) + 92


def _issue_line(svg: _Svg, y: float, issue: str) -> int:
    svg.icon("alert", _MARGIN + 2, y, 22, _AMBER)
    svg.text(_MARGIN + 34, y + 18, _fit(issue, _SMALL, _RIGHT - _MARGIN - 34, 700), _SMALL, _AMBER, weight=700)
    return int(y) + 22 + _GAP


def _quotas(svg: _Svg, dashboard: Dashboard, accounts: list[str], top: int) -> int:
    if not dashboard.quotas:
        return _unavailable_card(svg, top, dashboard.quota_issue or "Quota data unavailable")
    y = _issue_line(svg, top, dashboard.quota_issue) if dashboard.quota_issue else top
    cards = list(zip(dashboard.quotas, accounts))
    half = (_RIGHT - _MARGIN - _GAP) / 2
    for start in range(0, len(cards), 2):
        group = cards[start:start + 2]
        width = half if len(group) == 2 else _RIGHT - _MARGIN
        height = max(_card_height(quota) for quota, _ in group)
        for index, (quota, account) in enumerate(group):
            _provider_card(svg, _MARGIN + index * (half + _GAP), y, width, height, quota, account, dashboard.now_ms)
        y += height + _GAP
    return y - _GAP


def _axis_step(peak: int) -> int:
    power = 10 ** (len(str(peak)) - 1)
    for numerator in (1, 2, 3, 4, 5, 6, 8, 10, 15, 20):
        step = max(1, power * numerator // 2)
        if step * 2 >= peak:
            return step
    return power * 10


def _daily_chart(
    svg: _Svg, left: float, right: float, y: float, days: list[DayTotal], today: DayTotal | None, *, partial: bool
) -> None:
    peak = max((day["tokens"] for day in days), default=0)
    if peak == 0:
        empty_label = "Daily usage unavailable"
        if days:
            empty_label = "No tokens in collected data" if partial else "No tokens recorded"
        svg.text(left, y + 28, empty_label, 20, _MUTED)
        return
    axis_x = left + 50
    plot_x = axis_x + 16
    top = y + 12
    base = y + _CHART_HEIGHT - 34
    step = _axis_step(peak)
    slot = (right - plot_x) / len(days)
    bar_width = min(18.0, slot * 0.62)
    today_index = len(days) - 1 if days[-1] is today else None
    if today_index is not None:
        center = plot_x + (today_index + 0.5) * slot
        svg.rect(center - bar_width / 2 - 7, top - 6, bar_width + 14, base - top + 6, _MINT, 9, opacity=0.12)
    for tick, level in enumerate((step * 2, step, 0)):
        level_y = top + tick * (base - top) / 2
        if level:
            svg.rule(plot_x, level_y, right, _WHITE, 0.16, dashed=True)
        else:
            svg.rule(plot_x, level_y, right, _WHITE, 0.2)
        svg.text(axis_x, level_y + 6, _tokens(level), _MICRO, _MUTED, anchor="end", mono=True)
    pixels_per_token = (base - top) / (step * 2)
    radius = min(5.0, bar_width / 2)
    peak_index = max(range(len(days)), key=lambda index: days[index]["tokens"])
    for index, day in enumerate(days):
        total_height = day["tokens"] * pixels_per_token
        if total_height <= 0:
            continue
        bar_x = plot_x + (index + 0.5) * slot - bar_width / 2
        clip_id = svg.clip(bar_x, base - total_height, bar_width, total_height + radius, radius)
        svg.raw(f'<g clip-path="url(#{clip_id})">')
        bottom = float(base)
        for provider in day["providers"]:
            if provider["tokens"] > 0:
                segment = provider["tokens"] * pixels_per_token
                bottom -= segment
                svg.rect(bar_x, bottom, bar_width, segment, _provider_color(provider["provider"]))
        svg.raw("</g>")
        if index == peak_index:
            svg.flame(bar_x + bar_width / 2 - 9, base - total_height - 24, 18)
    label_y = base + 26
    last_label = "Today" if today_index is not None else _date(days[-1]["start_ms"])
    last_color = _MINT if today_index is not None else _MUTED
    if len(days) > 1:
        svg.text(plot_x, label_y, _date(days[0]["start_ms"]), _MICRO, _MUTED)
        if len(days) >= 7:
            middle = len(days) // 2
            svg.text(plot_x + (middle + 0.5) * slot, label_y, _date(days[middle]["start_ms"]), _MICRO, _MUTED,
                     anchor="middle")
    svg.text(right, label_y, last_label, _MICRO, last_color, weight=700 if today_index is not None else 500, anchor="end")


def _legend(svg: _Svg, left: float, right: float, y: float, providers: list[ProviderTotal]) -> float:
    tokens_x = left + 296
    total = sum(item["tokens"] for item in providers)
    for item in providers:
        name = item["provider"]
        color = _provider_color(name)
        svg.rect(left, y, right - left, _PILL_HEIGHT, color, _PILL_HEIGHT / 2, opacity=0.12, stroke=color,
                 stroke_opacity=0.3)
        svg.logo_mark(left + 13, y + 11, 22, name)
        tokens = _tokens(item["tokens"])
        tokens_left = tokens_x - _width(tokens, 20, mono=True)
        if total and item["tokens"] / total >= _HOT_TOKEN_SHARE:
            tokens_left -= 26
            svg.flame(tokens_left, y + 12, 20)
        name_room = tokens_left - 14 - (left + 46)
        svg.text(left + 46, y + 29, _fit(provider_name(name), 20, name_room), 20)
        svg.text(tokens_x, y + 29, tokens, 20, weight=700, anchor="end", mono=True)
        recorded = item["estimated_usd"]
        modeled = item["unpriced_estimated_usd"]
        cost: list[_Run] = []
        if recorded or not item["unpriced_records"]:
            cost.append(_Run(_usd(recorded), _MUTED))
        if modeled:
            cost.append(_Run(("+" if cost else "") + _usd(modeled) + " est.", _MINT))
        elif not cost:
            cost.append(_Run("unpriced", _MUTED))
        svg.runs(right - 18, y + 29, cost, _SMALL, gap=6, anchor="end")
        y += _PILL_HEIGHT + _PILL_GAP
    return y - _PILL_GAP


def _stat(
    svg: _Svg, x: float, y: float, width: float, accent: str, label: str, value: str | None, note: _Run | None = None
) -> None:
    svg.rect(x, y, width, _TILE_HEIGHT, accent, 18, opacity=0.1, stroke=accent, stroke_opacity=0.3)
    svg.circle(x + 24, y + 25, 5, accent)
    svg.text(x + 38, y + 31, label, _TINY, _MUTED)
    if note is not None:
        svg.text(x + width - 18, y + 31, note.text, _MICRO, note.color, weight=700, anchor="end")
    if value is None:
        svg.rect(x + 20, y + 56, 26, 4, _MUTED, 2)
    else:
        svg.text(x + 18, y + 68, value, 28, weight=700, mono=True)


def _tokens_panel(svg: _Svg, dashboard: Dashboard, top: int) -> int:
    left = _MARGIN + _PAD
    right = _RIGHT - _PAD
    snapshot = dashboard.tokens
    svg.badge(left, top + 24, None, icon="chart", color=_VIOLET)
    title = [_Run("Tokens", _WHITE, 700)]
    if snapshot is not None and snapshot["sources_ok"]:
        span_days = max(1, (snapshot["end_ms"] - snapshot["start_ms"] + DAY_MS - 1) // DAY_MS)
        title.append(_Run(f"{span_days} days", _MUTED, 500, 20))
    svg.runs(left + 58, top + 54, title, _HEAD, gap=12)
    y = top + _CARD_TOP
    if snapshot is None or not snapshot["sources_ok"]:
        svg.text(left, y + 24, "Token data unavailable", _BODY, _MUTED)
        bottom = y + 40 + 16
        svg.card(_MARGIN, top, _RIGHT - _MARGIN, bottom - top, _VIOLET)
        return bottom
    issues = len(snapshot["issues"])
    if issues:
        text = f"Partial · {issues} {'issue' if issues == 1 else 'issues'}"
        svg.text(right, top + 53, text, _SMALL, _AMBER, weight=700, anchor="end")
        svg.icon("alert", right - _width(text, _SMALL, 700) - 28, top + 36, 20, _AMBER)
    providers = sorted(
        (item for item in snapshot["providers"] if item["tokens"] or item["estimated_usd"] or item["unpriced_records"]),
        key=lambda item: (-item["tokens"], item["provider"]),
    )
    total = sum(item["tokens"] for item in providers)
    known = math.fsum(item["estimated_usd"] for item in providers)
    modeled = math.fsum(item["unpriced_estimated_usd"] for item in providers)
    unpriced = sum(item["unpriced_records"] for item in providers)
    days = snapshot["days"]
    current_day = _utc(dashboard.now_ms).date()
    today = next((day for day in reversed(days) if _utc(day["start_ms"]).date() == current_day), None)
    tiles_right = left + _TILES_WIDTH if providers else right
    tile_width = (tiles_right - left - 2 * 20) / 3
    _stat(svg, left, y, tile_width, _VIOLET, "Total", _tokens(total))
    _stat(svg, left + tile_width + 20, y, tile_width, _CYAN, "Today",
          _tokens(today["tokens"]) if today is not None else None)
    note = None
    if modeled:
        note = _Run(("+" if known else "") + _usd(modeled) + " modeled", _MINT)
    elif unpriced:
        note = _Run(f"{unpriced:,} unpriced", _AMBER)
    _stat(svg, left + 2 * (tile_width + 20), y, tile_width, _PINK, "Known cost",
          None if unpriced and not known else _usd(known), note)
    chart_y = y + _TILE_HEIGHT + 28
    _daily_chart(svg, left, tiles_right, chart_y, days, today, partial=bool(issues))
    bottom = chart_y + _CHART_HEIGHT
    if providers:
        bottom = max(bottom, _legend(svg, tiles_right + _LEGEND_GAP, right, y, providers))
    bottom += 24
    svg.card(_MARGIN, top, _RIGHT - _MARGIN, bottom - top, _VIOLET)
    return bottom


def render_svg(dashboard: Dashboard) -> bytes:
    svg = _Svg()
    accounts = _account_labels(dashboard.quotas)
    top = _alerts(svg, dashboard, accounts, _header(svg, dashboard))
    tokens_top = _quotas(svg, dashboard, accounts, top) + _SECTION_GAP
    return svg.finish(
        _tokens_panel(svg, dashboard, tokens_top) + _MARGIN,
        title="OMP usage dashboard",
        desc="Quota windows, pace to reset, and daily token usage.",
    )


def _forecast_ready(window: QuotaWindow) -> bool:
    return window.pace is not None and window.pace.verdict != "NO DATA"


def _forecast_height(quota: ProviderQuota) -> int:
    if not quota.windows:
        return _CARD_TOP + 40 + 16
    rows = sum(_FORECAST_ROW if _forecast_ready(window) else _COMPACT_ROW for window in quota.windows)
    return _CARD_TOP + rows + 8


def _risk_rank(quota: ProviderQuota) -> int:
    return min((_RISK_ORDER.get(_verdict(window), len(_RISK_ORDER)) for window in quota.windows), default=len(_RISK_ORDER))


def _advice(window: QuotaWindow, pace: Pace, now_ms: int) -> str:
    if pace.verdict == "RUN OUT" and pace.exhaust_in_ms is not None:
        lead = _copy(pace.detail).partition(" · ")[0]
        hits = f"hits 100% in {_duration(pace.exhaust_in_ms)}"
        return _joined(lead, hits, _before_reset(window, now_ms, pace.exhaust_in_ms))
    return _copy(pace.detail)


def _reset_label(svg: _Svg, x: float, baseline: float, window: QuotaWindow, now_ms: int) -> None:
    countdown = _countdown(window, now_ms)
    if countdown:
        svg.icon("clock", x, baseline - 15, 18, _MUTED)
        svg.text(x + 26, baseline, countdown, _SMALL, _MUTED)


def _sparkline(
    svg: _Svg, x: float, y: float, values: tuple[float | None, ...], color: str, projected: float | None, tone: str,
) -> None:
    svg.rect(x, y, _SPARK_WIDTH, _SPARK_HEIGHT, _TRACK, 12, opacity=0.45)
    history = _SPARK_WIDTH - _SPARK_FUTURE
    top = y + 8
    bottom = y + _SPARK_HEIGHT - 8
    span = bottom - top
    svg.raw(
        f'<path d="M{x + history:.1f} {y + 6:.1f}V{y + _SPARK_HEIGHT - 6:.1f}" stroke="{_WHITE}" stroke-opacity="0.16" '
        'stroke-width="1.5" stroke-dasharray="2 5"/>'
    )
    step = (history - 14) / (len(values) - 1) if len(values) > 1 else 0.0
    runs: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for index, value in enumerate(values):
        if value is None:
            if current:
                runs.append(current)
                current = []
            continue
        current.append((x + 7 + index * step, bottom - min(max(value, 0.0), 1.0) * span))
    if current:
        runs.append(current)
    for points in runs:
        if len(points) == 1:
            svg.circle(points[0][0], points[0][1], 3, color)
            continue
        line = "L".join(f"{px:.1f} {py:.1f}" for px, py in points)
        svg.raw(
            f'<path d="M{points[0][0]:.1f} {bottom:.1f}L{line}L{points[-1][0]:.1f} {bottom:.1f}Z" fill="{color}" '
            'fill-opacity="0.16"/>'
        )
        svg.raw(
            f'<path d="M{line}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" '
            'stroke-linecap="round"/>'
        )
    if not runs:
        return
    last_x, last_y = runs[-1][-1]
    if projected is not None:
        end_x = x + _SPARK_WIDTH - 16
        end_y = bottom - min(max(projected / 100, 0.0), 1.0) * span
        svg.raw(
            f'<path d="M{last_x:.1f} {last_y:.1f}L{end_x:.1f} {end_y:.1f}" stroke="{tone}" stroke-width="2.5" '
            'stroke-dasharray="5 5" stroke-linecap="round"/>'
        )
        svg.circle(end_x, end_y, 6, tone, stroke=_PANEL, stroke_width=3)
    svg.circle(last_x, last_y, 5, color, stroke=_PANEL, stroke_width=2.5)


def _forecast_row(
    svg: _Svg, left: float, right: float, y: float, window: QuotaWindow, pace: Pace, provider: str, now_ms: int
) -> None:
    chip = _chip(window, now_ms)
    tone = chip.tone if chip is not None else _MUTED
    color = _provider_color(provider)
    projected = pace.projected_percent
    heat = _heat(window)
    svg.text(left, y + 36, _fit(_window_label(window, provider), _BODY, _SPARK_OFFSET - 28), _BODY)
    _reset_label(svg, left, y + 66, window, now_ms)
    spark_x = left + _SPARK_OFFSET
    _sparkline(svg, spark_x, y + 14, pace.spark, color, projected, tone)
    numbers_x = left + _NUMBERS_OFFSET
    x = numbers_x
    used = window.used_percent
    if used is None:
        svg.rect(x, y + 32, 22, 3, _MUTED, 1.5)
        x += 22
    else:
        now_text = _percent(used)
        svg.text(x, y + 44, now_text, 26, _CORAL if _verdict(window) == "EXHAUSTED" else _WHITE, weight=700, mono=True)
        x += _width(now_text, 26, mono=True)
    if projected is not None and _verdict(window) != "EXHAUSTED":
        svg.icon("arrow", x + 10, y + 24, 22, _MUTED)
        projected_text = _percent(projected)
        svg.text(x + 42, y + 44, projected_text, 26, tone, weight=700, mono=True)
        x += 42 + _width(projected_text, 26, mono=True)
    if heat:
        size = 24 if heat == 2 else 18
        svg.flame(x + 8, y + 32 - size / 2, size)
        x += size + 8
    if "?" not in pace.rate:
        svg.text(x + 20, y + 43, pace.rate, _SMALL, _MUTED, mono=True)
    if chip is not None:
        text = _fit(chip.text, _SMALL, _PACE_WIDTH - 52, 700)
        _pill(svg, right - 56 - _width(text, _SMALL, 700), y + 16, chip, _PACE_WIDTH)
    svg.text(numbers_x, y + 80, _fit(_advice(window, pace, now_ms), _SMALL, right - numbers_x), _SMALL, _MUTED)


def _compact_row(svg: _Svg, left: float, right: float, y: float, window: QuotaWindow, provider: str, now_ms: int) -> None:
    svg.text(left, y + 34, _fit(_window_label(window, provider), 20, _SPARK_OFFSET - 28), 20, _MUTED)
    _reset_label(svg, left + _SPARK_OFFSET, y + 34, window, now_ms)
    numbers_x = left + _NUMBERS_OFFSET
    used = window.used_percent
    if used is None:
        svg.rect(numbers_x, y + 26, 22, 3, _MUTED, 1.5)
    else:
        used_color = _CORAL if _verdict(window) == "EXHAUSTED" else _MUTED
        used_text = _percent(used)
        svg.text(numbers_x, y + 35, used_text, 20, used_color, weight=700, mono=True)
        heat = _heat(window)
        if heat:
            size = 24 if heat == 2 else 18
            svg.flame(numbers_x + _width(used_text, 20, mono=True) + 8, y + 26 - size / 2, size)
    chip = _chip(window, now_ms)
    pill_left = right
    if chip is not None:
        text = _fit(chip.text, _SMALL, _PACE_WIDTH - 52, 700)
        pill_left = right - 56 - _width(text, _SMALL, 700)
        _pill(svg, pill_left, y + 11, chip, _PACE_WIDTH)
    note = _copy(window.pace.detail) if window.pace is not None else "No forecast"
    note_x = numbers_x + 90
    svg.text(note_x, y + 34, _fit(note, _SMALL, pill_left - note_x - 16), _SMALL, _MUTED)


def _forecast_card(svg: _Svg, y: float, height: float, quota: ProviderQuota, account: str, now_ms: int) -> None:
    opportunities = [_opportunity(window, now_ms) for window in quota.windows]
    rainbow = bool(opportunities) and all(opportunities)
    svg.card(_MARGIN, y, _RIGHT - _MARGIN, height, _provider_color(quota.provider), rainbow=rainbow)
    left = _MARGIN + _PAD
    right = _RIGHT - _PAD
    _card_header(svg, left, right, y, quota, account)
    row_y = y + _CARD_TOP
    if not quota.windows:
        svg.text(left, row_y + 24, "No windows reported", 20, _MUTED)
    for index, (window, opportunity) in enumerate(zip(quota.windows, opportunities)):
        pace = window.pace
        ready = pace is not None and _forecast_ready(window)
        row_height = _FORECAST_ROW if ready else _COMPACT_ROW
        if not rainbow:
            _opportunity_row(svg, left, right, row_y, row_height, opportunity)
        if index:
            svg.rule(left, row_y, right, _WHITE, 0.07)
        if pace is not None and ready:
            _forecast_row(svg, left, right, row_y, window, pace, quota.provider, now_ms)
        else:
            _compact_row(svg, left, right, row_y, window, quota.provider, now_ms)
        row_y += row_height


def render_forecast_svg(dashboard: Dashboard) -> bytes:
    svg = _Svg()
    left = [_Run("Predictions", _WHITE, 800, _TITLE), _Run(_stamp(dashboard.now_ms), _MUTED)]
    y = _title_bar(svg, left, _history_runs(dashboard, dashboard.history_sources), _RIGHT)
    if not dashboard.quotas:
        bottom = _unavailable_card(svg, y, dashboard.quota_issue or "Quota data unavailable")
    else:
        if dashboard.quota_issue:
            y = _issue_line(svg, y, dashboard.quota_issue)
        cards = sorted(zip(dashboard.quotas, _account_labels(dashboard.quotas)), key=lambda item: _risk_rank(item[0]))
        for quota, account in cards:
            height = _forecast_height(quota)
            _forecast_card(svg, y, height, quota, account, dashboard.now_ms)
            y += height + _GAP
        bottom = y - _GAP
    return svg.finish(
        bottom + _MARGIN,
        title="OMP usage predictions",
        desc="Pace history, projected usage at reset, and advice per quota window.",
    )


def _reset_sparks(svg: _Svg, right: float, y: float, color: str) -> None:
    svg.icon("spark", right - 70, y + 26, 48, color)
    svg.icon("spark", right - 100, y + 40, 16, color)
    svg.icon("spark", right - 25, y + 20, 20, color)


def _reset_card(svg: _Svg, y: float, event: ResetEvent, now_ms: int) -> None:
    x = _MARGIN
    width = _RESET_WIDTH - 2 * _MARGIN
    right = x + width - _PAD
    color = _provider_color(event.provider)
    svg.card(x, y, width, _RESET_CARD, color)
    center_x = x + _PAD + 64
    center_y = y + _RESET_CARD / 2
    fresh = min(max(100.0 - event.fresh_used_percent, 0.0), 100.0)
    circumference = 2 * math.pi * _RING_RADIUS
    svg.raw(
        f'<circle cx="{center_x:.1f}" cy="{center_y:.1f}" r="{_RING_RADIUS}" fill="none" stroke="{_TRACK}" stroke-width="16"/>'
    )
    if fresh > 0:
        svg.raw(
            f'<circle cx="{center_x:.1f}" cy="{center_y:.1f}" r="{_RING_RADIUS}" fill="none" stroke="{color}" '
            f'stroke-width="16" stroke-linecap="round" stroke-dasharray="{circumference * fresh / 100:.2f} {circumference:.2f}" '
            f'transform="rotate(-90 {center_x:.1f} {center_y:.1f})"/>'
        )
    svg.text(center_x, center_y + 8, _percent(fresh), 28, weight=700, anchor="middle", mono=True)
    svg.text(center_x, center_y + 30, "left", _MICRO, _MUTED, anchor="middle")
    text_x = x + _PAD + 128 + 40
    _reset_sparks(svg, right, y, color)
    svg.badge(text_x, y + 28, event.provider, color=color)
    name = _fit(provider_name(event.provider), 24, right - 170 - text_x - 58, 700)
    runs = [_Run(name, _WHITE, 700)]
    room = right - 170 - text_x - 58 - _width(name, 24, 700) - 12
    label = _clean_label(event.label, event.provider)
    if room > 40:
        runs.append(_Run(_fit(label, _BODY, room), _MUTED, 500, _BODY))
    svg.runs(text_x + 58, y + 58, runs, 24, gap=12)
    closed = min(max(event.closed_used_percent, 0.0), 100.0)
    svg.rect(text_x, y + 98, 120, 10, _TRACK, 5)
    if closed > 0:
        svg.rect(text_x, y + 98, max(10.0, 120 * closed / 100), 10, _SLATE, 5)
    closed_runs = [_Run(f"Closed at {_percent(closed)} used", _WHITE)]
    if event.amount_text:
        closed_runs.append(_Run(_copy(event.amount_text), _MUTED))
    svg.runs(text_x + 136, y + 110, closed_runs, 20, gap=12)
    svg.icon("calendar", text_x, y + 131, 18, _MUTED)
    rolled = f"Rolled over {_stamp(event.closed_at_ms)}"
    svg.text(text_x + 26, y + 146, rolled, _SMALL, _MUTED)
    next_x = text_x + 26 + _width(rolled, _SMALL) + 28
    svg.icon("refresh", next_x, y + 131, 18, _MUTED)
    remaining = event.resets_at_ms - now_ms
    next_reset = f"Next reset {_date(event.resets_at_ms)}"
    if remaining > 0:
        next_reset = _joined(next_reset, f"in {_duration(remaining)}")
    svg.text(next_x + 26, y + 146, _fit(next_reset, _SMALL, right - next_x - 26), _SMALL, _MUTED)


def render_reset_svg(events: list[ResetEvent], now_ms: int) -> bytes:
    svg = _Svg()
    kinds = {event.kind for event in events}
    title = "Limit resets"
    if len(kinds) == 1:
        kind = next(iter(kinds)).capitalize()
        title = f"{kind} limit reset" if len(events) == 1 else f"{kind} limits reset"
    y = _title_bar(svg, [_Run(title, _WHITE, 800, _TITLE), _Run(_stamp(now_ms), _MUTED)], [], _RESET_WIDTH - _MARGIN)
    for event in events:
        _reset_card(svg, y, event, now_ms)
        y += _RESET_CARD + _GAP
    return svg.finish(
        y - _GAP + _MARGIN,
        width=_RESET_WIDTH,
        title=title,
        desc="Quota windows that rolled over with fresh capacity.",
    )


_W_LOCK_WINDOWS = 3
_W_STATES = {
    "EXHAUSTED": "exhausted",
    "RUN OUT": "run_out",
    "GATED": "gated",
    "HOT": "hot",
    "WARNING": "near",
    "ON PACE": "on_pace",
    "SPARE": "spare",
}
_W_SHORT_NAMES = {"openai-codex": "Codex", "anthropic": "Claude", "google-antigravity": "Antigravity"}
_W_SPANS = {"hourly": "1h", "daily": "1d", "weekly": "7d", "monthly": "1mo"}
_W_FILLER = frozenset({"quota", "limit", "token", "tokens", "request", "requests", "credit", "credits", "usage", "window"})
_W_PARENS = re.compile(r"\(([^)]*)\)")
_W_WORD = re.compile(r"[^\W_][\w.+-]*")


def _w_provider(provider: str) -> str:
    return _W_SHORT_NAMES.get(_PROVIDER_ALIASES.get(provider, provider)) or provider_name(provider)


def _w_span(window: QuotaWindow) -> str:
    if window.window_ms is not None:
        if window.window_ms < 3_600_000:
            return f"{max(round(window.window_ms / 60_000), 1)}min"
        hours = round(window.window_ms / 3_600_000)
        if hours < 48:
            return f"{hours}h"
        days = round(hours / 24)
        return "1mo" if 28 <= days <= 31 else f"{days}d"
    period = _PERIOD.search(window.label)
    if period is not None:
        unit = period[2][0].lower()
        return period[1] + ("min" if unit == "m" else unit)
    text = window.label.casefold()
    return next((span for word, span in _W_SPANS.items() if word in text), "")


def _w_qualifier(quota: ProviderQuota, window: QuotaWindow) -> str:
    text = _clean_label(window.label, quota.provider)
    skip = {word.casefold() for word in f"{provider_name(quota.provider)} {_w_provider(quota.provider)}".split()}
    words: list[str] = []
    seen: set[str] = set()
    for piece in (_W_PARENS.sub(" ", text), *_W_PARENS.findall(text)):
        for word in _W_WORD.findall(_PERIOD.sub(" ", piece)):
            folded = word.casefold()
            if folded in skip or folded in seen or folded in _W_FILLER or folded in _W_SPANS or folded.isdigit():
                continue
            seen.add(folded)
            words.append(word)
    return " ".join(words)


def _w_label(quota: ProviderQuota, window: QuotaWindow) -> str:
    label = " ".join(part for part in (_w_qualifier(quota, window), _w_span(window)) if part)
    return label or _window_label(window, quota.provider)


def _w_tags(quotas: list[ProviderQuota]) -> list[str]:
    providers = Counter(quota.provider for quota in quotas)
    tags = []
    for quota, account in zip(quotas, _account_labels(quotas)):
        if providers[quota.provider] < 2:
            tags.append("")
        elif account.startswith("Account "):
            tags.append("#" + account.split()[1])
        else:
            tags.append(account.partition("@")[0])
    for provider in providers:
        indexes = [index for index, quota in enumerate(quotas) if quota.provider == provider]
        named = [tags[index] for index in indexes if tags[index]]
        if len(named) == len(set(named)):
            continue
        for position, index in enumerate(indexes, start=1):
            tags[index] = f"#{position}"
    return tags


def _w_out_ms(window: QuotaWindow, now_ms: int) -> int | None:
    pace = window.pace
    if _verdict(window) != "RUN OUT" or pace is None or pace.exhaust_in_ms is None:
        return None
    return now_ms + pace.exhaust_in_ms


def _w_state(window: QuotaWindow) -> str:
    return _W_STATES.get(_verdict(window), "unknown")


def _w_rank(window: QuotaWindow) -> tuple[int, float, float]:
    verdict = _verdict(window)
    reset = float(window.reset_ms) if window.reset_ms is not None else math.inf
    pace = window.pace
    if verdict == "EXHAUSTED":
        return 0, -reset, 0.0
    if verdict == "RUN OUT" and pace is not None and pace.exhaust_in_ms is not None:
        return 1, float(pace.exhaust_in_ms), reset
    used = window.used_percent
    if used is None:
        return 4, 0.0, reset
    projected = pace.projected_percent if pace is not None else None
    pressure = max(used, projected) if projected is not None else used
    return (2 if verdict in _RISK_ORDER else 3), -pressure, reset


def _w_ranked(view: Dashboard) -> list[tuple[ProviderQuota, QuotaWindow, str]]:
    items = [
        (quota, window, tag)
        for quota, tag in zip(view.quotas, _w_tags(view.quotas))
        for window in quota.windows
    ]
    return sorted(items, key=lambda item: _w_rank(item[1]))


def _w_lock(quota: ProviderQuota, window: QuotaWindow, tag: str, now_ms: int) -> dict[str, object]:
    used = window.used_percent
    projected = window.pace.projected_percent if window.pace is not None else None
    return {
        "provider": " ".join(part for part in (_w_provider(quota.provider), tag) if part),
        "window": _w_label(quota, window),
        "used": round(used, 1) if used is not None else None,
        "state": _w_state(window),
        "heat": _heat(window),
        "projected": round(projected, 1) if projected is not None else None,
        "out_ms": _w_out_ms(window, now_ms),
        "reset_ms": window.reset_ms,
    }


def widget_summary(view: Dashboard) -> dict[str, object]:
    """Lock screen data; `focus` and `next` follow one urgency order.

    Exhausted windows come first, latest reset first. Windows projected to run out follow, soonest
    exhaustion first. Gated, hot, and near-limit windows come next, then every other window with
    usage; both tiers sort by the higher of used and projected percent, then soonest reset.
    Windows without usage come last, and ties keep report order.
    """
    entries = [_w_lock(quota, window, tag, view.now_ms) for quota, window, tag in _w_ranked(view)[:_W_LOCK_WINDOWS]]
    return {
        "updated_ms": view.quota_updated_ms,
        "issue": view.quota_issue,
        "focus": entries[0] if entries else None,
        "next": entries[1:],
    }


_RECENT_LIMIT = 60


def window_signal(window: QuotaWindow, now_ms: int) -> str:
    """hot = blocked or burning fast, opportunity = closing window with room, normal = the rest."""
    if _verdict(window) in ("GATED", "WARNING") or _heat(window):
        return "hot"
    if _opportunity(window, now_ms):
        return "opportunity"
    return "normal"


def _token_only_windows(view: Dashboard) -> list[dict[str, object]]:
    if view.tokens is None:
        return []
    quoted = {_PROVIDER_ALIASES.get(quota.provider, quota.provider) for quota in view.quotas}
    active = [total for total in view.tokens["providers"] if total["tokens"] > 0]
    entries = []
    for total in sorted(active, key=lambda total: total["tokens"], reverse=True):
        provider = total["provider"]
        if _PROVIDER_ALIASES.get(provider, provider) in quoted:
            continue
        entries.append(
            {
                "provider": provider,
                "account": "",
                "label": "Tokens",
                "short": "tokens",
                "used": None,
                "reset_ms": None,
                "cutoff_ms": None,
                "window_ms": None,
                "signal": "normal",
                "state": "unknown",
                "projected": None,
            }
        )
    return entries


def windows_summary(view: Dashboard) -> list[dict[str, object]]:
    """Every quota window ranked by urgency, then token-only providers with unknown limits."""
    entries: list[dict[str, object]] = []
    for quota, window, tag in _w_ranked(view):
        pace = window.pace
        state = _w_state(window)
        used = window.used_percent
        if used is None and state == "exhausted":
            used = 100.0
        projected = pace.projected_percent if pace is not None else None
        entries.append(
            {
                "provider": quota.provider,
                "account": tag,
                "label": _joined(tag, _window_label(window, quota.provider)),
                "short": _w_label(quota, window),
                "used": round(used, 1) if used is not None else None,
                "reset_ms": window.reset_ms,
                "cutoff_ms": view.now_ms + pace.exhaust_in_ms if pace is not None and pace.exhaust_in_ms is not None else None,
                "window_ms": window.window_ms,
                "signal": window_signal(window, view.now_ms),
                "state": state,
                "projected": round(projected, 1) if projected is not None else None,
            }
        )
    entries.extend(_token_only_windows(view))
    return entries


def recent_summary(view: Dashboard) -> list[dict[str, object]]:
    """Latest activity first, enough rows for the detail history."""
    return [
        {
            "provider": record["provider"],
            "model": record["model"],
            "project": record["project"],
            "title": record["title"],
            "at_ms": record["at_ms"],
            "tokens": record["tokens"],
        }
        for record in sorted(view.recent, key=lambda record: record["at_ms"], reverse=True)[:_RECENT_LIMIT]
    ]
