# Bugs

## Known Issues

- **Translation**: Host `.ui` texts, bundled plugin `.ui` texts, status-bar messages,
  messages with runtime values, standard dialog captions/messages and the Properties
  dialog are translated. `tests/unit/test_translations.py` enforces the lookup keys, the
  plugin `.ui` coverage, literal `setText`/`showMessage` arguments, plain
  `QMessageBox`/`QInputDialog`/`QFileDialog` strings, the editor window title, messages
  raised by host actions, plugin menu labels, Plugin Management and plugin update errors,
  and that no `translate` key is built from an f-string (such a key never matches JSON).
  What remains: plugin names in the archive format selector and plugin settings title, and
  the labels Qt adds to standard buttons (the app installs no `QTranslator`, so
  `Save`/`Cancel` stay English).
- **Windows**: Compatibility issues, especially with file paths and permissions.
- **Error message**: During launching application under Garuda occur error message: 
  `/run/media/dawciobiel/4cb3e6fb-e74b-4ce8-b6db-d2f6943a2697/home/dawciobiel/PyCharmProjects/QuickFile`
  Application is located on NixOS partition:
  `Permission denied to access directory: /home/dawciobiel/PycharmProjects/QuickFile/resources/icons`

## Fixed

### Editor (2026-11-16)

- **The built-in editor had no minimise/maximise buttons and blocked the app**:
  `org.quickfile.standard_editor` opened a modal `QDialog` with `exec()`, so the window
  could not be minimised or maximised and the main window waited for it. It now uses
  `EditorWindow` (`QMainWindow`, `WindowMinMaxButtonsHint`) shown non-modally, like the
  file viewer. The plugin keeps one window per absolute path in `open_editors` and raises
  the existing window when the same file is opened again. Closing with unsaved changes
  asks `Save` / `Discard` / `Cancel`; `Save` still writes and closes, and `Cancel` keeps
  the window open. `EditorWidget.has_unsaved_changes()` reads
  `QTextDocument.isModified()`, which a successful `save_file()` now clears. Closed
  windows are removed from the registry and deleted. Covered by
  `tests/unit/test_standard_editor_window.py`.

### Delete (2026-11-16)

- **"Move to Trash" was ignored on Linux**: `DeleteDialog` sends `move_to_trash=True` by
  default, but `org.quickfile.delete_operation` ignored the option and always called
  `os.remove`/`os.rmdir`; `send2trash` was only used by the Windows-only plugin. Files the
  user expected in the Trash were deleted permanently. The task now moves items with
  `send2trash` when `move_to_trash` is set. If the platform cannot create a Trash (for
  example an external partition without write access at its root), it raises
  `TrashUnavailableError` **before deleting anything**, and the error tells the user to
  uncheck "Move to Trash". The dialog also offers "Delete permanently if the Trash is
  unavailable" (`permanent_fallback`); when ticked, the plugin logs a warning and deletes
  that item permanently instead of aborting. Covered by
  `tests/unit/test_delete_operation_trash.py` and `tests/unit/test_delete_dialog_options.py`.
- **Deleting a symlink to a directory destroyed the target's contents**:
  `os.path.isdir()` follows symlinks, so the task walked the target, deleted its files and
  then failed on `os.rmdir()` of the link. Nested symlinked directories hit the same
  `rmdir` path. Deletion now treats symlinks as leaves (`os.path.islink`/`os.remove`) and
  uses `os.path.lexists` so broken links are removed too. The target is never entered.

### File browser (2026-11-16)

- **Pasting a path produced a doubled leading slash**: `Ctrl+V` did reach the path
  field (the global key filter is installed on the file view, not on the path edit,
  and `Ctrl+L` selects the whole path), but typing `/` and then pasting an absolute
  path left `//some-path`, which was then rejected as an invalid directory. The field
  now collapses a run of leading separators after every user edit, and `Enter`
  normalises repeated separators before validating the path, so `//tmp//x` navigates
  to `/tmp/x`. `..` is not resolved, so paths through symlinks keep their meaning,
  and a UNC prefix is preserved on Windows. Covered by
  `tests/unit/test_path_edit.py`.

- **"Could not get current theme data" warning on every launch**: `FlatFileSystemModel.__init__`
  calls `on_theme_changed()`, but `main.py` applies the saved theme only after `MainWindow`
  (and its file views) is built, so `ThemeManager.current_theme_data` is still empty at that
  point. The model correctly starts with empty styles and reloads them through `theme_changed`
  when the theme is applied, so the empty state is expected — it is now logged at debug level
  instead of warning. Covered by `tests/unit/test_flat_view_theme.py`.

- **Insert skipped rows when pressed quickly**: `FlatFileView.handle_key_event` toggled the
  current row and then deferred the cursor move with `QTimer.singleShot(10, ...)`. Presses
  arriving before the timer fired toggled the same row again (removing the mark) and both
  callbacks computed their target from the same, unchanged current row, so the cursor moved
  down while nothing was marked. The move is now synchronous: every keypress marks the row
  that is current at that moment and advances the cursor immediately. Covered by
  `tests/unit/test_flat_view_insert_navigation.py`.

### Task queue (2026-11-16)

- **Calculator of directory size was wired to nothing**: `ApplicationLogicHandler.calculate_directory_size`
  created a `TaskType.CALCULATE_SIZE` task without `plugin_id`, and no bundled plugin implemented
  `calculate_directory_size`, so every attempt failed with "requires a 'plugin_id'". It was first fixed
  in-process (the queue ran `FileManager.calculate_directory_size` like `SYNC`), then moved to the
  plugin it belongs to: the sandboxed `org.quickfile.directory_size`
  (`TaskPlugin` + `PluginTask`), mapped by `PLUGIN_ID_BY_ACTION["calculate_directory_size"]`.
  The plugin owns the two-pass `os.walk`, reports progress via `ctx.progress()` and cancels through
  `ctx.check_cancelled()`; replacing it only requires another plugin that declares the same action.
  Covered by `tests/unit/test_directory_size_plugin.py`, including a run over the real protocol.

- **Resuming a paused task raised `AttributeError`**: `BackgroundTaskManager.resume_task`
  read `self.active_tasks` (that mapping lives in `TaskQueueManager`) and an
  unimported `TaskStatus`, so `TaskQueueManager.resume_task` — the path behind the
  pause/resume button — crashed after a task had been paused. Pause worked because
  it only touched the task context. `resume_task` now delegates to
  `TaskContext.resume()` like `pause_task` delegates to `pause()`, which forwards
  to `SandboxedPluginWrapper.resume_task` and wakes a worker blocked in
  `wait_if_paused()`. Covered by `tests/unit/test_background_task_manager.py`,
  including the queue path and the blocked-worker wake-up.

### Plugin runtime (2026-11-15)

- **Sandboxed plugins aborted the interpreter on exit**: with plugin processes still
  running, the IPC listener thread logged and emitted Qt signals while Python was
  finalizing. Writing to an already closed stream raised
  `Fatal Python error: _enter_buffered_busy` and the process died with `SIGABRT`
  (exit 134), so the real exit code — and, in CI, the whole test report — was lost.
  A destroyed wrapper produced `RuntimeError: wrapped C/C++ object ... has been
  deleted` in the same thread. The host now logs through `_safe_log()` (skips
  `sys.is_finalizing()`, swallows closed-stream errors), emits through `_emit()`
  (tolerates a deleted QObject) and contains unexpected listener exceptions.
  The application itself was already ordering shutdown from
  `QApplication.aboutToQuit`; the fix covers exits that bypass it.
- **`pytest` collected a manual script and leaked eight plugin processes**: with
  `pytest.ini` pointing at the project root, `scripts/test_plugin_dependencies.py`
  was collected as a test. It asserts nothing and never called
  `manager.shutdown()`, so eight plugin processes and their IPC threads survived
  into the rest of the session — the trigger for the abort above. `testpaths = tests`
  now scopes plain `pytest` to the real suite, and the script shuts the manager
  down in a `finally` block so running it by hand exits cleanly too.
- **ZIP cancellation test raced the archive**: it created 1000 tiny files and slept
  50 ms before cancelling. On a fast runner the archive finished first and the test
  failed with "Task finished successfully instead of being cancelled" while the
  runtime was correct. It now builds 32 MB of incompressible data and cancels only
  after the plugin reports progress, so the task is provably still writing.

### File operations (2026-11-15)

- **Copy/move/delete failed with "Plugin not found"**: the dialogs stored the plugin *type*
  (`org.quickfile.standard_operations`) in `options["plugin_id"]`, but a task needs the plugin
  *id* (`org.quickfile.copy_operation`, `...move_operation`, `...delete_operation`). The queue
  now falls back to the bundled plugin that implements the task's action and logs a warning,
  and the dialogs use the new `app/plugin_ids.py` constants instead of string literals.

### Build, environment and plugins (2026-11-14)

- **Plugin loading ran `pip install`**: `PluginDependencyManager` installed declared
  dependencies into the plugin's `libs/` directory during startup. That required network
  access, changed the runtime environment silently and made tests hang. Loading now only
  checks dependencies; installation is an explicit action.
- **Plugin attribute lookup froze the caller for 10s**: `SandboxedPluginWrapper.__getattr__`
  answered every name with a synchronous RPC. The plugin process now reports its public
  methods in a `READY` message and unknown names raise `AttributeError` immediately.
- **Wheel was unusable**: it shipped no `.ui` files, icons, themes, translations or plugin
  modules. Runtime data now lives in the `resources` package and is declared as
  package-data; plugins are shipped as data because their directories are not importable
  packages.
- **Environment was unreproducible**: Nix, direnv, a virtualenv and pip were mixed, and
  `requirements.txt` pinned the project to an old commit. The flake is now the single
  source of truth on Linux; pip files remain as a documented secondary path.

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
