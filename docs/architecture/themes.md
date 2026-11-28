# Themes

A theme is a directory under `resources/themes/<name>/`:

- `palette.json` — named colours used by the stylesheet.
- `style.qss` — Qt stylesheet with `@@key@@` placeholders.
- `file_styles.json` — optional per-extension colours for the file views.

`ThemeManager.apply_theme` loads the palette, replaces every `@@key@@`
placeholder with the palette value and applies the result to the
`QApplication`. A placeholder without a palette key is logged as an error, and
`tests/unit/test_theme_menu_style.py` fails the build for it.

## Menu contract

An open menu has to stand out from the window chrome:

- `menu_background` is lighter than `background` (toolbar, status bar) and
  `alternate_background` (file panel rows).
- `menu_border` is visibly different from `menu_background`, so the menu has a
  clear outline.
- `QMenu` uses `menu_background` and `menu_border`.
- `QMenu::item:selected` uses `selection_background` and
  `selection_foreground`.
- `QMenu::item:disabled` uses `disabled_foreground`.

In the light theme white is the lightest available colour, so the menu
background is `#FFFFFF` and the border provides the separation from the white
file panels.

## Adding a theme

Create the directory, provide `palette.json` with every key used by
`style.qss`, and run `python -m pytest tests/unit/test_theme_menu_style.py`.
