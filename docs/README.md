# QuickFile

QuickFile is a modern, cross-platform file manager designed for developers and power users. It focuses on performance, extensibility through
plugins, and a highly configurable user interface.

## Features

- **Dual-Panel Interface**: Classic two-panel layout for efficient file management.
- **Tabs**: Use multiple tabs in each panel to navigate different folders simultaneously.
- **Extensible via Plugins**:
    - **Archive Management**: Handles ZIP (create and extract) and RAR (extraction only) archives.
    - **Checksum Calculation**: Supports various algorithms (MD5, SHA-256, etc.).
    - **Advanced File Attributes**: Edit file owner/group on Linux systems.
    - **File Viewer**: Built-in viewer with text and hex modes.
- **Background Task Manager**: All file operations (copy, move, delete, sync) run in the background, keeping the UI responsive.
    - Progress tracking with pause, resume, and cancel support.
    - Dual-color progress bar showing read/write progress.
- **Customizable UI**:
    - **Configurable Toolbar**: Customize the layout and visibility of the toolbar via a JSON config.
    - **Themes**: Supports light and dark themes.
    - **Configurable Shortcuts**: Modify keyboard shortcuts to your preference.
- **Directory Synchronization**: Synchronize the contents of two directories.
- **Action Logging & Replay**: Anonymously logs user actions for easy debugging and provides a replay script to reproduce issues.

## Quick Start

On Linux the environment is defined by `flake.nix`:

1. Enter the development shell:
   `direnv allow` (or `nix develop`)
2. Run the application:
   `python main.py`

Do not create a virtual environment or run `pip install` on Linux with Nix. On Windows and
macOS, `requirements.txt` is the secondary dependency path:

1. `python -m venv .venv`
2. Activate it and run `pip install -r requirements.txt`
3. Run `python main.py`

See [the environment guide](developer_guide/environment.md) for details.

## Contributing

Please read `contributing.md` for details on our code of conduct and the process for submitting pull requests.
