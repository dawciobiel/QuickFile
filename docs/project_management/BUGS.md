# Bugs

## Known Issues

- **Bug for pasting path**: Brak możliwości wklejenia (CTRL+V) ścieżki w polu edycji ścieżki.
  - Skrót klawiszowy CTRL+V jest przypisany do innej akcji która zostaje wywoływana (prawdopodobnie jest to wklejenie katalogu lub pliku).
  - W polu edycji ścieżki jako pierwszy znak zawsze wpisany jest znak `/`. Więc jeżeli wstawiany ciąg znaków zawiera na początku np. `/some-path` to jako całość w tym polu wstawione będzie `//some-path`.
- **To add maxymize, minimalize build it editor window**: Okno pluginu wbudowanego edytora powinno mieć również możliwość minimalizacji, maksymalizacji. Obecnie jest to chyba okno dialogowe. Więc powinno zostać zmodyfikowane tak jak okno pluginu default viewer.
- **Translation**: Some parts of the UI are not yet translated.
- **Windows**: Compatibility issues, especially with file paths and permissions.
- **Error message**: During launching application under Garuda occur error message: 
  `/run/media/dawciobiel/4cb3e6fb-e74b-4ce8-b6db-d2f6943a2697/home/dawciobiel/PyCharmProjects/QuickFile`
  Application is located on NixOS partition:
  `Permission denied to access directory: /home/dawciobiel/PycharmProjects/QuickFile/resources/icons`
- **Trash Permission Error**: `send2trash` fails with `PermissionError: [Errno 13]` when deleting files from external or mounted partitions (e.g., `/run/media/...`) on Linux.
  - This happens because the user lacks write permissions to the root of the mount point where `send2trash` tries to create the `.Trash-1000` folder.
  - **Workaround**: Users should use permanent delete (Shift+Delete) for files on such partitions.
  - **Future Fix**: Implement a fallback mechanism in `StandardOperationsPlugin` to catch this error and prompt the user to permanently delete the file.

## Fixed

### Viewer (`standard_viewer`)

- **Focus Issues**: Fixed a bug where the viewer window would not get focus upon opening.
- **Rendering Artifacts**: Fixed horizontal lines appearing in the code view by synchronizing widget background with the Pygments style.
- **Missing Toolbar Buttons**: Fixed an issue where some view mode buttons (HEX, DEC) were not visible on the toolbar.
- **Incorrect Dialog Parenting**: Fixed a bug where opening the "Properties" dialog from the viewer would cause the main window to
  incorrectly come to the foreground.
- **Incorrect Default Mode**: Fixed an issue where `.txt` files were incorrectly opened in "Code" mode instead of "Text" mode.

### General

`run/media/dawciobiel/Nixos-root/@/home/dawciobiel/PyCharmProjects/QuickFile/`
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
