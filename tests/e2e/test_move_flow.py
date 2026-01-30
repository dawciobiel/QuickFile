# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt
from app.task_queue_manager import TaskType, Task

def test_move_flow_e2e(main_window, qtbot):
    """
    Tests the end-to-end move operation flow by directly creating a task.
    """
    window, isolated_env = main_window
    source_dir = isolated_env["move_source_dir"]
    dest_dir = isolated_env["move_dest_dir"]
    file_to_move = "file_to_move.txt"
    source_path = os.path.join(source_dir, file_to_move)
    dest_path = os.path.join(dest_dir, file_to_move)

    assert os.path.exists(source_path)
    assert not os.path.exists(dest_path)

    # --- Setup ---
    left_panel = window.folder_browser.get_left_panel_widget()
    right_panel = window.folder_browser.get_right_panel_widget()
    
    window.folder_browser.set_active_panel(left_panel)
    window.folder_browser.navigate_to_path(source_dir)
    
    window.folder_browser.set_active_panel(right_panel)
    window.folder_browser.navigate_to_path(dest_dir)

    qtbot.waitUntil(lambda: left_panel.path_edit.text() == source_dir)
    qtbot.waitUntil(lambda: right_panel.path_edit.text() == dest_dir)

    # Set active panel back to left for selection
    window.folder_browser.set_active_panel(left_panel)
    left_panel.file_view.select_items_by_paths([source_path])
    qtbot.wait(50)

    # --- Action ---
    options = {
        "overwrite": False,
        "plugin_id": "org.quickfile.move_operation" # Używamy nowego pluginu
    }

    move_task = Task(
        TaskType.MOVE,
        source_paths=[source_path],
        destination_path=dest_dir,
        options=options
    )

    def refresh_on_finish(task):
        if task.id == move_task.id:
            window.folder_browser.refresh_path(dest_dir)
            window.folder_browser.refresh_path(source_dir)

    window.task_queue_manager.task_finished.connect(refresh_on_finish)

    window.task_queue_manager.add_task(move_task)

    # --- Verification ---
    qtbot.waitUntil(lambda: os.path.exists(dest_path), timeout=10000)
    assert os.path.exists(dest_path)
    assert not os.path.exists(source_path) # Source should NOT exist

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    right_view_model = right_panel.file_view.model
    
    qtbot.waitUntil(lambda: does_item_exist_in_model(right_view_model, file_to_move), timeout=10000)
    assert does_item_exist_in_model(right_view_model, file_to_move)

    window.task_queue_manager.task_finished.disconnect(refresh_on_finish)
