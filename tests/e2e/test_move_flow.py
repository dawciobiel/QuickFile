# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtCore import Qt
from app.task_queue_manager import TaskType, Task
from utils.move_dialog import MoveDialog

def test_move_end_to_end(main_window, qtbot, handle_modal_dialog):
    """
    Tests the entire file move process (F6) from a user's perspective.
    """
    window, isolated_env = main_window
    source_dir = isolated_env["move_source_dir"]
    dest_dir = isolated_env["move_dest_dir"]
    file_to_move = "file_to_move.txt"
    source_path = os.path.join(source_dir, file_to_move)
    dest_path = os.path.join(dest_dir, file_to_move)

    # --- Setup ---
    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    right_panel = window.ui_manager.folder_browser.get_right_panel_widget()

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(source_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == source_dir)

    window.ui_manager.folder_browser.set_active_panel(right_panel)
    window.ui_manager.folder_browser.navigate_to_path(dest_dir)
    qtbot.waitUntil(lambda: right_panel.path_edit.text() == dest_dir)

    window.ui_manager.folder_browser.set_active_panel(left_panel)
    left_panel.file_view.select_items_by_paths([source_path])
    qtbot.wait(50)

    captured_task = []
    def on_task_completed(task: Task):
        captured_task.append(task)
    window.task_queue_manager.task_completed.connect(on_task_completed)

    # --- Action ---
    def interaction_logic():
        dialog = window.findChild(MoveDialog)
        assert dialog is not None, "MoveDialog did not appear."
        qtbot.mouseClick(dialog.start_button, Qt.MouseButton.LeftButton)

    handle_modal_dialog(
        trigger_action=window.ui_manager.menu_panel.actions["operations.move"],
        interaction_logic=interaction_logic
    )

    # --- Verification ---
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=5000)
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    assert len(captured_task) == 1
    task_result = captured_task[0]
    assert task_result.type == TaskType.MOVE
    assert task_result.source_paths[0] == source_path
    assert task_result.destination_path == dest_dir

    assert not os.path.exists(source_path)
    assert os.path.exists(dest_path)

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    left_view_model = left_panel.file_view.model
    right_view_model = right_panel.file_view.model
    qtbot.waitUntil(lambda: not does_item_exist_in_model(left_view_model, file_to_move), timeout=2000)
    qtbot.waitUntil(lambda: does_item_exist_in_model(right_view_model, file_to_move), timeout=2000)

    assert not does_item_exist_in_model(left_view_model, file_to_move)
    assert does_item_exist_in_model(right_view_model, file_to_move)
