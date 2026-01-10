# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialogButtonBox
from app.task_queue_manager import TaskType, Task
from utils.sync_dialog import SyncDialog

def test_sync_end_to_end(main_window, qtbot):
    """
    Tests the entire directory synchronization process from a user's perspective.
    """
    window, isolated_env = main_window
    source_dir = isolated_env["sync_source_dir"]
    dest_dir = isolated_env["sync_dest_dir"]
    file_to_sync = "file_to_sync.txt"
    synced_file_path = os.path.join(dest_dir, file_to_sync)

    # --- Setup: Navigate panels ---
    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    right_panel = window.ui_manager.folder_browser.get_right_panel_widget()

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(source_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == source_dir)

    window.ui_manager.folder_browser.set_active_panel(right_panel)
    window.ui_manager.folder_browser.navigate_to_path(dest_dir)
    qtbot.waitUntil(lambda: right_panel.path_edit.text() == dest_dir)

    # --- Action: Trigger sync ---
    def interact_with_sync_dialog():
        dialog = window.findChild(SyncDialog)
        assert dialog is not None, "SyncDialog did not appear."
        # Find the OK button in the QDialogButtonBox
        ok_button = dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        assert ok_button is not None, "OK button not found in SyncDialog."
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    captured_task = []
    def on_task_completed(task: Task):
        captured_task.append(task)
    window.task_queue_manager.task_completed.connect(on_task_completed)

    QTimer.singleShot(100, interact_with_sync_dialog)
    
    sync_action = window.ui_manager.menu_panel.actions["view.synchronize"]
    sync_action.trigger()

    # --- Verification ---
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=5000)
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    assert len(captured_task) == 1
    task_result = captured_task[0]
    assert task_result.type == TaskType.SYNC
    assert task_result.source_paths[0] == source_dir
    assert task_result.destination_path == dest_dir

    assert os.path.exists(synced_file_path), "File was not synchronized to the destination directory."

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if model.data(index) == name:
                return True
        return False

    right_view_model = right_panel.file_view.model
    qtbot.waitUntil(lambda: does_item_exist_in_model(right_view_model, file_to_sync), timeout=2000)
    
    assert does_item_exist_in_model(right_view_model, file_to_sync), "Synced file did not appear in the destination panel's view."
