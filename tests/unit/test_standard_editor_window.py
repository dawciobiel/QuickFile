# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""The built-in editor opens a non-modal window, not a modal dialog.

Specification: ``docs/architecture/plugins/plugins.md``
("``org.quickfile.standard_editor``").
"""

import importlib
import sys
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QDialogButtonBox, QMainWindow, QMessageBox

from tests.plugin_helpers import get_latest_plugin_path

PLUGIN_GROUP = "org.quickfile"
PLUGIN_NAME = "standard_editor"


@pytest.fixture
def editor_modules():
    version_dir = get_latest_plugin_path(PLUGIN_GROUP, PLUGIN_NAME)
    saved = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "plugin" or name == "widgets" or name.startswith("widgets.")
    }
    for name in saved:
        sys.modules.pop(name, None)

    sys.path.insert(0, version_dir)
    try:
        plugin = importlib.import_module("plugin")
        editor_window = importlib.import_module("widgets.editor_window")
        yield plugin, editor_window
    finally:
        sys.path.remove(version_dir)
        for name in list(sys.modules):
            if name == "plugin" or name == "widgets" or name.startswith("widgets."):
                sys.modules.pop(name, None)
        sys.modules.update(saved)


@pytest.fixture
def theme_manager():
    manager = MagicMock()
    manager.get_current_theme_data.return_value = {
        "foreground": "#000000",
        "code_highlighting": {},
    }
    return manager


def _type_at_end(window, text):
    cursor = window.editor_widget.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    window.editor_widget.editor.setTextCursor(cursor)
    window.editor_widget.editor.insertPlainText(text)


def _open_editor(plugin_module, path, theme_manager):
    plugin = plugin_module.StandardEditorPlugin()
    window = plugin.open_editor(str(path), theme_manager, None)
    return plugin, window


def test_editor_opens_as_a_non_modal_window_with_window_controls(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert isinstance(window, QMainWindow)
    assert not window.isModal()
    assert window.isVisible()
    assert window.windowFlags() & Qt.WindowType.WindowMinMaxButtonsHint

    window.close()


def test_opening_the_same_file_twice_raises_the_existing_window(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    same_window = plugin.open_editor(str(path), theme_manager, None)
    qapp.processEvents()

    assert same_window is window
    assert list(plugin.open_editors) == [str(path)]

    window.close()


def test_closing_a_clean_window_does_not_ask(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    question = mocker.patch.object(_editor_window.QMessageBox, "question")
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    window.close()

    question.assert_not_called()
    assert str(path) not in plugin.open_editors


def test_discarding_changes_closes_without_writing(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    question = mocker.patch.object(
        _editor_window.QMessageBox,
        "question",
        return_value=QMessageBox.StandardButton.Discard,
    )
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    _type_at_end(window, " changed")
    assert window.editor_widget.has_unsaved_changes()

    window.close()

    question.assert_called_once()
    assert path.read_text(encoding="utf-8") == "original"
    assert str(path) not in plugin.open_editors


def test_cancelling_the_close_question_keeps_the_window_open(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    mocker.patch.object(
        _editor_window.QMessageBox,
        "question",
        return_value=QMessageBox.StandardButton.Cancel,
    )
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    _type_at_end(window, " changed")

    window.close()

    assert window.isVisible()
    assert str(path) in plugin.open_editors
    assert path.read_text(encoding="utf-8") == "original"

    window.editor_widget.editor.document().setModified(False)
    window.close()


def test_choosing_save_writes_the_file_and_closes(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    mocker.patch.object(
        _editor_window.QMessageBox,
        "question",
        return_value=QMessageBox.StandardButton.Save,
    )
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    _type_at_end(window, " changed")

    window.close()

    assert path.read_text(encoding="utf-8") == "original changed"
    assert str(path) not in plugin.open_editors


def test_save_button_writes_the_file_and_closes(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    path = tmp_path / "note.txt"
    path.write_text("original", encoding="utf-8")

    plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    _type_at_end(window, " changed")

    window.button_box.button(QDialogButtonBox.StandardButton.Save).click()

    assert path.read_text(encoding="utf-8") == "original changed"
    assert str(path) not in plugin.open_editors
