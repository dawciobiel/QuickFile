# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt, QTimer
from app.task_queue_manager import TaskType, Task
from utils.copy_dialog import CopyDialog

def test_copy_end_to_end(main_window, qtbot):
    """
    Tests the entire file copy process (F5) from a user's perspective.
    """
    window, isolated_env = main_window
    source_dir = isolated_env["source_dir"]
    destination_dir = isolated_env["destination_dir"]
    file_to_copy = "file_to_copy.txt"
    source_path = os.path.join(source_dir, file_to_copy)
    destination_path = os.path.join(destination_dir, file_to_copy)

    # --- Setup: Navigate panels ---
    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    right_panel = window.ui_manager.folder_browser.get_right_panel_widget()

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(source_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == source_dir)

    window.ui_manager.folder_browser.set_active_panel(right_panel)
    window.ui_manager.folder_browser.navigate_to_path(destination_dir)
    qtbot.waitUntil(lambda: right_panel.path_edit.text() == destination_dir)

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    qtbot.wait(50)

    # --- Action: Select file and trigger copy ---
    left_panel.file_view.select_items_by_paths([source_path])
    qtbot.wait(50)

    def interact_with_copy_dialog():
        dialog = window.findChild(CopyDialog)
        assert dialog is not None, "CopyDialog did not appear."
        qtbot.mouseClick(dialog.start_button, Qt.MouseButton.LeftButton)

    captured_task = []
    def on_task_completed(task: Task):
        captured_task.append(task)
    window.task_queue_manager.task_completed.connect(on_task_completed)

    QTimer.singleShot(100, interact_with_copy_dialog)
    copy_action = window.ui_manager.menu_panel.actions["operations.copy"]
    copy_action.trigger()

    # --- Verification ---
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=5000)
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    assert len(captured_task) == 1
    task_result = captured_task[0]
    assert task_result.type == TaskType.COPY
    assert task_result.source_paths[0] == source_path
    assert task_result.destination_path == destination_dir

    assert os.path.exists(destination_path), "File was not copied to the destination directory."

    # Custom verification function to check if the item exists in the model
    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            index = model.index(row, 0) # Assuming name is in the first column
            if model.data(index) == name:
                return True
        return False

    right_view_model = right_panel.file_view.model
    qtbot.waitUntil(lambda: does_item_exist_in_model(right_view_model, file_to_copy), timeout=2000)
    
    assert does_item_exist_in_model(right_view_model, file_to_copy), "Copied file did not appear in the destination panel's view."
