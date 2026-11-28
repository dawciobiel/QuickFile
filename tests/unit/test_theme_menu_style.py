# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Theme contract for open menus.

Specification: ``docs/architecture/themes.md``.

An open menu has to stand out from the window chrome. Its background must be
lighter than the toolbar and the file panels, and a border must separate it
from the rest of the window. The colours live in ``palette.json`` and reach
``style.qss`` through ``@@placeholder@@`` tokens.
"""

import json
import re
from pathlib import Path

import pytest

THEMES_DIR = Path(__file__).resolve().parents[2] / "resources" / "themes"
THEMES = sorted(path for path in THEMES_DIR.iterdir() if path.is_dir())


def load_palette(theme_dir):
    return json.loads((theme_dir / "palette.json").read_text(encoding="utf-8"))


def load_stylesheet(theme_dir):
    return (theme_dir / "style.qss").read_text(encoding="utf-8")


def relative_luminance(color):
    """Return the WCAG relative luminance of a ``#rgb`` or ``#rrggbb`` colour."""
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)

    def linear(channel):
        channel = channel / 255
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (
        linear(int(value[index : index + 2], 16)) for index in (0, 2, 4)
    )
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def channel_distance(first, second):
    first = first.lstrip("#")
    second = second.lstrip("#")
    if len(first) == 3:
        first = "".join(character * 2 for character in first)
    if len(second) == 3:
        second = "".join(character * 2 for character in second)
    return sum(
        abs(int(first[index : index + 2], 16) - int(second[index : index + 2], 16))
        for index in (0, 2, 4)
    )


@pytest.mark.parametrize("theme_dir", THEMES, ids=lambda path: path.name)
def test_every_theme_defines_menu_colours(theme_dir):
    palette = load_palette(theme_dir)

    assert isinstance(palette.get("menu_background"), str)
    assert isinstance(palette.get("menu_border"), str)


@pytest.mark.parametrize("theme_dir", THEMES, ids=lambda path: path.name)
def test_menu_background_is_lighter_than_the_window_chrome(theme_dir):
    palette = load_palette(theme_dir)
    menu = relative_luminance(palette["menu_background"])

    assert menu > relative_luminance(palette["background"])
    assert menu > relative_luminance(palette["alternate_background"])


@pytest.mark.parametrize("theme_dir", THEMES, ids=lambda path: path.name)
def test_menu_border_separates_the_menu_from_its_background(theme_dir):
    palette = load_palette(theme_dir)

    assert palette["menu_border"] != palette["menu_background"]
    assert channel_distance(palette["menu_border"], palette["menu_background"]) > 60


@pytest.mark.parametrize("theme_dir", THEMES, ids=lambda path: path.name)
def test_stylesheet_paints_menus_with_the_menu_colours(theme_dir):
    stylesheet = load_stylesheet(theme_dir)

    assert "QMenu {" in stylesheet
    assert "background-color: @@menu_background@@;" in stylesheet
    assert "border: 1px solid @@menu_border@@;" in stylesheet


@pytest.mark.parametrize("theme_dir", THEMES, ids=lambda path: path.name)
def test_every_stylesheet_placeholder_has_a_palette_value(theme_dir):
    palette = load_palette(theme_dir)
    placeholders = set(re.findall(r"@@(\w+)@@", load_stylesheet(theme_dir)))

    assert placeholders <= set(palette)
