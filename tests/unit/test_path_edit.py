# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Behaviour of the folder browser's path field.

Specification: ``docs/architecture/file-browser/folder-browser.md``.

``Ctrl+V`` already reached the ``QLineEdit`` (the global keyboard filter is
installed on the file view, not on the path field). The bug was in what the
field did with the text: typing a leading ``/`` and then pasting an absolute
path produced ``//tmp/x``, and the invalid path was rejected. The same doubled
form survived if it was typed or pasted as a whole.
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


def _active_path_edit(window):
    return window.folder_browser.active_panel_widget.path_edit


def test_ctrl_l_then_ctrl_v_replaces_the_whole_path(main_window, qapp):
    window, env = main_window
    edit = _active_path_edit(window)

    QApplication.clipboard().setText(env["source_dir"])
    window.app_handler.set_focus_on_path_edit()
    qapp.processEvents()

    assert edit.hasFocus()
    assert edit.selectedText() == edit.text()

    QTest.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    qapp.processEvents()

    assert edit.text() == env["source_dir"]


def test_pasting_after_a_typed_slash_keeps_one_leading_separator(
    main_window, qapp
):
    window, _env = main_window
    edit = _active_path_edit(window)

    edit.setText("/")
    edit.setCursorPosition(1)
    edit.setFocus()
    QApplication.clipboard().setText("/tmp/example")
    qapp.processEvents()

    QTest.keyClick(edit, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    qapp.processEvents()

    assert edit.text() == "/tmp/example"


def test_enter_collapses_repeated_separators_before_navigating(
    main_window, qapp, qtbot, monkeypatch, tmp_path
):
    window, _env = main_window
    # The main_window fixture expands every path to the isolated config dir;
    # this test navigates to a real directory instead.
    monkeypatch.setattr(os.path, "expanduser", lambda path: path)

    target = tmp_path / "target"
    target.mkdir()
    panel = window.folder_browser.active_panel_widget
    edit = panel.path_edit

    doubled = str(target).replace("/", "//")
    assert doubled.startswith("//")
    edit.setText(doubled)
    edit.setFocus()
    qapp.processEvents()

    QTest.keyClick(edit, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: panel.file_view.get_current_path() == str(target))

    assert edit.text() == str(target)


def test_normalize_collapses_repeated_separators():
    from browser.folder_browser import normalize_path_text

    assert normalize_path_text("//tmp//example") == "/tmp/example"
    assert normalize_path_text("/tmp/example") == "/tmp/example"
    assert normalize_path_text("relative//path") == "relative/path"
    assert normalize_path_text("   ") == ""
