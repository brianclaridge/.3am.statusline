"""Statusline entry point: stdin JSON -> tokens -> render -> stdout."""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BLANK, CLEAR_EOL, CONFIG, get_terminal_width
from expr import evaluate
from git_info import get_git_info
from render import render_line
from resolve import resolve_path
from tokens import build_tokens

# Derive project root: one level up from src/
_SCRIPT_DIR = Path(__file__).resolve().parent  # src/
ROOT = _SCRIPT_DIR.parent
CACHE_PATH = resolve_path(ROOT, CONFIG.get("cache", {}).get("file", ".data/statusline-cache.json"))


def _read_transcript_slug(transcript_path: str) -> str:
    """Read the plan slug from the last entry of the session transcript."""
    if not transcript_path:
        return ""
    try:
        tp = Path(transcript_path)
        if not tp.exists():
            return ""
        with open(tp, "rb") as f:
            f.seek(0, 2)
            pos = f.tell()
            if pos == 0:
                return ""
            # Read backwards to find the last newline
            buf = b""
            while pos > 0:
                pos = max(0, pos - 4096)
                f.seek(pos)
                chunk = f.read(min(4096, f.tell() + 4096 - pos))
                buf = chunk + buf
                lines = buf.split(b"\n")
                if len(lines) > 1:
                    last_line = lines[-1] if lines[-1] else lines[-2]
                    return json.loads(last_line).get("slug", "")
            # Single line file
            return json.loads(buf).get("slug", "")
    except Exception:
        return ""


def _now_ms() -> float:
    return time.time() * 1000


def _read_git_cache() -> tuple[dict, float]:
    """Read cached git info. Returns (git_data, timestamp_ms)."""
    try:
        data = json.loads(CACHE_PATH.read_text())
        return data.get("git", {}), data.get("git_ts", 0)
    except Exception:
        return {}, 0


def _write_git_cache(git_data: dict, ts: float) -> None:
    """Write git info to cache file."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps({"git": git_data, "git_ts": ts}))
        tmp.replace(CACHE_PATH)
    except Exception:
        pass


def _detect_active_plan(data: dict) -> dict[str, str]:
    """Detect active plan from the transcript slug field (authoritative, self-contained)."""
    no_plan = {"slug": "--", "title": "no active plan"}
    transcript_path = data.get("transcript_path", "")
    slug = _read_transcript_slug(transcript_path)
    if not slug:
        return no_plan
    # Derive plan file path from the user's project dir (not plugin root)
    try:
        project_dir = data.get("workspace", {}).get("project_dir", "") or data.get("cwd", "")
        if not project_dir:
            return {"slug": slug, "title": slug}
        plans_dir = Path(project_dir) / ".claude" / "plans"
        plan_path = plans_dir / f"{slug}.md"
        title = ""
        if plan_path.exists():
            for line in plan_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        return {"slug": slug, "title": title or slug}
    except Exception:
        return {"slug": slug, "title": slug}


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    session_id = data.get("session_id", "unknown")

    # Git info with file cache
    cache_cfg = CONFIG.get("cache", {})
    git_interval = cache_cfg.get("git_interval_ms", 10000)
    cached_git, git_ts = _read_git_cache()
    now_ms = _now_ms()
    git_cache_hit = bool(cached_git and (now_ms - git_ts) < git_interval)

    # Use the user's project dir for git info, not the plugin's own dir
    project_dir = data.get("workspace", {}).get("project_dir", "") or data.get("cwd", "")
    git_root = Path(project_dir) if project_dir else ROOT

    if git_cache_hit:
        git_data = cached_git
    else:
        git_data = get_git_info(git_root)
        _write_git_cache(git_data, now_ms)

    # Detect active plan from .active-context cache
    plan_info = _detect_active_plan(data)

    width = get_terminal_width()
    tokens = build_tokens(data, CONFIG, git_data, plan_info)

    # Build flat raw values for visible_if expressions
    cost_data = data.get("cost", {})
    ctx = data.get("context_window", {})
    current = ctx.get("current_usage", {})
    rate_data = data.get("rate_limits", {})
    raw_values = {
        "session_id": data.get("session_id", ""),
        "session_name": data.get("session_name", ""),
        "model_name": data.get("model", {}).get("display_name", ""),
        "model_id": data.get("model", {}).get("id", ""),
        "version": data.get("version", ""),
        "output_style": data.get("output_style", {}).get("name", ""),
        "cwd": data.get("cwd", ""),
        "project_dir": data.get("workspace", {}).get("project_dir", ""),
        "current_dir": data.get("workspace", {}).get("current_dir", ""),
        "duration": cost_data.get("total_duration_ms", 0),
        "cost": cost_data.get("total_cost_usd", 0),
        "lines_added": cost_data.get("total_lines_added", 0),
        "lines_removed": cost_data.get("total_lines_removed", 0),
        "api_duration": cost_data.get("total_api_duration_ms", 0),
        "context_pct": ctx.get("used_percentage", 0),
        "remaining_pct": ctx.get("remaining_percentage", 0),
        "context_window_size": ctx.get("context_window_size", 0),
        "total_input": ctx.get("total_input_tokens", 0),
        "total_output": ctx.get("total_output_tokens", 0),
        "turn_input": current.get("input_tokens", 0),
        "turn_output": current.get("output_tokens", 0),
        "cache_read": current.get("cache_read_input_tokens", 0),
        "cache_creation": current.get("cache_creation_input_tokens", 0),
        "exceeds_200k": data.get("exceeds_200k_tokens", False),
        "rate_5h_pct": rate_data.get("five_hour", {}).get("used_percentage", 0),
        "rate_7d_pct": rate_data.get("seven_day", {}).get("used_percentage", 0),
        "git_branch": git_data.get("branch", ""),
        "plan": plan_info.get("slug", ""),
    }

    # Render lines
    padding = CONFIG.get("padding", 0)
    above = padding
    below = padding
    line_configs = CONFIG.get("lines", [])

    space_char = CONFIG.get("space_character", " ")
    output: list[str] = [BLANK + CLEAR_EOL] * above
    for line_cfg in line_configs:
        if isinstance(line_cfg, str):
            left_tpl = line_cfg
            right_tpl = None
        else:
            left_tpl = line_cfg.get("left", "")
            right_tpl = line_cfg.get("right")

        # Check visible_if condition
        if isinstance(line_cfg, dict):
            vis_expr = line_cfg.get("visible_if")
            if vis_expr and not evaluate(vis_expr, raw_values):
                continue

        rendered = render_line(left_tpl, right_tpl, tokens, width, space=space_char)
        if rendered is not None:
            output.append(rendered)
    output.extend([BLANK + CLEAR_EOL] * below)

    rendered_output = "\n".join(output)
    print(rendered_output)


if __name__ == "__main__":
    main()
