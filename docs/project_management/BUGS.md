# Bugs

## Known Issues

- **Translation**: Some parts of the UI are not yet translated.
- **Windows**: Compatibility issues, especially with file paths and permissions.

## TODO

- Open terminal in the current path.
- Open terminal in the current path with admin rights.
- Relaunch QuickFile with admin rights.
- Create unit tests.
- Create integration tests.
- Plugin management from the UI level: A window to enable/disable installed plugins.
- Plugin for handling other archive formats (e.g., 7z, RAR for packing).
- FTP/SFTP client plugin.
- Plugin for integration with a cloud API (e.g., Dropbox, Google Drive).

## Fixed

### Viewer (`standard_viewer`)

- **Focus Issues**: Fixed a bug where the viewer window would not get focus upon opening.
- **Rendering Artifacts**: Fixed horizontal lines appearing in the code view by synchronizing widget background with the Pygments style.
- **Missing Toolbar Buttons**: Fixed an issue where some view mode buttons (HEX, DEC) were not visible on the toolbar.
- **Incorrect Dialog Parenting**: Fixed a bug where opening the "Properties" dialog from the viewer would cause the main window to
  incorrectly come to the foreground.
- **Incorrect Default Mode**: Fixed an issue where `.txt` files were incorrectly opened in "Code" mode instead of "Text" mode.

### General
- **Plugin Initialization Order**: Fixed a bug where UI extension plugins were initialized before the main UI was fully built, preventing them from adding elements to the menu.
- **Plugin Internal Imports**: Fixed a `ModuleNotFoundError` for plugins with internal dependencies by modifying `sys.path` during the loading process in `PluginManager`.
- **`TypeError` in `findChildren`**: Fixed a `TypeError` in the feedback plugin caused by passing a string (`"QMenu"`) instead of a type (`QMenu`) to `findChildren`.
- **Disabled Widget Styling**: Fixed an issue where disabled widgets were not visually "grayed out" by adding styles for the `:disabled` state to the application's QSS files.
- **Plugin Loading Error**: Fixed `KeyError: 'id'` during plugin loading by adding missing 'id' fields to all `metadata.json` files.
- **Blank Window on Startup**: Fixed an issue where the application would start with an empty window if panel settings were corrupted or empty. Added a fallback to default tabs.
- **Hanging selection with Insert**: Fixed an issue where files selected with the Insert key were not cleared after an operation, causing errors on subsequent actions.
- **Queue Panel Issues**:
    - Fixed tasks disappearing from the queue panel.
    - Fixed progress bars not updating.
    - Fixed column resizing being disabled.
- **No column resize in Queue**: Fixed by setting the resize mode to Interactive.
- **Space in external command**: Fixed an issue where external commands (F3/F4) would fail if the filename contained spaces and the command template was not quoted.
- **`AttributeError` on startup**: Multiple `AttributeError` issues related to `MenuPanel` and `UIManager` have been fixed.
- **`TypeError` in 'Change Owner' dialog**: Fixed by setting layout stretch programmatically.
- **`metaclass conflict`**: Resolved by creating a custom metaclass for `AbstractFileSystemModel`.
- **`ImportError` for `FileStyleRole`**: Fixed by moving the definition to `styling_delegate.py`.
- **`NameError` for `TaskType`**: Added missing import in `folder_browser.py`.
- **Broken shortcuts for Favorites**: Corrected action IDs in `ShortcutsManager`.
- **UI Freeze**: Long-running operations (copy, move, delete) can freeze the UI.
