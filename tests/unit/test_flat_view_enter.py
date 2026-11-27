# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Enter opens files with the OS association in the flat file view.

Specification: ``docs/architecture/file-browser/folder-browser.md``. Enter on
a directory keeps navigating into it; Enter on a file asks the host to launch
the program associated with the file type instead of using the internal
viewer used by double-click.
"""

import importlib
import os
import sys
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent

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


@pytest.fixture
def view(flat_view_module, qapp, tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "subdir").mkdir()

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


def index_for(view, name):
    for row in range(view.model.rowCount()):
        index = view.model.index(row, 0)
        if view.model.fileName(index) == name:
            return index
    raise AssertionError(f"{name} is not listed")


def press_enter(view):
    event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
    )
    assert view.handle_key_event(event) is True


def test_enter_on_a_file_requests_the_system_default(view):
    requested = []
    selected = []
    view.file_open_requested.connect(requested.append)
    view.file_selected.connect(selected.append)
    view.view.setCurrentIndex(index_for(view, "a.txt"))

    press_enter(view)

    assert requested == [os.path.join(view.get_current_path(), "a.txt")]
    assert selected == []


def test_enter_on_a_directory_still_navigates(view):
    requested = []
    view.file_open_requested.connect(requested.append)
    view.view.setCurrentIndex(index_for(view, "subdir"))

    press_enter(view)

    assert os.path.basename(view.get_current_path()) == "subdir"
    assert requested == []
