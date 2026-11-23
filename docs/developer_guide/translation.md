## Translation Workflow

Translations are flat JSON dictionaries in `resources/translations/`:

*   `en_US.json` — source language; its values must match the English text used in code.
*   `pl_PL.json` — Polish translation.

Both files must contain the same keys. There is no compilation step and no `.ts`/`.qm`
file: `TranslationManager` loads the JSON file for the selected locale at startup.

### Adding a string

Use `translation_manager.translate` with a context and the English text:

```python
from app.translation_manager import translation_manager

translation_manager.translate("PluginManagement", "Check for updates")
```

The lookup key is `Context.Text`, so the example needs the key
`PluginManagement.Check for updates` in both language files. When a key is missing,
the English text is returned unchanged — the UI still works, but the string stays
untranslated in every non-English locale.

Rules:

*   Add the key to **both** files in the same change.
*   The `en_US.json` value must equal the source text exactly.
*   The Polish value must be non-empty; keep placeholders such as `{plugin}` unchanged.
*   Strings built at runtime (for example status labels) must be listed explicitly, as
    `utils/plugin_management_page.py` does with `STATUS_LABELS`, so coverage can be checked.

### Checking coverage

```bash
python scripts/check_translations.py
```

The script scans Python sources with a single-line regular expression and prints keys
missing from each language file plus keys that no longer appear in code. It only sees
`translation_manager.translate("...", "...")` written on one line, so multi-line calls and
runtime-built keys show up as false positives; use it as a rough report, not as a gate.

Coverage is enforced by `tests/unit/test_translations.py`. It parses every literal
`translate(...)` call in `app/`, `file_operations/`, `favorites/`, `ui/`, `utils/`,
`browser/`, `panels/`, `plugins/` and `plugins-external/`, adds the runtime-built strings
listed above, and fails when:

*   a key is missing or empty in `en_US.json` or `pl_PL.json`,
*   the `en_US.json` value differs from the source text,
*   a `{placeholder}` from the source text is absent from the translation,
*   the two language files have different key sets.

Strings assembled from variables (`f"..."` with a runtime value) or passed in from data
cannot be checked statically. Build them from a fixed, listed set of keys instead of
interpolating into the lookup key.

### Texts set at runtime

Four tests fail when code hands a widget a plain literal instead of a translation:

*   `test_literal_widget_texts_are_translated` checks the first argument of `setText(...)`,
*   `test_literal_status_bar_messages_are_translated` checks `showMessage(...)`,
*   `test_dialog_strings_are_translated` checks every text argument of `QMessageBox`,
    `QInputDialog` and `QFileDialog` (the first argument is the parent widget),
*   `test_host_error_messages_are_translated` checks the message of a `raise` in host code,
    because the error handler shows it in a dialog. `INTERNAL_ERROR_MODULES` lists the
    internal modules whose exceptions never reach a dialog (`action_replayer`,
    `plugin_updater`, `external_tools`, `plugin_system/*`, `plugin_task_interface`).
    Plugin Management shows installer, state, settings and dependency errors in its page,
    so those messages use `PluginInstaller`, `PluginState`, `PluginSettings` and
    `PluginDependencyManager` keys and are checked by the same test.

A fifth test, `test_translation_keys_are_not_built_at_runtime`, rejects a `translate` key
built from an f-string with placeholders. The lookup uses the whole string, so such a key
never matches the JSON file and the English text always wins:

```python
# Wrong: the key contains the file name and is never found.
translation_manager.translate("FileManager", f"Renamed to: {new_name}")
# Right: a fixed key with a placeholder.
translation_manager.translate("FileManager", "Renamed to: {name}").format(name=new_name)
```

Use `translation_manager.translate` (or a helper such as `task_queued_message`) and pass
the result to the widget. Dynamic text needs a placeholder in a fixed key:

```python
template = translation_manager.translate("StatusBar", "Task added to queue: {task}")
self.statusBar().showMessage(template.format(task=name))
```

`UNTRANSLATED_SET_TEXTS` in the test lists the few values that are symbols rather than
sentences: `""`, `"~"`, `"/"`, `".."` and `"="`.

### Texts from `.ui` files

`uic.loadUi` copies the strings from the `.ui` file verbatim, so a dialog built in Qt
Designer stays English unless it translates its widgets. After loading a host dialog,
call `translate_widgets` before setting any text from data:

```python
from app.ui_translation import translate_widgets

uic.loadUi(get_resource_path("ui/search_dialog.ui"), self)
translate_widgets(self)
```

It applies the `Ui.<text>` key to window titles, label/button/checkbox/radio texts, group
box titles, tab titles, combo box items and placeholder texts. A text without a key keeps
its original value, which is how examples such as `/path/to/source` or `e.g. py, cpp`
stay untranslated. The coverage test requires a key for every text in `ui/*.ui` except
those listed in `UNTRANSLATED_UI_TEXTS` in `tests/unit/test_translations.py`, so adding a
label to a `.ui` file means adding `Ui.<text>` to both language files.

Bundled plugins use the same helper. A plugin dialog that loads its own `.ui` file calls
`translate_widgets(self)` right after `loadUi`; a plugin that prefers explicit
`translation_manager.translate("Context", "Text")` calls needs no helper. The coverage
test accepts either form: every text in a bundled plugin's `.ui` file must be translated
explicitly in the plugin code or have a `Ui.<text>` key. Changing a plugin's files means
renaming its version directory and updating `metadata.json`; the package builder rejects
a directory whose name differs from the metadata version.

### Plugin menu labels

A plugin returns its menu entries from `get_menu_actions()`, and the label is data, not a
`translate(...)` call, so the host translates it while building the menu. `MenuPanel`
looks the label up as `PluginAction.<text>`:

```python
action = QAction(
    translation_manager.translate("PluginAction", action_info["text"]),
    self.main_window,
)
```

A label without a key keeps its original value. `test_bundled_plugin_menu_actions_are_translated`
requires a `PluginAction.<label>` key in both language files for every literal `"text"`
a bundled plugin returns, so a new plugin action means two new keys in the host language
files, not a change to the plugin.
