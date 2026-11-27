# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""The viewer detects the file encoding when it opens a file.

Specification: ``docs/architecture/plugins/plugins.md``
("``org.quickfile.standard_viewer``").
"""

import glob
import importlib.util
import os

import pytest

from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def load_viewer_module():
    pattern = os.path.join(
        PROJECT_ROOT,
        "plugins",
        "org.quickfile",
        "standard_viewer",
        "*",
        "file_viewer_dialog.py",
    )
    paths = sorted(glob.glob(pattern))
    assert len(paths) == 1, paths
    spec = importlib.util.spec_from_file_location(
        "plugin_standard_viewer_encoding", paths[0]
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def open_viewer(qapp):
    module = load_viewer_module()
    theme = ThemeManager(SettingsManager())
    created = []

    def open_file(path):
        viewer = module.FileViewerWindow(str(path), theme)
        created.append(viewer)
        return viewer

    yield open_file
    for viewer in created:
        viewer.deleteLater()


def test_windows_1250_file_is_detected(open_viewer, tmp_path):
    text = "Zażółć gęślą jaźń"
    path = tmp_path / "cp1250.txt"
    path.write_bytes(text.encode("windows-1250"))

    viewer = open_viewer(path)

    assert viewer.current_encoding == "windows-1250"
    assert viewer.encoding_combo.currentData() == "windows-1250"
    assert viewer.text_edit.toPlainText() == text


def test_utf8_bom_is_detected(open_viewer, tmp_path):
    path = tmp_path / "bom.txt"
    path.write_bytes("hello".encode("utf-8-sig"))

    viewer = open_viewer(path)

    assert viewer.current_encoding == "utf-8-sig"
    assert viewer.text_edit.toPlainText() == "hello"


def test_utf16_bom_is_detected(open_viewer, tmp_path):
    path = tmp_path / "utf16.txt"
    path.write_bytes("hello".encode("utf-16"))

    viewer = open_viewer(path)

    assert viewer.current_encoding == "utf-16"
    assert viewer.text_edit.toPlainText() == "hello"


def test_switching_the_selector_decodes_with_the_new_codec(open_viewer, tmp_path):
    path = tmp_path / "encoded.txt"
    path.write_bytes(b"\xb9")

    viewer = open_viewer(path)
    assert viewer.text_edit.toPlainText() == "ą"

    index = viewer.encoding_combo.findData("iso-8859-2")
    viewer.encoding_combo.setCurrentIndex(index)

    assert viewer.current_encoding == "iso-8859-2"
    assert viewer.text_edit.toPlainText() == "š"


def test_markdown_uses_the_detected_encoding(open_viewer, tmp_path):
    text = "Zażółć gęślą jaźń"
    path = tmp_path / "note.md"
    path.write_bytes(text.encode("windows-1250"))

    viewer = open_viewer(path)

    assert viewer.current_view_mode == "markdown"
    assert viewer.current_encoding == "windows-1250"
    assert text in viewer.rich_text_browser.toPlainText()
