"""ANSI rendering helpers: colors, bars, left/right line layout."""
from __future__ import annotations

import re
import unicodedata

from config import BLANK, CLEAR_EOL, CONFIG, RESET

_ANSI_RE = re.compile(r"\033\[[0-9;]*[A-Za-z]|\033]8;[^\a]*\a")


def c(code: str) -> str:
    return f"\033[{code}m"


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences and OSC 8 hyperlinks for visible-width measurement."""
    return _ANSI_RE.sub("", s)


def link(url: str, text: str) -> str:
    """Wrap text in an OSC 8 clickable hyperlink. Degrades to plain text in unsupported terminals."""
    return f"\033]8;;{url}\a{text}\033]8;;\a"


# Subset of Unicode Emoji_Presentation characters in BMP
# that render 2-wide without needing FE0F
_EMOJI_DEFAULT_WIDE = frozenset({
    0x231A, 0x231B, 0x23E9, 0x23EA, 0x23EB, 0x23EC, 0x23F0, 0x23F3,
    0x25FD, 0x25FE, 0x2614, 0x2615, 0x2648, 0x2649, 0x264A, 0x264B,
    0x264C, 0x264D, 0x264E, 0x264F, 0x2650, 0x2651, 0x2652, 0x2653,
    0x267F, 0x2693, 0x26A1, 0x26AA, 0x26AB, 0x26BD, 0x26BE, 0x26C4,
    0x26C5, 0x26CE, 0x26D4, 0x26EA, 0x26F2, 0x26F3, 0x26F5, 0x26FA,
    0x26FD, 0x2705, 0x270A, 0x270B, 0x2728, 0x274C, 0x274E, 0x2753,
    0x2754, 0x2755, 0x2757, 0x2795, 0x2796, 0x2797, 0x27B0, 0x27BF,
    0x2B1B, 0x2B1C, 0x2B50, 0x2B55,
})


def visible_width(s: str) -> int:
    """Display width accounting for wide characters, ZWJ sequences, FE0F, and emoji-default BMP chars."""
    text = strip_ansi(s)
    w = 0
    prev_was_zwj = False
    prev_narrow = False
    for ch in text:
        cp = ord(ch)
        if cp == 0xFE0F:
            if prev_narrow:
                w += 1  # upgrade narrow char to 2-wide emoji
                prev_narrow = False
            continue
        if cp == 0xFE0E:
            continue
        if cp == 0x200D:
            prev_was_zwj = True
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("M"):
            continue
        if prev_was_zwj:
            prev_was_zwj = False
            continue  # part of ZWJ sequence, already counted
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("W", "F") or cp >= 0x10000 or cp in _EMOJI_DEFAULT_WIDE:
            w += 2
            prev_narrow = False
        else:
            w += 1
            prev_narrow = True
    return w


def render_bar(fraction: float) -> str:
    bar = CONFIG.get("bar", {})
    w = bar.get("width", 20)
    fill, empty = bar.get("fill", "\u2588"), bar.get("empty", "\u2591")
    left, right = bar.get("left", "["), bar.get("right", "]")
    filled = max(0, min(w, int(fraction * w)))
    return left + fill * filled + empty * (w - filled) + right


def tier_color(pct: float, prefix: str = "context") -> str:
    colors = CONFIG.get("colors", {})
    if pct >= 90:
        return colors.get(f"{prefix}_crit", "1;31")
    if pct >= 70:
        return colors.get(f"{prefix}_warn", "1;33")
    return colors.get(f"{prefix}_ok", "1;32")


def format_token_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_cost(amount: float) -> str:
    if amount <= 0:
        return ""
    return f"${amount:.2f}"


def format_duration(ms: float) -> str:
    s = int(ms / 1000)
    if s < 60:
        return f"{s}s"
    m = s // 60
    if m < 60:
        return f"{m}m"
    h = m // 60
    return f"{h}h{m % 60:02d}m"


def format_relative_time(epoch: float) -> str:
    """Format a Unix epoch timestamp as relative time from now (e.g., '4h12m', '5d8h')."""
    import time
    delta = int(epoch - time.time())
    if delta <= 0:
        return "now"
    if delta < 60:
        return f"{delta}s"
    m = delta // 60
    if m < 60:
        return f"{m}m"
    h = m // 60
    if h < 24:
        return f"{h}h{m % 60:02d}m"
    d = h // 24
    return f"{d}d{h % 24}h"


def render_line(left_tpl: str, right_tpl: str | None, tokens: dict[str, str], width: int, *, space: str = " ") -> str | None:
    """Substitute tokens, pad left/right to fill width. Return None if visually empty."""
    def _substitute(tpl: str) -> str:
        result = tpl
        for key, val in tokens.items():
            result = result.replace(f"{{{key}}}", val)
        return result

    left = _substitute(left_tpl)
    right = _substitute(right_tpl) if right_tpl else ""

    # Intentional spacer lines (e.g. raw \u2800 in template) always render
    intentional_spacer = BLANK in left_tpl or (right_tpl and BLANK in right_tpl)

    # Check if visually empty
    if not intentional_spacer:
        combined = left + right
        stripped = combined.replace(RESET, "").replace(BLANK, "").strip()
        if not _ANSI_RE.sub("", stripped):
            return None

    # Measure visible widths
    left_vis = visible_width(left)
    right_vis = visible_width(right)

    if right_vis > 0:
        gap = max(1, width - left_vis - right_vis)
        return left + space * gap + right + CLEAR_EOL
    return left + CLEAR_EOL
