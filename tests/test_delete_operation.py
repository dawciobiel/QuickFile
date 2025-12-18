import pytest
from PyQt6.QtWidgets import QDialog
from unittest.mock import MagicMock, call, patch
import os

# Fixtures are now loaded automatically from conftest.py

@pytest.fixture
def create_dummy_file(tmp_path):
    def _create_dummy_file(file_name="test_file.txt", content="test content"):
        file_path = tmp_path / file_name
        file_path.write_text(content)
        return str(file_path)
    return _create_dummy_file

@pytest.fixture
def create_dummy_dir(tmp_path):
    def _create_dummy_dir(dir_name="test_dir"):
        dir_path = tmp_path / dir_name
        dir_path.mkdir()
        return str(dir_path)
    return _create_dummy_dir

def test_delete_items_confirmed(app_handler, mocker, create_dummy_file, create_dummy_dir):
    # 1. Przygotowanie
    file_path = create_dummy_file("file1.txt")
    dir_path = create_dummy_dir("dir1")
    source_paths = [file_path, dir_path]

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=source_paths)
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    
    # Mock the dialog instance and its should_move_to_trash method
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.should_move_to_trash.return_value = True # Default behavior: move to trash

    # 3. Wywołanie
    app_handler.dialog_handler.delete_selected_item()

    # 4. Asercje
    MockDeleteDialog.assert_called_once_with(app_handler.main_window, source_paths)
    mock_dialog_instance.should_move_to_trash.assert_called_once() # Ensure this method was called
    
    expected_calls = [call(path, move_to_trash=True) for path in source_paths]
    app_handler.file_manager.delete_item.assert_has_calls(expected_calls, any_order=True)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_delete_items_cancelled(app_handler, mocker):
    # 1. Przygotowanie
    source_paths = ["/source/file1.txt"] # Path doesn't need to exist as delete_item won't be called

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=source_paths)
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    MockDeleteDialog.return_value.exec.return_value = QDialog.DialogCode.Rejected

    # 3. Wywołanie
    app_handler.dialog_handler.delete_selected_item()

    # 4. Asercje
    MockDeleteDialog.assert_called_once_with(app_handler.main_window, source_paths)
    app_handler.file_manager.delete_item.assert_not_called()
    app_handler.main_window.statusBar().showMessage.assert_not_called()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_not_called()

def test_delete_no_source_selected(app_handler, mocker):
    # 1. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=[])
    # mock_show_error = mocker.patch('utils.dialogs.show_error_message') # Not needed as ValueError is raised

    # 2. Wywołanie
    with pytest.raises(ValueError):
        app_handler.dialog_handler.delete_selected_item()

    # 3. Asercje
    app_handler.file_manager.delete_item.assert_not_called()

def test_delete_items_to_trash(app_handler, mocker, create_dummy_file):
    # 1. Przygotowanie
    file_path = create_dummy_file("file_to_trash.txt")
    source_paths = [file_path]

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=source_paths)
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.should_move_to_trash.return_value = True # User wants to move to trash

    # 3. Wywołanie
    app_handler.dialog_handler.delete_selected_item()

    # 4. Asercje
    mock_dialog_instance.should_move_to_trash.assert_called_once()
    app_handler.file_manager.delete_item.assert_called_once_with(file_path, move_to_trash=True)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_delete_items_permanently(app_handler, mocker, create_dummy_file):
    # 1. Przygotowanie
    file_path = create_dummy_file("file_to_delete_permanently.txt")
    source_paths = [file_path]

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=source_paths)
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.should_move_to_trash.return_value = False # User wants to delete permanently

    # 3. Wywołanie
    app_handler.dialog_handler.delete_selected_item()

    # 4. Asercje
    mock_dialog_instance.should_move_to_trash.assert_called_once()
    app_handler.file_manager.delete_item.assert_called_once_with(file_path, move_to_trash=False)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()
