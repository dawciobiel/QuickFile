# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""The built-in editor opens a non-modal window and handles file encodings.

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


def test_editor_loads_a_file_in_windows_1250(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    text = "Zażółć gęślą jaźń"
    path = tmp_path / "cp1250.txt"
    path.write_bytes(text.encode("windows-1250"))

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert window.editor_widget.encoding == "windows-1250"
    assert window.editor_widget.editor.toPlainText() == text

    window.close()


def test_utf_16_bom_is_detected(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    path = tmp_path / "utf16.txt"
    path.write_bytes("hello".encode("utf-16"))

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert window.editor_widget.encoding == "utf-16"
    assert window.editor_widget.editor.toPlainText() == "hello"

    window.close()


def test_switching_display_encoding_reloads_without_marking_modified(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    path = tmp_path / "encoded.txt"
    path.write_bytes(b"\xb9")

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    assert window.editor_widget.encoding == "windows-1250"
    assert window.editor_widget.editor.toPlainText() == "ą"

    assert window.editor_widget.set_display_encoding("iso-8859-2") is True

    assert window.editor_widget.encoding == "iso-8859-2"
    assert window.editor_widget.editor.toPlainText() == "š"
    assert not window.editor_widget.has_unsaved_changes()

    window.close()


def test_switching_encoding_can_be_cancelled_with_unsaved_changes(
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

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()
    _type_at_end(window, " changed")

    assert window.editor_widget.set_display_encoding("windows-1250") is False
    assert window.editor_widget.encoding == "utf-8"
    assert window.editor_widget.editor.toPlainText() == "original changed"

    window.editor_widget.editor.document().setModified(False)
    window.close()


def test_reload_with_a_wrong_encoding_keeps_the_current_text(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    warning = mocker.patch.object(_editor_window.QMessageBox, "warning")
    path = tmp_path / "encoded.txt"
    path.write_bytes(b"\xb9")

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert window.editor_widget.set_display_encoding("utf-8") is False
    assert window.editor_widget.encoding == "windows-1250"
    assert window.editor_widget.editor.toPlainText() == "ą"
    warning.assert_called_once()

    window.close()


def test_unknown_encoding_is_rejected(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    warning = mocker.patch.object(_editor_window.QMessageBox, "warning")
    path = tmp_path / "note.txt"
    path.write_text("hello", encoding="utf-8")

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert window.editor_widget.set_display_encoding("not-a-codec") is False
    assert window.editor_widget.encoding == "utf-8"
    warning.assert_called_once()

    window.close()


def test_converting_encoding_marks_modified_and_saves_new_encoding(
    editor_modules, theme_manager, tmp_path, qapp
):
    plugin_module, _editor_window = editor_modules
    path = tmp_path / "note.txt"
    path.write_text("Zażółć", encoding="utf-8")

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert window.editor_widget.convert_encoding("windows-1250") is True
    assert window.editor_widget.encoding == "windows-1250"
    assert window.editor_widget.has_unsaved_changes()

    assert window.editor_widget.save_file() is True
    assert path.read_bytes() == "Zażółć".encode("windows-1250")

    window.close()


def test_conversion_rejects_unrepresentable_characters(
    editor_modules, theme_manager, tmp_path, qapp, mocker
):
    plugin_module, _editor_window = editor_modules
    warning = mocker.patch.object(_editor_window.QMessageBox, "warning")
    path = tmp_path / "note.txt"
    path.write_text("😀", encoding="utf-8")

    _plugin, window = _open_editor(plugin_module, path, theme_manager)
    qapp.processEvents()

    assert window.editor_widget.convert_encoding("windows-1250") is False
    assert window.editor_widget.encoding == "utf-8"
    assert not window.editor_widget.has_unsaved_changes()
    warning.assert_called_once()

    window.close()
