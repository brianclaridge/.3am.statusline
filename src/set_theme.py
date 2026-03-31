"""Switch the active statusline theme."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from config import CONFIG
from resolve import resolve_path

_PLUGIN_DIR = Path(__file__).resolve().parent.parent
_THEMES_DIR = _PLUGIN_DIR / "themes"
_THEME_FILE = resolve_path(_PLUGIN_DIR, CONFIG["theme_file"])


def _discover_themes() -> dict:
    themes: dict = {}
    if _THEMES_DIR.is_dir():
        for p in sorted(_THEMES_DIR.glob("*.yml")):
            with open(p, encoding="utf-8") as f:
                themes[p.stem] = yaml.safe_load(f)
    return themes


def _read_active() -> str:
    try:
        return _THEME_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "default"


def list_themes() -> None:
    active = _read_active()
    themes = _discover_themes()
    print("Available themes:")
    for name in themes:
        marker = " (active)" if name == active else ""
        print(f"  {name}{marker}")


def set_theme(name: str) -> None:
    themes = _discover_themes()
    if name not in themes:
        print(f"Error: theme '{name}' not found.", file=sys.stderr)
        print(f"Available: {', '.join(themes)}", file=sys.stderr)
        sys.exit(1)

    _THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    _THEME_FILE.write_text(name + "\n", encoding="utf-8")
    print(f"Theme set to: {name}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        list_themes()
        return
    set_theme(args[0])


if __name__ == "__main__":
    main()
