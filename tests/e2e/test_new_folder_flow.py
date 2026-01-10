# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
from PyQt6.QtWidgets import QInputDialog

def test_new_folder_end_to_end(main_window, qtbot, mocker):
    """
    Tests the entire new folder creation process (F7) from a user's perspective.
    """
    window, isolated_env = main_window
    creation_dir = isolated_env["creation_dir"]
    new_folder_name = "my_new_folder"
    new_folder_path = os.path.join(creation_dir, new_folder_name)

    # --- Setup ---
    mocker.patch.object(QInputDialog, 'getText', return_value=(new_folder_name, True))

    left_panel = window.ui_manager.folder_browser.get_left_panel_widget()
    window.ui_manager.folder_browser.set_active_panel(left_panel)
    window.ui_manager.folder_browser.navigate_to_path(creation_dir)
    qtbot.waitUntil(lambda: left_panel.path_edit.text() == creation_dir)

    # --- Action ---
    new_folder_action = window.ui_manager.menu_panel.actions["operations.new_folder"]
    new_folder_action.trigger()

    # --- Verification ---
    qtbot.wait(200)

    assert os.path.isdir(new_folder_path)

    def does_item_exist_in_model(model, name):
        for row in range(model.rowCount()):
            if model.data(model.index(row, 0)) == name:
                return True
        return False

    left_view_model = left_panel.file_view.model
    qtbot.waitUntil(lambda: does_item_exist_in_model(left_view_model, new_folder_name), timeout=2000)
    
    assert does_item_exist_in_model(left_view_model, new_folder_name)
