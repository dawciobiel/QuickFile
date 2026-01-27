# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt, QTimer
from app.task_queue_manager import TaskType, Task
from utils.copy_dialog import CopyDialog

def test_copy_flow_e2e(main_window, qtbot):
    """
    Tests the end-to-end copy operation flow by directly creating a task,
    bypassing the modal dialog to avoid issues in the test environment.
    """
    window, isolated_env = main_window
    source_dir = isolated_env["source_dir"]
    destination_dir = isolated_env["destination_dir"]
    file_to_copy = "file_to_copy.txt"
    source_path = os.path.join(source_dir, file_to_copy)
    destination_path = os.path.join(destination_dir, file_to_copy)

    # --- Setup UI ---
    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    right_panel = window.ui_manager.folder_browser.get_right_panel_widget()

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(source_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == source_dir)
    
    window.ui_manager.folder_browser.set_active_panel(right_panel)
    window.ui_manager.folder_browser.navigate_to_path(destination_dir)
    qtbot.waitUntil(lambda: right_panel.path_edit.text() == destination_dir)

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    left_panel.file_view.select_items_by_paths([source_path])
    qtbot.wait(50)

    # --- Action ---
    # 1. Define the task options, as the dialog would.
    options = {
        "overwrite": False,
        "preserve_timestamp": True,
        "plugin_id": "org.quickfile.standard_operations"
    }

    # 2. Create the Task object directly.
    copy_task = Task(
        TaskType.COPY,
        source_paths=[source_path],
        destination_path=destination_dir,
        options=options
    )

    # 3. Add the task to the queue manager, simulating the dialog's action.
    window.task_queue_manager.add_task(copy_task)

    # --- Verification ---
    # 1. Wait until the file appears in the destination directory.
    qtbot.waitUntil(lambda: os.path.exists(destination_path), timeout=10000)
    assert os.path.exists(destination_path)
    assert open(destination_path).read() == "This is a test file."

    # 2. Verify that the UI (right panel) has been updated.
    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    right_view_model = right_panel.file_view.model
    # We need to trigger a refresh manually, as the dialog would have done it via signals.
    # In a real scenario, the task completion signal would trigger this.
    # Let's connect to the task_finished signal to trigger a refresh.
    def refresh_on_finish(task):
        if task.id == copy_task.id:
            window.ui_manager.folder_browser.refresh_path(destination_dir)

    window.task_queue_manager.task_finished.connect(refresh_on_finish)
    
    qtbot.waitUntil(lambda: does_item_exist_in_model(right_view_model, file_to_copy), timeout=5000)
    assert does_item_exist_in_model(right_view_model, file_to_copy)
    
    # Disconnect to avoid side effects in other tests
    window.task_queue_manager.task_finished.disconnect(refresh_on_finish)
