"""Config path resolution for Claude Code plugin paths."""
from __future__ import annotations

from pathlib import Path


def resolve_path(project_dir: Path, raw: str) -> Path:
    """Resolve a config path to absolute. Handles both absolute and relative results."""
    p = Path(raw)
    return p if p.is_absolute() else project_dir / p
