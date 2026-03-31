"""YAML config loader for statusline."""
from __future__ import annotations

from pathlib import Path

import yaml

from resolve import resolve_path

RESET = "\033[0m"
BLANK = "\u2800"
CLEAR_EOL = "\033[K"
CLEAR_LINE = "\033[2K"

_PLUGIN_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PLUGIN_DIR / "statusline.yml"
_THEMES_DIR = _PLUGIN_DIR / "themes"
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _cache = yaml.safe_load(f)
    return _cache


def _load_themes() -> dict:
    themes: dict = {}
    if _THEMES_DIR.is_dir():
        for p in sorted(_THEMES_DIR.glob("*.yml")):
            with open(p, encoding="utf-8") as f:
                themes[p.stem] = yaml.safe_load(f)
    return themes


def _read_theme(cfg: dict) -> str:
    """Read theme name from config-driven theme_file path, falling back to 'default'."""
    theme_raw = cfg.get("theme_file")
    if not theme_raw:
        return "default"
    theme_path = resolve_path(_PLUGIN_DIR, theme_raw)
    try:
        return theme_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "default"


CONFIG = _load()
CONFIG["themes"] = _load_themes()

# Theme merging: resolve colors from the selected theme
_theme_name = _read_theme(CONFIG)
_themes = CONFIG.get("themes", {})
if _theme_name in _themes:
    CONFIG["theme"] = _theme_name
    CONFIG["colors"] = _themes[_theme_name].get("colors", {})
    CONFIG["bar"] = {**CONFIG.get("bar", {}), **_themes[_theme_name].get("bar", {})}
    CONFIG["labels"] = _themes[_theme_name].get("labels", {})
else:
    CONFIG["theme"] = _theme_name

# Resolve ansi_map names -> ANSI codes in colors
_ansi_map = CONFIG.get("ansi_map", {})
if _ansi_map and "colors" in CONFIG:
    CONFIG["colors"] = {k: _ansi_map.get(v, v) for k, v in CONFIG["colors"].items()}


def _validate(config: dict) -> None:
    """Warn on missing critical config keys (non-fatal)."""
    import warnings
    required = ("lines",)
    for key in required:
        if key not in config:
            warnings.warn(f"statusline config missing required key: {key}")
    if config.get("theme") and config["theme"] not in config.get("themes", {}):
        warnings.warn(f"statusline theme '{config['theme']}' not found in themes")


_validate(CONFIG)


def get_terminal_width() -> int:
    """Return terminal width from config (auto -> detect, capped by max_width)."""
    import os
    tw = CONFIG.get("terminal_width", "auto")
    max_w = CONFIG.get("max_width")
    if tw != "auto":
        w = int(tw)
    else:
        try:
            w = os.get_terminal_size().columns
        except (ValueError, OSError):
            w = 120
    if max_w:
        w = min(w, int(max_w))
    return w
