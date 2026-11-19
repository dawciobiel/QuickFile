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
`translate(...)` call in `app/`, `ui/`, `utils/`, `browser/`, `panels/`, `plugins/` and
`plugins-external/`, adds the runtime-built strings listed above, and fails when:

*   a key is missing or empty in `en_US.json` or `pl_PL.json`,
*   the `en_US.json` value differs from the source text,
*   a `{placeholder}` from the source text is absent from the translation,
*   the two language files have different key sets.

Strings assembled from variables (`f"..."` with a runtime value) or passed in from data
cannot be checked statically. Build them from a fixed, listed set of keys instead of
interpolating into the lookup key.

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
