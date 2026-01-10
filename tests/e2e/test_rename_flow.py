# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtWidgets import QInputDialog

def test_rename_end_to_end(main_window, qtbot, mocker):
    """
    Tests the entire file rename process (F2) from a user's perspective.
    """
    window, isolated_env = main_window
    rename_dir = isolated_env["rename_dir"]
    original_name = "file_to_rename.txt"
    new_name = "renamed_file.txt"
    original_path = os.path.join(rename_dir, original_name)
    new_path = os.path.join(rename_dir, new_name)

    # --- Setup ---
    mocker.patch.object(QInputDialog, 'getText', return_value=(new_name, True))

    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(rename_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == rename_dir)

    # Correctly select the item by setting the current index in the view,
    # which simulates a user clicking or using arrow keys.
    model = left_panel.file_view.model
    index_to_select = None
    for row in range(model.rowCount()):
        index = model.index(row, 0)
        if model.data(index) == original_name:
            index_to_select = index
            break
    assert index_to_select is not None, "Test file not found in model."
    left_panel.file_view.view.setCurrentIndex(index_to_select)
    qtbot.wait(50)

    # --- Action ---
    rename_action = window.ui_manager.menu_panel.actions["operations.rename"]
    rename_action.trigger()

    # --- Verification ---
    qtbot.wait(200)

    assert not os.path.exists(original_path)
    assert os.path.exists(new_path)

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    left_view_model = left_panel.file_view.model
    qtbot.waitUntil(lambda: does_item_exist_in_model(left_view_model, new_name), timeout=2000)
    
    assert not does_item_exist_in_model(left_view_model, original_name)
    assert does_item_exist_in_model(left_view_model, new_name)
