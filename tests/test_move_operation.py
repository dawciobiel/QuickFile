import pytest
from PyQt6.QtWidgets import QDialog
from unittest.mock import MagicMock, call

# Fixtures are now loaded automatically from conftest.py

# --- Tests for Move Operation ---

def test_move_single_item_with_dialog(app_handler, mocker):
    # 1. Przygotowanie
    source_path = "/source/file.txt"
    dest_path = "/dest"
    move_options = {"overwrite": True, "preserve_timestamp": False}

    # 2. Mockowanie
    app_handler.main_window.ui_manager.folder_browser.get_selected_paths.return_value = [source_path]
    mocker.patch.object(app_handler, '_get_inactive_panel_path', return_value=dest_path)

    MockMoveDialog = mocker.patch('app.application_logic_handler.MoveDialog')
    MockMoveDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
    MockMoveDialog.return_value.get_options.return_value = move_options

    # 3. Wywołanie
    app_handler.move_selected_item()

    # 4. Asercje
    MockMoveDialog.assert_called_once_with(app_handler.main_window, source_path, dest_path)
    MockMoveDialog.return_value.exec.assert_called_once()
    app_handler.file_manager.move_item_with_options.assert_called_once_with(source_path, dest_path, move_options)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.main_window.ui_manager.folder_browser.refresh_all_views.assert_called_once()

def test_move_multiple_items(app_handler, mocker):
    # 1. Przygotowanie
    source_paths = ["/source/file1.txt", "/source/dir1"]
    dest_path = "/dest"
    default_options = {"overwrite": False, "preserve_timestamp": True}

    # 2. Mockowanie
    app_handler.main_window.ui_manager.folder_browser.get_selected_paths.return_value = source_paths
    mocker.patch.object(app_handler, '_get_inactive_panel_path', return_value=dest_path)
    MockMoveDialog = mocker.patch('app.application_logic_handler.MoveDialog')

    # 3. Wywołanie
    app_handler.move_selected_item()

    # 4. Asercje
    MockMoveDialog.assert_not_called()
    expected_calls = [call(path, dest_path, default_options) for path in source_paths]
    app_handler.file_manager.move_item_with_options.assert_has_calls(expected_calls, any_order=True)
    assert app_handler.file_manager.move_item_with_options.call_count == len(source_paths)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.main_window.ui_manager.folder_browser.refresh_all_views.assert_called_once()

def test_move_no_source_selected(app_handler, mocker):
    # 1. Mockowanie
    app_handler.main_window.ui_manager.folder_browser.get_selected_paths.return_value = []
    # Mockujemy również get_current_selected_path, ponieważ jest to fallback w logice
    app_handler.main_window.ui_manager.folder_browser.get_current_selected_path.return_value = None
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # 2. Wywołanie
    app_handler.move_selected_item()

    # 3. Asercje
    mock_show_error.assert_called_once()
    app_handler.file_manager.move_item_with_options.assert_not_called()
