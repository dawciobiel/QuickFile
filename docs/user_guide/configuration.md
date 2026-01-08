# Configuration

This document describes the main configuration options available in QuickFile.

## Terminal

QuickFile allows you to open a terminal directly in the directory of the active panel. You can configure both a standard terminal and a terminal with administrator privileges.

### Standard Terminal

- **Use system default terminal**: When checked, QuickFile will try to open the default terminal for your operating system.
- **Custom command**: If the default option doesn't work or you prefer a different terminal, you can provide a custom command here. Use the placeholder `%d` to specify where the directory path should be inserted.

**Default Commands:**
- **Windows**: `cmd.exe /c "cd /d %d && start cmd.exe"`
- **macOS**: `open -a Terminal %d`
- **Linux**: QuickFile will try to detect `gnome-terminal`, `konsole`, or `xfce4-terminal` and use the appropriate command. The fallback is `x-terminal-emulator`.

### Admin Terminal

- **Use system default admin terminal**: When checked, QuickFile will attempt to open a terminal with administrator/root privileges. This will usually trigger a system prompt for your password.
- **Custom command**: You can provide a custom command to launch an administrative terminal.

**Default Commands:**
- **Windows**: `powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/k cd /d %d'"`
- **macOS**: `osascript -e 'do shell script "cd \\"%d\\"; open -a Terminal .\" with administrator privileges'`
- **Linux**: QuickFile will try to detect a common terminal and run it with `sudo`. For example, for `konsole`, it will use `konsole --workdir %d -e sudo -s`. If your setup requires a different command (e.g., using `pkexec` or a different terminal), you should provide it in the "Custom command" field.

**Example for Linux (if default doesn't work):**
- For `konsole`: `konsole -e "cd %d && sudo -s"`
- For `gnome-terminal`: `gnome-terminal --working-directory=%d -- bash -c "sudo -s; exec bash"`
