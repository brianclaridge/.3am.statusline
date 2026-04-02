# Fix: Dogfood statusline plugin by pointing --plugin-dir at project root

## Context

When running `task claude` to dogfood the statusline plugin on itself, Claude Code fails with:
```
commands path not found: D:\..\.3am.statusline\.claude\statusline
```

**Root cause:** Taskfile.yml line 38 passes `--plugin-dir {{.TASKFILE_DIR}}/.claude/statusline`, but `.claude/statusline/` doesn't exist. The plugin IS the project root — its `.claude-plugin/plugin.json`, `skills/`, `agents/`, and `src/` all live at the repo root, not nested under `.claude/`.

For comparison, the tts-agent plugin works because it's installed as a git submodule at `.claude/tts-agent/` — a real directory with its own `.claude-plugin/plugin.json`.

## Fix

**File:** `Taskfile.yml` line 38

Change:
```yaml
--plugin-dir {{toSlash .TASKFILE_DIR}}/.claude/statusline
```
To:
```yaml
--plugin-dir {{toSlash .TASKFILE_DIR}}
```

This points `--plugin-dir` at the project root, where Claude Code will find `.claude-plugin/plugin.json` and discover the plugin's skills, agents, and source.

## Verification

1. Run `task claude` — should launch without the "commands path not found" error
2. Verify the statusline renders in the terminal
3. Verify `/statusline:theme` and `/statusline:upgrade` skills are discoverable
