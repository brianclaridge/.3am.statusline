"""Git repository state: branch, dirty, staged, unstaged, untracked, ahead/behind."""
from __future__ import annotations

import subprocess
from pathlib import Path


def get_git_info(root: Path) -> dict:
    """Run git commands and return structured repo info."""
    info = {
        "branch": "",
        "sha": "",
        "dirty": False,
        "staged": 0,
        "unstaged": 0,
        "untracked": 0,
        "ahead": 0,
        "behind": 0,
        "remote_url": "",
    }

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5, cwd=root,
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return info

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=root,
        )
        if result.returncode == 0:
            info["sha"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, cwd=root,
        )
        if result.returncode == 0:
            staged = 0
            unstaged = 0
            untracked = 0
            for line in result.stdout.splitlines():
                if len(line) < 2:
                    continue
                x, y = line[0], line[1]
                if x == "?" and y == "?":
                    untracked += 1
                else:
                    if x not in (" ", "?"):
                        staged += 1
                    if y not in (" ", "?"):
                        unstaged += 1
            info["staged"] = staged
            info["unstaged"] = unstaged
            info["untracked"] = untracked
            info["dirty"] = (staged + unstaged + untracked) > 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5, cwd=root,
        )
        if result.returncode == 0:
            raw = result.stdout.strip()
            # Convert git@host:org/repo.git -> https://host/org/repo
            if raw.startswith("git@"):
                raw = raw.replace(":", "/", 1).replace("git@", "https://", 1)
            if raw.endswith(".git"):
                raw = raw[:-4]
            info["remote_url"] = raw
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"],
            capture_output=True, text=True, timeout=5, cwd=root,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                info["behind"] = int(parts[0])
                info["ahead"] = int(parts[1])
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    return info
