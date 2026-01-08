## Translation Workflow

This project uses Qt Linguist tools (`lupdate` and `lrelease`) to manage translations.  
The workflow consists of two steps: **updating** translation sources and **compiling** them into binary files.

---

### 1. Update translation sources

Run the `update_translations.sh` script to scan Python source files for new translatable strings.  
Only files containing `QCoreApplication.translate` or `self.tr()` are processed, while auxiliary directories
(`.venv`, `experiments`, `docs`, `tests`, `translations`, `logs`) are ignored.

```bash
./update_translations.sh
```

This updates the `.ts` files in the `translations` directory.  
Open them in Qt Linguist to add or update translations.

---

### 2. Compile translations

Run the `compile_translations.sh` script to compile all `.ts` files into binary `.qm` files:

```bash
./compile_translations.sh
```

The `.qm` files are generated in the `translations` directory and can be loaded by the application at runtime.

---

### Notes
- `lupdate` extracts new strings and removes obsolete ones (`-no-obsolete` flag).
- `lrelease` converts `.ts` files into `.qm` files required by Qt applications.
- Always commit both updated `.ts` and compiled `.qm` files to keep translations in sync.
- Ensure Qt tools (`lupdate`, `lrelease`) are installed and available in your PATH.
