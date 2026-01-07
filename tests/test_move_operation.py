# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from PyQt6.QtWidgets import QDialog

def test_move_single_item_with_dialog(create_app_handler, mocker):
    MockMoveDialog = mocker.patch('app.dialog_handler.MoveDialog')
    mock_dialog_instance = MockMoveDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"overwrite": False}

    app_handler = create_app_handler()

    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/to/source"]
    app_handler.ui_state_provider.get_inactive_panel_path.return_value = "/path/to/dest"

    app_handler.move_selected_item()

    MockMoveDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/to/source"],
        "/path/to/dest",
        app_handler.task_queue_manager,
        app_handler.background_task_manager
    )

def test_move_multiple_items(create_app_handler, mocker):
    MockMoveDialog = mocker.patch('app.dialog_handler.MoveDialog')
    mock_dialog_instance = MockMoveDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"overwrite": True}

    app_handler = create_app_handler()

    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1", "/path/2"]
    app_handler.ui_state_provider.get_inactive_panel_path.return_value = "/dest"

    app_handler.move_selected_item()

    MockMoveDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1", "/path/2"],
        "/dest",
        app_handler.task_queue_manager,
        app_handler.background_task_manager
    )

def test_move_no_source_selected(create_app_handler, mocker):
    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = []
    
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')
    
    app_handler.move_selected_item()
    
    mock_show_error.assert_called_once()
