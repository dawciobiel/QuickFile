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
    window.folder_browser.navigate_to_path(search_dir)
    qtbot.wait(100)

    # Clear previous results before starting a new search
    window.search_results_panel.clear_results()

    # --- Action ---
    def interaction_logic():
        dialog = window.findChild(SearchDialog)
        assert dialog is not None, "SearchDialog did not appear."
        qtbot.keyClicks(dialog.fileNameEdit, "found_me.txt")
        qtbot.mouseClick(dialog.searchButton, Qt.MouseButton.LeftButton)

    handle_modal_dialog(
        trigger_action=window.menu_panel.actions["view.search"],
        interaction_logic=interaction_logic
    )

    # --- Verification ---
    # In the new architecture, results are streamed. We need to wait until the search panel is populated.
    def check_results():
        if window.mainTabWidget.currentWidget() != window.search_tab:
            window.mainTabWidget.setCurrentWidget(window.search_tab)
        
        results_model = window.search_results_panel.model
        if results_model.rowCount() > 0:
            for row in range(results_model.rowCount()):
                first_result_index = results_model.index(row, 0)
                if "found_me.txt" in results_model.data(first_result_index):
                    return True
        return False

    qtbot.waitUntil(check_results, timeout=10000)
    
    results_model = window.search_results_panel.model
    assert results_model.rowCount() >= 1

    # Verify that our specific file is in the results
    found = False
    for row in range(results_model.rowCount()):
        index = results_model.index(row, 0)
        if "found_me.txt" in results_model.data(index):
            found = True
            break
    assert found, "Expected file 'found_me.txt' not found in search results"
