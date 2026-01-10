# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from PyQt6.QtCore import Qt, QTimer
from app.task_queue_manager import TaskType, Task
from utils.search_dialog import SearchDialog

def test_search_end_to_end(main_window, qtbot):
    """
    Tests the entire search process from a user's perspective,
    handling modal dialogs correctly and using a robust signal waiting mechanism.
    """
    window, isolated_env = main_window
    search_dir = isolated_env["search_data_dir"]

    # --- Setup: Prepare to capture the signal ---
    # This list will hold the task object when the signal is emitted.
    # Using a list allows the inner function to modify the outer scope variable.
    captured_task = []

    def on_task_completed(task: Task):
        """This slot will be connected to the signal and will capture the task."""
        captured_task.append(task)

    # Connect our custom slot to the signal
    window.task_queue_manager.task_completed.connect(on_task_completed)

    # --- Action: Simulate user interaction ---
    # 1. Navigate to the test search directory
    window.ui_manager.folder_browser.navigate_to_path(search_dir)
    qtbot.wait(100)

    def interact_with_search_dialog():
        """Function to be called by QTimer to interact with the modal dialog."""
        dialog = window.findChild(SearchDialog)
        assert dialog is not None, "SearchDialog did not appear."
        qtbot.keyClicks(dialog.fileNameEdit, "found_me.txt")
        qtbot.mouseClick(dialog.searchButton, Qt.MouseButton.LeftButton)

    # 2. Schedule the interaction and trigger the dialog
    QTimer.singleShot(50, interact_with_search_dialog)
    search_action = window.ui_manager.menu_panel.actions["view.search"]
    search_action.trigger()

    # --- Verification ---
    # 3. Wait until our slot has captured the task object
    qtbot.waitUntil(lambda: len(captured_task) > 0, timeout=5000)

    # 4. Disconnect the signal to avoid side-effects in other tests
    window.task_queue_manager.task_completed.disconnect(on_task_completed)

    # 5. Perform assertions on the captured task
    assert len(captured_task) == 1, "Signal was emitted more than once or not at all."
    task_result = captured_task[0]
    
    assert task_result.type == TaskType.SEARCH, "The completed task was not a search task."
    assert len(task_result.result) == 1, "Search did not find exactly one file."
    assert "found_me.txt" in task_result.result[0], "The wrong file was found."

    # 6. Check if the UI has updated correctly
    assert window.mainTabWidget.currentWidget() == window.search_tab, "Did not switch to the search results tab."

    results_model = window.search_results_panel.model
    assert results_model.rowCount() == 1, "Search results panel does not contain the expected number of results."
    
    first_result_index = results_model.index(0, 0)
    assert "found_me.txt" in results_model.data(first_result_index), "The found file path is incorrect."
