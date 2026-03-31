---
name: theme
description: Switch the statusline color theme
argument-hint: "[theme-name]"
allowed-tools: ["Bash", "Read"]
---

# Theme Switcher

Switch the active statusline theme.

## Steps

1. If `$ARGUMENTS` is provided, run: `cd "${CLAUDE_PLUGIN_ROOT}" && uv run src/set_theme.py $ARGUMENTS`
2. If no arguments, list available themes: `cd "${CLAUDE_PLUGIN_ROOT}" && uv run src/set_theme.py`
3. Ask the user which theme they want and run set_theme.py with their choice
