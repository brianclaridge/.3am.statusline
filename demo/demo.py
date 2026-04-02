"""Generate progressive statusline frames for the VHS demo recording."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import time
import os

BASE = {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "transcript_path": "/home/dev/acme-api/.transcript.jsonl",
    "cwd": "/home/dev/acme-api",
    "session_name": "my-feature",
    "model": {
        "id": "claude-opus-4-6[1m]",
        "display_name": "Opus 4.6 (1M context)",
    },
    "workspace": {
        "current_dir": "/home/dev/acme-api",
        "project_dir": "/home/dev/acme-api",
        "added_dirs": [],
    },
    "version": "2.1.88",
    "output_style": {"name": "default"},
    "cost": {
        "total_cost_usd": 0.0,
        "total_duration_ms": 0,
        "total_api_duration_ms": 0,
        "total_lines_added": 0,
        "total_lines_removed": 0,
    },
    "context_window": {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "context_window_size": 1000000,
        "current_usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "used_percentage": 0,
        "remaining_percentage": 100,
    },
    "exceeds_200k_tokens": False,
    "rate_limits": {
        "five_hour": {"used_percentage": 0, "resets_at": 0},
        "seven_day": {"used_percentage": 0, "resets_at": 0},
    },
}

# (cost, duration_s, api_s, ctx_pct, lines+, lines-, rate5h, rate7d, cwd)
# cwd=None means same as project_dir (📂 line hidden)
PROJECT = "/home/dev/acme-api"
STEPS = [
    # default theme — early session, exploring the codebase
    (0.02,    5,    3,   1,    0,   0,   1,  0, None),
    (0.08,   18,   10,   3,    4,   0,   2,  1, f"{PROJECT}/src/routes"),
    (0.15,   45,   22,   6,   12,   3,   3,  1, f"{PROJECT}/src/routes/auth"),
    (0.31,   90,   41,  10,   28,   7,   5,  2, f"{PROJECT}/src/db/migrations"),
    # dracula theme — mid session, jumping around
    (0.78,  310,   95,  22,   67,  19,  12,  4, f"{PROJECT}/tests"),
    (1.34,  620,  168,  35, 134,  38,  21,  7, f"{PROJECT}/tests/integration"),
    (2.10,  950,  255,  48, 215,  52,  33,  11, None),
    (3.20, 1400,  380,  62, 340,  85,  48,  16, f"{PROJECT}/src/middleware"),
    # tokyo theme — deep session, heavy usage
    (4.80, 2100,  520,  74, 480, 120,  65,  24, f"{PROJECT}/.claude/plans"),
    (6.50, 2800,  680,  83, 620, 155,  78,  35, f"{PROJECT}/src/routes/auth"),
    (8.40, 3600,  850,  90, 780, 195,  88,  48, None),
    (10.2, 4200, 1020,  95, 940, 240,  95,  62, f"{PROJECT}/deploy"),
]

THEMES = ["default", "dracula", "tokyo"]
FRAMES_PER_THEME = len(STEPS) // len(THEMES)

GIT_DIR = "/home/dev/acme-api"
STATUSLINE_DIR = os.environ.get("STATUSLINE_DIR", "/statusline")
PYTHON = os.path.join(STATUSLINE_DIR, ".venv", "bin", "python")
STATUSLINE = os.path.join(STATUSLINE_DIR, "src", "statusline.py")
SET_THEME = os.path.join(STATUSLINE_DIR, "src", "set_theme.py")

# Per-frame git actions run before rendering. Simulates real git activity.
GIT_ACTIONS: dict[int, list[list[str]]] = {
    # Frame 1: create feature branch
    1: [["git", "checkout", "-b", "feat/add-auth-middleware"]],
    # Frame 2: stage a file
    2: [["git", "add", "README.md"]],
    # Frame 3: commit + create new untracked files
    3: [
        ["git", "commit", "-m", "feat: add jwt validation layer"],
        ["bash", "-c", "echo 'module.exports = {}' > auth.js && echo 'test' > auth.test.js"],
    ],
    # Frame 5: stage one, leave one untracked
    5: [["git", "add", "auth.js"]],
    # Frame 6: commit, make more changes
    6: [
        ["git", "commit", "-m", "feat: auth middleware + route guards"],
        ["bash", "-c", "echo 'updated' >> README.md && echo 'config' > .env.local"],
    ],
    # Frame 8: new branch for hotfix
    8: [
        ["git", "checkout", "-b", "fix/rate-limit-headers"],
        ["bash", "-c", "echo 'patched' > hotfix.py"],
        ["git", "add", "hotfix.py"],
    ],
    # Frame 10: commit the fix, back to clean-ish
    10: [["git", "commit", "-m", "fix: include retry-after in 429 response"]],
    # Frame 11: more uncommitted work
    11: [["bash", "-c", "echo 'deploy v2' > deploy.sh && echo 'notes' > RELEASE.md"]],
}


def run_git_actions(frame_idx: int) -> None:
    actions = GIT_ACTIONS.get(frame_idx, [])
    for cmd in actions:
        subprocess.run(cmd, capture_output=True, timeout=10, cwd=GIT_DIR)


def build_frame(idx: int) -> dict:
    cost, dur_s, api_s, ctx_pct, la, lr, r5, r7, cwd = STEPS[idx]
    now = int(time.time())
    d = copy.deepcopy(BASE)
    d["cost"]["total_cost_usd"] = cost
    d["cost"]["total_duration_ms"] = dur_s * 1000
    d["cost"]["total_api_duration_ms"] = api_s * 1000
    d["cost"]["total_lines_added"] = la
    d["cost"]["total_lines_removed"] = lr
    d["context_window"]["used_percentage"] = ctx_pct
    d["context_window"]["remaining_percentage"] = 100 - ctx_pct
    d["context_window"]["total_input_tokens"] = int(ctx_pct * 10000)
    d["context_window"]["total_output_tokens"] = int(ctx_pct * 3000)
    d["rate_limits"]["five_hour"]["used_percentage"] = r5
    d["rate_limits"]["five_hour"]["resets_at"] = now + 18000
    d["rate_limits"]["seven_day"]["used_percentage"] = r7
    d["rate_limits"]["seven_day"]["resets_at"] = now + 604800
    if cwd:
        d["cwd"] = cwd
        d["workspace"]["current_dir"] = cwd
    return d


def set_theme(name: str) -> None:
    subprocess.run([PYTHON, SET_THEME, name], capture_output=True, timeout=10)


def render_frame(data: dict) -> str:
    proc = subprocess.run(
        [PYTHON, STATUSLINE],
        input=json.dumps(data),
        capture_output=True, text=True, timeout=10,
        env={**os.environ, "PYTHONPATH": os.path.join(STATUSLINE_DIR, "src")},
    )
    return proc.stdout


def main() -> None:
    HOME = "\033[H"
    CLEAR = "\033[2J"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

    sys.stdout.write(HIDE_CURSOR + CLEAR + HOME)
    sys.stdout.flush()

    current_theme = None
    for i in range(len(STEPS)):
        theme_idx = min(i // FRAMES_PER_THEME, len(THEMES) - 1)
        theme = THEMES[theme_idx]
        if theme != current_theme:
            set_theme(theme)
            current_theme = theme

        run_git_actions(i)
        data = build_frame(i)
        output = render_frame(data)

        sys.stdout.write(HOME)
        sys.stdout.write(output)
        sys.stdout.flush()
        time.sleep(1.8)

    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
