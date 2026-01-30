# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt
from app.task_queue_manager import TaskType, Task

def test_delete_flow_e2e(main_window, qtbot):
    """
    Tests the end-to-end delete operation flow by directly creating a task.
    """
    window, isolated_env = main_window
    delete_dir = isolated_env["delete_dir"]
    file_to_delete = "file_to_delete.txt"
    path_to_delete = os.path.join(delete_dir, file_to_delete)

    assert os.path.exists(path_to_delete)

    # --- Setup ---
    left_panel = window.folder_browser.get_left_panel_widget()
    window.folder_browser.set_active_panel(left_panel)
    window.folder_browser.navigate_to_path(delete_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == delete_dir)

    left_panel.file_view.select_items_by_paths([path_to_delete])
    qtbot.wait(50)

    # --- Action ---
    options = {
        "move_to_trash": False, # Permanent delete for simplicity in tests
        "plugin_id": "org.quickfile.delete_operation" # Używamy nowego pluginu
    }

    delete_task = Task(
        TaskType.DELETE,
        source_paths=[path_to_delete],
        options=options
    )

    def refresh_on_finish(task):
        if task.id == delete_task.id:
            window.folder_browser.refresh_path(delete_dir)

    window.task_queue_manager.task_finished.connect(refresh_on_finish)

    window.task_queue_manager.add_task(delete_task)

    # --- Verification ---
    qtbot.waitUntil(lambda: not os.path.exists(path_to_delete), timeout=10000)
    assert not os.path.exists(path_to_delete)

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    left_view_model = left_panel.file_view.model
    
    qtbot.waitUntil(lambda: not does_item_exist_in_model(left_view_model, file_to_delete), timeout=5000)
    assert not does_item_exist_in_model(left_view_model, file_to_delete)

    window.task_queue_manager.task_finished.disconnect(refresh_on_finish)
