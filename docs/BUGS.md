# Bugs

## Known Issues

- **Translation**: Some parts of the UI are not yet translated.
- **Windows**: Compatibility issues, especially with file paths and permissions.

## Fixed

- **Hanging selection with Insert**: Fixed an issue where files selected with the Insert key were not cleared after an operation, causing
  errors on subsequent actions.
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
