# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Theme handling in the flat file view.

``main.py`` applies the saved theme only after ``MainWindow`` (and therefore the
file views) has been built, so a model created at startup legitimately sees an
empty ``ThemeManager.current_theme_data``. That used to be logged as a warning,
which looked like an error on every launch. The model has to start with empty
styles and pick the real ones up from ``theme_changed``.
"""

import importlib
import logging
import sys
from unittest.mock import MagicMock

import pytest

from tests.plugin_helpers import get_latest_plugin_path


@pytest.fixture(scope="module")
def flat_view_module():
    plugin_dir = get_latest_plugin_path("org.quickfile", "flat_view")
    sys.path.insert(0, plugin_dir)
    try:
        yield importlib.import_module("flat_view")
    finally:
        sys.path.remove(plugin_dir)
        sys.modules.pop("flat_view", None)


def make_theme(theme_data):
    theme = MagicMock()
    theme.get_current_theme_data.return_value = theme_data
    return theme


def theme_warnings(caplog):
    return [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING and "theme" in record.getMessage().lower()
    ]


def test_startup_without_an_applied_theme_does_not_warn(
    flat_view_module, qapp, caplog
):
    caplog.set_level(logging.DEBUG)

    model = flat_view_module.FlatFileSystemModel(theme_manager=make_theme({}))

    assert theme_warnings(caplog) == []
    assert model._file_styles == {}
    assert model._special_type_styles == {}


def test_an_applied_theme_is_loaded(flat_view_module, qapp):
    file_styles = {"txt": {"foreground_color": "#ffffff"}}
    special_types = {"symlink": {"foreground_color": "#00ff00"}}
    theme = make_theme({"file_styles": file_styles, "special_types": special_types})

    model = flat_view_module.FlatFileSystemModel(theme_manager=theme)

    assert model._file_styles == file_styles
    assert model._special_type_styles == special_types


def test_a_theme_applied_later_replaces_the_empty_styles(flat_view_module, qapp):
    theme = make_theme({})
    model = flat_view_module.FlatFileSystemModel(theme_manager=theme)
    assert model._file_styles == {}
    layout_changes = []
    model.layoutChanged.connect(lambda: layout_changes.append(True))

    theme.get_current_theme_data.return_value = {
        "file_styles": {"txt": {"foreground_color": "#ffffff"}},
        "special_types": {},
    }
    model.on_theme_changed()

    assert model._file_styles == {"txt": {"foreground_color": "#ffffff"}}
    assert layout_changes
