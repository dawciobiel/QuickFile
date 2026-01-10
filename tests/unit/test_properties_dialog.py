# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from PyQt6.QtWidgets import QDialog

def test_show_properties_dialog_with_file(create_app_handler, mocker):
    MockPropertiesDialog = mocker.patch('app.dialog_handler.PropertiesDialog')
    mock_dialog_instance = MockPropertiesDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted

    # Mock get_file_properties
    mock_get_properties = mocker.patch('app.dialog_handler.get_file_properties')
    mock_get_properties.return_value = {"name": "file.txt", "size": 100}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_current_selected_path.return_value = "/path/to/file.txt"

    app_handler.show_properties_dialog()

    MockPropertiesDialog.assert_called_once()
    mock_get_properties.assert_called_once_with("/path/to/file.txt")

def test_show_properties_dialog_no_selection(create_app_handler, mocker):
    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_current_selected_path.return_value = None
    
    # Expect ValueError to be raised (and caught by decorator)
    # We check if show_error_message is called
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')
    
    app_handler.show_properties_dialog()
    
    mock_show_error.assert_called_once()
