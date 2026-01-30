# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox
from app.task_queue_manager import TaskType, Task
from utils.sync_dialog import SyncDialog

def test_sync_end_to_end(main_window, qtbot, handle_modal_dialog):
    """
    Tests the entire directory synchronization process using the modal dialog helper.
    """
    window, isolated_env = main_window
    source_dir = isolated_env["sync_source_dir"]
    dest_dir = isolated_env["sync_dest_dir"]
    file_to_sync = "file_to_sync.txt"
    synced_file_path = os.path.join(dest_dir, file_to_sync)

    # --- Setup ---
    left_panel = window.folder_browser.get_left_panel_widget()
    right_panel = window.folder_browser.get_right_panel_widget()

    window.folder_browser.set_active_panel(left_panel)
    window.folder_browser.navigate_to_path(source_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == source_dir)

    window.folder_browser.set_active_panel(right_panel)
    window.folder_browser.navigate_to_path(dest_dir)
    qtbot.waitUntil(lambda: right_panel.path_edit.text() == dest_dir)

    captured_task = []
    def on_task_completed(task: Task):
        captured_task.append(task)
    window.task_queue_manager.task_completed.connect(on_task_completed)

    # --- Action ---
    def interaction_logic():
        dialog = window.findChild(SyncDialog)
        assert dialog is not None, "SyncDialog did not appear."
        ok_button = dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    handle_modal_dialog(
        trigger_action=window.menu_panel.actions["view.synchronize"],
        interaction_logic=interaction_logic
    )

    # --- Verification ---
    # 1. Wait for the task to be marked as completed in the manager
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=10000)
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    # 2. Verify the task details
    assert len(captured_task) == 1
    task_result = captured_task[0]
    assert task_result.type == TaskType.SYNC
    assert task_result.source_paths[0] == source_dir
    assert task_result.destination_path == dest_dir

    # 3. Wait for the file to physically exist
    qtbot.waitUntil(lambda: os.path.exists(synced_file_path), timeout=5000)
    assert os.path.exists(synced_file_path)

    # 4. Manually trigger a refresh and wait for the model to update
    window.folder_browser.refresh_path(dest_dir)

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    right_view_model = right_panel.file_view.model
    qtbot.waitUntil(lambda: does_item_exist_in_model(right_view_model, file_to_sync), timeout=10000)
    assert does_item_exist_in_model(right_view_model, file_to_sync)
