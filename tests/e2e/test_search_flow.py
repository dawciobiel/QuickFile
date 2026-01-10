# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from PyQt6.QtCore import Qt
from app.task_queue_manager import TaskType, Task
from utils.search_dialog import SearchDialog

def test_search_end_to_end(main_window, qtbot, handle_modal_dialog):
    """
    Tests the entire search process using the modal dialog helper.
    """
    window, isolated_env = main_window
    search_dir = isolated_env["search_data_dir"]

    # --- Setup ---
    window.ui_manager.folder_browser.navigate_to_path(search_dir)
    qtbot.wait(100)

    captured_task = []
    def on_task_completed(task: Task):
        captured_task.append(task)
    window.task_queue_manager.task_completed.connect(on_task_completed)

    # --- Action ---
    def interaction_logic():
        dialog = window.findChild(SearchDialog)
        assert dialog is not None, "SearchDialog did not appear."
        qtbot.keyClicks(dialog.fileNameEdit, "found_me.txt")
        qtbot.mouseClick(dialog.searchButton, Qt.MouseButton.LeftButton)

    handle_modal_dialog(
        trigger_action=window.ui_manager.menu_panel.actions["view.search"],
        interaction_logic=interaction_logic
    )

    # --- Verification ---
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=5000)
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    assert len(captured_task) == 1
    task_result = captured_task[0]
    assert task_result.type == TaskType.SEARCH
    assert len(task_result.result) == 1
    assert "found_me.txt" in task_result.result[0]

    assert window.mainTabWidget.currentWidget() == window.search_tab
    results_model = window.search_results_panel.model
    assert results_model.rowCount() == 1
    first_result_index = results_model.index(0, 0)
    assert "found_me.txt" in results_model.data(first_result_index)
