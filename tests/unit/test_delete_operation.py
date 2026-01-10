# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from PyQt6.QtWidgets import QDialog

def test_delete_items_to_trash(create_app_handler, mocker):
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"move_to_trash": True}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1", "/path/2"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1", "/path/2"],
        app_handler.task_queue_manager,
        app_handler.background_task_manager
    )

def test_delete_items_permanently(create_app_handler, mocker):
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"move_to_trash": False}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1"],
        app_handler.task_queue_manager,
        app_handler.background_task_manager
    )

def test_delete_items_cancelled(create_app_handler, mocker):
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Rejected

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once()
    # TaskQueueManager should NOT be called (we can't easily verify this without mocking TQM inside handler)

def test_delete_items_confirmed(create_app_handler, mocker):
    # This is essentially duplicate of test_delete_items_to_trash but let's keep it consistent
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"move_to_trash": True}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once()

def test_delete_no_source_selected(create_app_handler, mocker):
    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = []
    
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')
    
    app_handler.delete_selected_item()
    
    mock_show_error.assert_called_once()
