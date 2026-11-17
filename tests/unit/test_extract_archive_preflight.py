# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Extraction must not queue a task that cannot succeed.

RAR extraction is done by an external program. If none is installed, the user
gets an actionable message before being asked for a destination, instead of a
failed task later. The check belongs to the host: a sandboxed plugin cannot
show a dialog, and a task error is the wrong place to explain an installation.
"""

from unittest.mock import MagicMock

from app.dialog_handler import DialogHandler
from app.task_queue_manager import TaskType


RAR_PLUGIN_METADATA = {
    "id": "org.quickfile.rar_archiver",
    "name": "RAR Archiver",
    "external_tools": [
        {
            "id": "rar_backend",
            "name": "RAR extraction backend",
            "executables": ["unrar", "unar", "bsdtar", "7z", "7zz"],
        }
    ],
}


class FakeArchivePlugin:
    def __init__(self, metadata):
        self.metadata = metadata


def make_handler(plugin):
    plugin_manager = MagicMock()
    plugin_manager.get_archiver_for_file.return_value = plugin

    task_queue_manager = MagicMock()
    task_queue_manager.plugin_manager = plugin_manager

    ui_state_provider = MagicMock()
    ui_state_provider.get_current_selected_path.return_value = "/tmp/archive.rar"

    handler = DialogHandler(
        main_window=MagicMock(),
        file_manager=MagicMock(),
        file_comparator=MagicMock(),
        favorites_manager=MagicMock(),
        directory_synchronizer=MagicMock(),
        ui_state_provider=ui_state_provider,
        settings_manager=MagicMock(),
        background_task_manager=MagicMock(),
        task_queue_manager=task_queue_manager,
    )
    return handler, task_queue_manager


def test_extraction_is_refused_when_the_backend_is_missing(monkeypatch, mocker):
    monkeypatch.setattr("shutil.which", lambda command: None)
    warning = mocker.patch("app.dialog_handler.QMessageBox.warning")
    ask_destination = mocker.patch("app.dialog_handler.QInputDialog.getText")

    handler, queue = make_handler(FakeArchivePlugin(RAR_PLUGIN_METADATA))
    handler.extract_archive()

    assert warning.call_count == 1
    message = warning.call_args.args[2]
    assert "RAR Archiver" in message
    assert "unrar" in message

    ask_destination.assert_not_called()
    queue.add_task.assert_not_called()


def test_extraction_proceeds_when_any_backend_is_available(monkeypatch, mocker):
    monkeypatch.setattr(
        "shutil.which",
        lambda command: "/usr/bin/bsdtar" if command == "bsdtar" else None,
    )
    warning = mocker.patch("app.dialog_handler.QMessageBox.warning")
    mocker.patch(
        "app.dialog_handler.QInputDialog.getText", return_value=("/tmp/out", True)
    )

    handler, queue = make_handler(FakeArchivePlugin(RAR_PLUGIN_METADATA))
    handler.extract_archive()

    warning.assert_not_called()
    queue.add_task.assert_called_once()
    assert queue.add_task.call_args.args[0].type is TaskType.EXTRACT_ARCHIVE


def test_a_plugin_without_tool_declarations_is_not_checked(monkeypatch, mocker):
    def which(command):
        raise AssertionError(f"which({command!r}) was called for a plugin without tools")

    monkeypatch.setattr("shutil.which", which)
    mocker.patch(
        "app.dialog_handler.QInputDialog.getText", return_value=("/tmp/out", True)
    )

    plugin = FakeArchivePlugin({"id": "org.quickfile.zip_archiver", "name": "ZIP"})
    handler, queue = make_handler(plugin)
    handler.extract_archive()

    queue.add_task.assert_called_once()
