# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Enter launches files with the operating system association.

Specification: ``docs/architecture/file-browser/folder-browser.md``.
"""

from unittest.mock import MagicMock

import pytest

import app.application_logic_handler as module
from app.application_logic_handler import ApplicationLogicHandler


@pytest.fixture
def handler():
    task_queue_manager = MagicMock()
    return ApplicationLogicHandler(
        main_window=MagicMock(),
        file_manager=MagicMock(),
        file_comparator=MagicMock(),
        favorites_manager=MagicMock(),
        directory_synchronizer=MagicMock(),
        theme_manager=MagicMock(),
        ui_state_provider=MagicMock(),
        dialog_handler=MagicMock(),
        settings_handler=MagicMock(),
        background_task_manager=MagicMock(),
        task_queue_manager=task_queue_manager,
    )


def test_file_is_opened_with_xdg_open_on_linux(handler, tmp_path, monkeypatch):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    calls = []
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        module.subprocess, "call", lambda args: calls.append(args) or 0
    )

    handler.open_file_with_system_default(str(target))

    assert calls == [("xdg-open", str(target))]


def test_macos_uses_open(handler, tmp_path, monkeypatch):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    calls = []
    monkeypatch.setattr(module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        module.subprocess, "call", lambda args: calls.append(args) or 0
    )

    handler.open_file_with_system_default(str(target))

    assert calls == [("open", str(target))]


def test_windows_uses_startfile(handler, tmp_path, monkeypatch):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    calls = []
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        module.os, "startfile", lambda path: calls.append(path), raising=False
    )

    handler.open_file_with_system_default(str(target))

    assert calls == [str(target)]


def test_directories_are_ignored(handler, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        module.subprocess, "call", lambda args: calls.append(args) or 0
    )

    handler.open_file_with_system_default(str(tmp_path))

    assert calls == []


def test_missing_files_are_ignored(handler, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        module.subprocess, "call", lambda args: calls.append(args) or 0
    )

    handler.open_file_with_system_default(str(tmp_path / "missing.txt"))

    assert calls == []


def test_failed_launch_is_reported(handler, tmp_path, monkeypatch):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.subprocess, "call", lambda args: 4)
    handler._show_system_open_error = MagicMock()

    handler.open_file_with_system_default(str(target))

    handler._show_system_open_error.assert_called_once()
