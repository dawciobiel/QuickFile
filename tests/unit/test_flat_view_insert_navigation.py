# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Insert-key navigation in the flat file view.

Specification (``docs/architecture/file-browser/folder-browser.md``): Insert
marks the current row and immediately moves the cursor one row down. Each
keypress must act on the row that is current *at that moment*, so held or
rapidly repeated presses mark consecutive rows. The action is therefore
synchronous: a queued cursor move lets two presses toggle the same row (a
second toggle unmarks it) and then both move to the same target.
"""

import importlib
import os
import sys
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent

from tests.plugin_helpers import get_latest_plugin_path

FILE_NAMES = ("a.txt", "b.txt", "c.txt")


@pytest.fixture(scope="module")
def flat_view_module():
    plugin_dir = get_latest_plugin_path("org.quickfile", "flat_view")
    sys.path.insert(0, plugin_dir)
    try:
        yield importlib.import_module("flat_view")
    finally:
        sys.path.remove(plugin_dir)
        sys.modules.pop("flat_view", None)


@pytest.fixture
def view(flat_view_module, qapp, tmp_path):
    for name in FILE_NAMES:
        (tmp_path / name).write_text(name)

    settings = MagicMock()
    settings.get_setting.side_effect = lambda key, default=None: {
        "showDotFiles": False,
        "file_permissions_display_mode": "symbolic",
        "show_uid_column": False,
        "show_gid_column": False,
    }.get(key, default)
    theme = MagicMock()
    theme.get_current_theme_data.return_value = {}

    file_view = flat_view_module.FlatFileView(settings, theme)
    file_view.set_path(str(tmp_path))
    yield file_view
    file_view.deleteLater()


def move_to_row(view, row):
    view.view.setCurrentIndex(view.model.index(row, 0))


def press_insert(view):
    event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Insert, Qt.KeyboardModifier.NoModifier
    )
    assert view.handle_key_event(event) is True


def marked_names(view):
    return {os.path.basename(path) for path in view.get_insert_selected_paths()}


def test_insert_marks_the_current_row_and_moves_the_cursor_down(view, qtbot):
    move_to_row(view, 1)

    press_insert(view)
    qtbot.wait(20)  # would catch a deferred move, should not be needed

    assert marked_names(view) == {"a.txt"}
    assert view.view.currentIndex().row() == 2


def test_rapid_insert_presses_mark_consecutive_rows(view, qtbot):
    move_to_row(view, 1)

    press_insert(view)
    press_insert(view)

    qtbot.wait(20)

    assert marked_names(view) == {"a.txt", "b.txt"}
    assert view.view.currentIndex().row() == 3


def test_insert_on_the_parent_entry_only_moves_the_cursor(view, qtbot):
    move_to_row(view, 0)  # ".."

    press_insert(view)
    qtbot.wait(20)

    assert marked_names(view) == set()
    assert view.view.currentIndex().row() == 1


def test_insert_on_the_last_row_does_not_move_past_the_end(view, qtbot):
    last_row = view.model.rowCount() - 1
    move_to_row(view, last_row)

    press_insert(view)
    qtbot.wait(20)

    assert marked_names(view) == {FILE_NAMES[-1]}
    assert view.view.currentIndex().row() == last_row


def test_insert_twice_on_the_same_row_unmarks_it(view, qtbot):
    move_to_row(view, 1)

    press_insert(view)
    move_to_row(view, 1)
    press_insert(view)
    qtbot.wait(20)

    assert marked_names(view) == set()
