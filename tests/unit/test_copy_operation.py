# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from PyQt6.QtWidgets import QDialog

def test_copy_single_item_with_dialog(create_app_handler, mocker):
    # Patch CopyDialog BEFORE creating the handler
    MockCopyDialog = mocker.patch('app.dialog_handler.CopyDialog')
    mock_dialog_instance = MockCopyDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"overwrite": False}

    # Create handler
    app_handler = create_app_handler()

    # Setup mocks
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/to/source"]
    app_handler.ui_state_provider.get_inactive_panel_path.return_value = "/path/to/dest"

    # Execute
    app_handler.copy_selected_item()

    # Assert
    MockCopyDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/to/source"],
        "/path/to/dest",
        app_handler.task_queue_manager,
        app_handler.background_task_manager,
        app_handler.dialog_handler.theme_manager
    )

def test_copy_multiple_items(create_app_handler, mocker):
    MockCopyDialog = mocker.patch('app.dialog_handler.CopyDialog')
    mock_dialog_instance = MockCopyDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"overwrite": True}

    app_handler = create_app_handler()

    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1", "/path/2"]
    app_handler.ui_state_provider.get_inactive_panel_path.return_value = "/dest"

    app_handler.copy_selected_item()

    MockCopyDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1", "/path/2"],
        "/dest",
        app_handler.task_queue_manager,
        app_handler.background_task_manager,
        app_handler.dialog_handler.theme_manager
    )

def test_copy_no_source_selected(create_app_handler, mocker):
    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = []
    
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')
    
    app_handler.copy_selected_item()
    
    mock_show_error.assert_called_once()
