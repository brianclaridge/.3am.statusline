# VHS demo recording for .3am.statusline
# https://github.com/charmbracelet/vhs

Output demo.webp

Set Shell "bash"
Set FontFamily "Hack Nerd Font Mono"
Set FontSize 16
Set Width 820
Set Height 300
Set Padding 0
Set TypingSpeed 0ms
Set Theme { "name": "demo", "black": "#1a1b26", "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68", "blue": "#7aa2f7", "magenta": "#bb9af7", "cyan": "#7dcfff", "white": "#c0caf5", "brightBlack": "#414868", "brightRed": "#f7768e", "brightGreen": "#9ece6a", "brightYellow": "#e0af68", "brightBlue": "#7aa2f7", "brightMagenta": "#bb9af7", "brightCyan": "#7dcfff", "brightWhite": "#c0caf5", "background": "#000000", "foreground": "#c0caf5", "selection": "#33467c", "cursor": "#c0caf5" }

Hide
Type@0ms "cd /statusline && .venv/bin/python demo/demo.py"
Enter
Sleep 2s
Show

Sleep 24s
