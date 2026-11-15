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
- **Directory size calculation has no plugin**: `ApplicationLogicHandler.calculate_directory_size` creates
  a `TaskType.CALCULATE_SIZE` task without `plugin_id`, and no bundled plugin implements that action.
  The task fails with "requires a 'plugin_id'". The feature needs a real implementation (it can live in
  `disk_utils_standard`) or the menu entry should be removed.

## Fixed

### Task queue (2026-11-16)

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
