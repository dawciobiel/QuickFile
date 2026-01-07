# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from unittest.mock import MagicMock, patch
from app.dialog_handler import DialogHandler

@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to create all necessary mocks for DialogHandler."""
    mocks = {
        "main_window": MagicMock(),
        "file_manager": MagicMock(),
        "file_comparator": MagicMock(),
        "favorites_manager": MagicMock(),
        "directory_synchronizer": MagicMock(),
        "ui_state_provider": MagicMock(),
        "settings_manager": MagicMock(),
        "background_task_manager": MagicMock(),
        "task_queue_manager": MagicMock(),
        "theme_manager": MagicMock(),
    }
    # Mock the translation manager to avoid issues with translations in tests
    mocker.patch('app.dialog_handler.translation_manager.translate', side_effect=lambda _, s: s)
    return mocks

@pytest.fixture
def dialog_handler(mock_dependencies):
    """Fixture to create a DialogHandler instance with mocked dependencies."""
    return DialogHandler(**mock_dependencies)

def test_create_new_file_confirmed(dialog_handler, mocker):
    """Test creating a new file when the user confirms the dialog."""
    # Arrange
    mock_qinput = mocker.patch('app.dialog_handler.QInputDialog.getText', return_value=("new_file.txt", True))
    dialog_handler.ui_state_provider.get_active_panel_path.return_value = "/fake/path"
    
    # Act
    dialog_handler.create_new_file()
    
    # Assert
    mock_qinput.assert_called_once()
    dialog_handler.file_manager.create_file.assert_called_once_with("/fake/path", "new_file.txt")
    dialog_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_create_new_file_cancelled(dialog_handler, mocker):
    """Test that no file is created when the user cancels the dialog."""
    # Arrange
    mocker.patch('app.dialog_handler.QInputDialog.getText', return_value=("", False))
    dialog_handler.ui_state_provider.get_active_panel_path.return_value = "/fake/path"
    
    # Act
    dialog_handler.create_new_file()
    
    # Assert
    dialog_handler.file_manager.create_file.assert_not_called()

def test_create_new_file_with_empty_name(dialog_handler, mocker):
    """Test that no file is created when the user provides an empty name."""
    # Arrange
    mocker.patch('app.dialog_handler.QInputDialog.getText', return_value=("", True))
    dialog_handler.ui_state_provider.get_active_panel_path.return_value = "/fake/path"
    
    # Act
    dialog_handler.create_new_file()
    
    # Assert
    # The call to create_file should not happen if the name is empty, this is handled by the if statement.
    dialog_handler.file_manager.create_file.assert_not_called()

def test_create_new_directory_confirmed(dialog_handler, mocker):
    """Test creating a new directory when the user confirms the dialog."""
    # Arrange
    mocker.patch('app.dialog_handler.QInputDialog.getText', return_value=("new_dir", True))
    dialog_handler.ui_state_provider.get_active_panel_path.return_value = "/fake/path"
    
    # Act
    dialog_handler.create_new_directory()
    
    # Assert
    dialog_handler.file_manager.create_directory.assert_called_once_with("/fake/path", "new_dir")
    dialog_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_rename_selected_item_confirmed(dialog_handler, mocker):
    """Test renaming an item when the user confirms the dialog."""
    # Arrange
    mocker.patch('app.dialog_handler.QInputDialog.getText', return_value=("new_name", True))
    dialog_handler.ui_state_provider.get_current_selected_path.return_value = "/fake/path/old_name"
    
    # Act
    dialog_handler.rename_selected_item()
    
    # Assert
    dialog_handler.file_manager.rename_item.assert_called_once_with("/fake/path/old_name", "new_name")
    dialog_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_rename_selected_item_no_selection(dialog_handler, mocker):
    """Test that rename does nothing if no item is selected."""
    # Arrange
    dialog_handler.ui_state_provider.get_current_selected_path.return_value = None
    mock_qinput = mocker.patch('app.dialog_handler.QInputDialog.getText')
    
    # Act & Assert
    with pytest.raises(ValueError):
        dialog_handler.rename_selected_item()
    
    mock_qinput.assert_not_called()
    dialog_handler.file_manager.rename_item.assert_not_called()

@patch('app.dialog_handler.get_file_properties')
@patch('app.dialog_handler.PropertiesDialog')
def test_show_properties_dialog_successfully(MockPropertiesDialog, mock_get_properties, dialog_handler):
    """Test showing the properties dialog for a selected file."""
    # Arrange
    fake_path = "/fake/path/file.txt"
    fake_properties = {"name": "file.txt", "size": 1024}
    dialog_handler.ui_state_provider.get_current_selected_path.return_value = fake_path
    mock_get_properties.return_value = fake_properties
    
    # Act
    dialog_handler.show_properties_dialog()
    
    # Assert
    mock_get_properties.assert_called_once_with(fake_path)
    MockPropertiesDialog.assert_called_once_with(fake_properties, dialog_handler.main_window)
    MockPropertiesDialog.return_value.exec.assert_called_once()

def test_show_properties_dialog_no_selection(dialog_handler):
    """Test that showing properties raises an error if no file is selected."""
    # Arrange
    dialog_handler.ui_state_provider.get_current_selected_path.return_value = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="No file or folder selected"):
        dialog_handler.show_properties_dialog()
