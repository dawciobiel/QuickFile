# Changelog

All notable changes to this project will be documented in this file.

## [0.16.0] - 2026-01-10

### Added
- **Transfer Speed Display**: Implemented transfer speed calculation and display in Copy/Move dialogs and Task Queue.
- **Smooth Overall Progress**: Improved Overall Progress calculation to be byte-based for smoother updates.
- **Open Terminal**: Added "Open Terminal Here" and "Open Admin Terminal Here" functionality to the main menu and context menu.
- **Terminal Configuration**: Added settings to configure default and custom terminal commands.
- **Unit Tests**: Added extensive unit tests for `FileManager`, `SettingsManager`, `ThemeManager`, `FavoritesManager`, and `ApplicationLogicHandler`.
- **Documentation Structure**: Reorganized documentation into `user_guide`, `developer_guide`, and `project_management` directories.

### Fixed
- **Plugin Loading**: Fixed several issues related to plugin discovery, versioning, and handling of broken plugins.
- **UI Rendering**: Fixed rendering issues with the `DualProgressBar`.
- **License Headers**: Added missing license headers to all plugin source files.

## [0.15.1] - 2025-12-25

### Added
- **Action Logger**: Created `ActionLogger` to record user actions for debugging.
- **Action Replay**: Implemented `scripts/replay_actions.py` to replay anonymized logs.

### Fixed
- **Multi-file Operations**: Fixed a bug where only one file was copied/moved when multiple were selected.
- **Background Task Management**: Implemented pause, resume, and cancel functionality for background tasks.
- **UI Stability**: Fixed numerous `AttributeError` and a critical `SIGSEGV` crash on exit.
- **Tab Management**: Implemented full support for multiple tabs, including saving and restoring them.
- **Favorites**: Renamed "Bookmarks" to "Favorites" and added a "Delete" button.
- **External Editors**: Added settings to configure custom commands for F3 (View) and F4 (Edit).
