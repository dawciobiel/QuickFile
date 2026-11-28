# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Double-click and Enter open files through the real main-window wiring.

The application used to connect these signals only in the unused ``UIManager``
class, so the real window emitted them into nothing. These tests drive the
actual ``MainWindow`` and check that the OS launcher is reached.
"""

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent


def index_for(view, name):
    for row in range(view.model.rowCount()):
        index = view.model.index(row, 0)
        if view.model.fileName(index) == name:
            return index
    raise AssertionError(f"{name} is not listed")


def open_panel(main_window, path):
    window, _env = main_window
    window.folder_browser.add_new_tab(path=str(path))
    view = window.folder_browser.active_panel_widget.file_view
    calls = []
    window.app_handler._open_with_system_default = calls.append
    return window, view, calls


def test_double_click_opens_the_file_with_the_system_default(
    main_window, tmp_path
):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    _window, view, calls = open_panel(main_window, tmp_path)

    view.view.doubleClicked.emit(index_for(view, "note.txt"))

    assert calls == [str(target)]


def test_enter_opens_the_file_with_the_system_default(main_window, tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    _window, view, calls = open_panel(main_window, tmp_path)
    view.view.setCurrentIndex(index_for(view, "note.txt"))

    event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier
    )
    assert view.handle_key_event(event) is True

    assert calls == [str(target)]


def test_double_click_on_a_directory_still_navigates(main_window, tmp_path):
    (tmp_path / "subdir").mkdir()
    _window, view, calls = open_panel(main_window, tmp_path)

    view.view.doubleClicked.emit(index_for(view, "subdir"))

    assert calls == []
    assert view.get_current_path().endswith("subdir")
