# .3am.statusline

ANSI-colored terminal status line for Claude Code. Model, cost, context, git, rate limits. 5 themes.

## Install

```bash
# load as plugin (enables /statusline:theme skill)
claude --plugin-dir /path/to/.3am.statusline
```

Add to your `settings.json` (or `.claude/settings.json`):

```json
{
  "statusLine": {
    "type": "command",
    "command": "cd /path/to/.3am.statusline && uv run src/statusline.py",
    "padding": 2
  }
}
```

Replace `/path/to/statusline` with the absolute path to this directory.

## Themes

5 built-in themes: `default`, `dracula`, `gruvbox`, `nord`, `tokyo`

```bash
/statusline:theme              # interactive picker (requires --plugin-dir)
uv run src/set_theme.py        # list themes
uv run src/set_theme.py tokyo  # set directly
```

## Test

```bash
cat example.json | uv run src/statusline.py
```
