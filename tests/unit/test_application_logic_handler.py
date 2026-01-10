# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from unittest.mock import MagicMock, patch
from app.application_logic_handler import ApplicationLogicHandler

@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to create all necessary mocks for ApplicationLogicHandler."""
    mocks = {
        "main_window": MagicMock(),
        "file_manager": MagicMock(),
        "file_comparator": MagicMock(),
        "favorites_manager": MagicMock(),
        "directory_synchronizer": MagicMock(),
        "theme_manager": MagicMock(),
        "ui_state_provider": MagicMock(),
        "dialog_handler": MagicMock(),
        "settings_handler": MagicMock(),
        "background_task_manager": MagicMock(),
        "task_queue_manager": MagicMock(),
    }
    # Mock the translation manager to avoid issues with translations in tests
    mocker.patch('app.application_logic_handler.translation_manager.translate', side_effect=lambda _, s: s)
    return mocks

@pytest.fixture
def app_logic_handler(mock_dependencies):
    """Fixture to create an ApplicationLogicHandler instance with mocked dependencies."""
    # The handler connects a signal in __init__, so we need the mock to have it
    mock_dependencies["task_queue_manager"].task_completed = MagicMock()
    return ApplicationLogicHandler(**mock_dependencies)

def test_add_favorite(app_logic_handler):
    """Test that add_favorite calls the favorites_manager with the correct path."""
    # Arrange
    fake_path = "/home/user/documents"
    app_logic_handler.ui_state_provider.get_active_panel_path.return_value = fake_path
    
    # Act
    app_logic_handler.add_favorite()
    
    # Assert
    app_logic_handler.favorites_manager.add_favorite.assert_called_once_with(fake_path)
    app_logic_handler.main_window.statusBar().showMessage.assert_called_once()

def test_add_favorite_no_path(app_logic_handler):
    """Test that add_favorite does nothing if no path is returned."""
    # Arrange
    app_logic_handler.ui_state_provider.get_active_panel_path.return_value = None
    
    # Act
    app_logic_handler.add_favorite()
    
    # Assert
    app_logic_handler.favorites_manager.add_favorite.assert_not_called()

@patch('app.application_logic_handler.subprocess.Popen')
def test_execute_external_command_with_f_placeholder(mock_popen, app_logic_handler):
    """Test that %f is correctly replaced and quoted."""
    app_logic_handler._execute_external_command("kate %f", "/path/with spaces/file.txt")
    mock_popen.assert_called_once_with('kate "/path/with spaces/file.txt"', shell=True)

@patch('app.application_logic_handler.subprocess.Popen')
def test_execute_external_command_with_d_placeholder(mock_popen, app_logic_handler):
    """Test that %d is correctly replaced and quoted."""
    app_logic_handler._execute_external_command("konsole --workdir %d", "/path/with spaces")
    mock_popen.assert_called_once_with('konsole --workdir "/path/with spaces"', shell=True)

@patch('app.application_logic_handler.subprocess.Popen')
def test_execute_external_command_no_placeholder(mock_popen, app_logic_handler):
    """Test that path is appended and quoted if no placeholder exists."""
    app_logic_handler._execute_external_command("nautilus", "/path/with spaces")
    mock_popen.assert_called_once_with('nautilus "/path/with spaces"', shell=True)

@patch('app.application_logic_handler.subprocess.Popen')
def test_execute_external_command_already_quoted(mock_popen, app_logic_handler):
    """Test that no extra quotes are added if the placeholder is already quoted."""
    app_logic_handler._execute_external_command('kate "%f"', "/path/file.txt")
    mock_popen.assert_called_once_with('kate "/path/file.txt"', shell=True)

@patch('app.application_logic_handler.os.path.isfile', return_value=True)
def test_handle_f3_internal_viewer(mock_isfile, app_logic_handler):
    """Test F3 key uses internal viewer when configured."""
    app_logic_handler.settings_handler.settings_manager.get_setting.return_value = True
    app_logic_handler.ui_state_provider.get_current_selected_path.return_value = "/fake/file.txt"
    
    app_logic_handler._handle_f3_key()
    
    app_logic_handler.dialog_handler.show_file_viewer_dialog.assert_called_once()

@patch('app.application_logic_handler.os.path.isfile', return_value=True)
def test_handle_f3_external_viewer(mock_isfile, app_logic_handler):
    """Test F3 key uses external viewer when configured."""
    app_logic_handler.settings_handler.settings_manager.get_setting.side_effect = [False, "gedit %f"] # First call for use_internal, second for viewer_command
    app_logic_handler.ui_state_provider.get_current_selected_path.return_value = "/fake/file.txt"
    app_logic_handler._execute_external_command = MagicMock() # Mock the internal method
    
    app_logic_handler._handle_f3_key()
    
    app_logic_handler.dialog_handler.show_file_viewer_dialog.assert_not_called()
    app_logic_handler._execute_external_command.assert_called_once_with("gedit %f", "/fake/file.txt")

@patch('app.application_logic_handler.os.path.isfile', return_value=True)
def test_handle_f4_internal_editor(mock_isfile, app_logic_handler):
    """Test F4 key uses internal editor when configured."""
    app_logic_handler.settings_handler.settings_manager.get_setting.return_value = True
    app_logic_handler.ui_state_provider.get_current_selected_path.return_value = "/fake/file.txt"
    
    app_logic_handler._handle_f4_key()
    
    app_logic_handler.dialog_handler.show_file_editor_dialog.assert_called_once()

@patch('app.application_logic_handler.os.path.isfile', return_value=True)
def test_handle_f4_external_editor(mock_isfile, app_logic_handler):
    """Test F4 key uses external editor when configured."""
    app_logic_handler.settings_handler.settings_manager.get_setting.side_effect = [False, "nano %f"]
    app_logic_handler.ui_state_provider.get_current_selected_path.return_value = "/fake/file.txt"
    app_logic_handler._execute_external_command = MagicMock()
    
    app_logic_handler._handle_f4_key()
    
    app_logic_handler.dialog_handler.show_file_editor_dialog.assert_not_called()
    app_logic_handler._execute_external_command.assert_called_once_with("nano %f", "/fake/file.txt")

@patch('app.application_logic_handler.SelectDialog')
def test_show_select_dialog_selects_files(MockSelectDialog, app_logic_handler):
    """Test that show_select_dialog correctly filters and selects files."""
    # Arrange
    mock_dialog_instance = MockSelectDialog.return_value
    mock_dialog_instance.exec.return_value = True
    mock_dialog_instance.get_selection_options.return_value = {
        "pattern": "*.txt",
        "case_sensitive": True,
        "only_files": True
    }

    mock_view = MagicMock()
    mock_model = MagicMock()
    mock_view.model = mock_model
    app_logic_handler.ui_state_provider.get_active_panel_view.return_value = mock_view

    # Mock the model's items
    model_items = [
        {"name": "file1.txt", "path": "/path/file1.txt", "is_dir": False},
        {"name": "image.jpg", "path": "/path/image.jpg", "is_dir": False},
        {"name": "file2.txt", "path": "/path/file2.txt", "is_dir": False},
    ]
    
    mock_model.rowCount.return_value = len(model_items)
    
    def get_mock_index(row, col):
        mock_index = MagicMock()
        mock_index.row.return_value = row
        mock_index.column.return_value = col
        return mock_index
        
    mock_model.index.side_effect = get_mock_index
    mock_model.fileName.side_effect = lambda index: model_items[index.row()]["name"]
    mock_model.filePath.side_effect = lambda index: model_items[index.row()]["path"]
    mock_model.isDir.side_effect = lambda index: model_items[index.row()]["is_dir"]

    # Act
    app_logic_handler.show_select_dialog()

    # Assert
    MockSelectDialog.assert_called_once()
    mock_view.select_items_by_paths.assert_called_once_with(["/path/file1.txt", "/path/file2.txt"])

@patch('app.application_logic_handler.SelectDialog')
def test_show_select_dialog_cancelled(MockSelectDialog, app_logic_handler):
    """Test that show_select_dialog does nothing if cancelled."""
    # Arrange
    mock_dialog_instance = MockSelectDialog.return_value
    mock_dialog_instance.exec.return_value = False # User cancels
    mock_view = MagicMock()
    app_logic_handler.ui_state_provider.get_active_panel_view.return_value = mock_view

    # Act
    app_logic_handler.show_select_dialog()

    # Assert
    mock_view.select_items_by_paths.assert_not_called()
