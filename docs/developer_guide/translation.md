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

The script scans Python sources for literal `translation_manager.translate(...)` calls and
prints keys missing from each language file plus keys that no longer appear in code. The
report is informational and covers the whole project.

The plugin management page is guarded by
`tests/unit/test_plugin_management_translations.py`, which fails when a string from that
page has no key in `en_US.json` or `pl_PL.json`, when the English value differs from the
source text, or when the two language files diverge.
