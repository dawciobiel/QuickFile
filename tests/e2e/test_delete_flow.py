# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt
from app.task_queue_manager import TaskType, Task
from utils.delete_dialog import DeleteDialog

def test_delete_end_to_end(main_window, qtbot, handle_modal_dialog):
    """
    Tests the entire file delete process (F8) using the modal dialog helper.
    """
    window, isolated_env = main_window
    delete_dir = isolated_env["delete_dir"]
    file_to_delete = "file_to_delete.txt"
    path_to_delete = os.path.join(delete_dir, file_to_delete)

    assert os.path.exists(path_to_delete)

    # --- Setup ---
    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(delete_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == delete_dir)

    left_panel.file_view.select_items_by_paths([path_to_delete])
    qtbot.wait(50)

    captured_task = []
    def on_task_completed(task: Task):
        captured_task.append(task)
    window.task_queue_manager.task_completed.connect(on_task_completed)

    # --- Action ---
    def interaction_logic():
        dialog = window.findChild(DeleteDialog)
        assert dialog is not None, "DeleteDialog did not appear."
        qtbot.mouseClick(dialog.start_button, Qt.MouseButton.LeftButton)

    handle_modal_dialog(
        trigger_action=window.ui_manager.menu_panel.actions["operations.delete"],
        interaction_logic=interaction_logic
    )

    # --- Verification ---
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=5000)
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    assert len(captured_task) == 1
    task_result = captured_task[0]
    assert task_result.type == TaskType.DELETE
    assert task_result.source_paths[0] == path_to_delete

    assert not os.path.exists(path_to_delete)

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    left_view_model = left_panel.file_view.model
    qtbot.waitUntil(lambda: not does_item_exist_in_model(left_view_model, file_to_delete), timeout=2000)
    assert not does_item_exist_in_model(left_view_model, file_to_delete)
