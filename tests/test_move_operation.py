import pytest
from PyQt6.QtWidgets import QDialog
from unittest.mock import MagicMock, call

# Fixtures are now loaded automatically from conftest.py

def test_move_single_item_with_dialog(app_handler, mocker):
    # 1. Przygotowanie
    source_path = "/source/file.txt"
    dest_path = "/dest"
    move_options = {"overwrite": True, "preserve_timestamp": False}

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=[source_path])
    app_handler.ui_state_provider.get_inactive_panel_path = MagicMock(return_value=dest_path)

    MockMoveDialog = mocker.patch('app.dialog_handler.MoveDialog')
    MockMoveDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
    MockMoveDialog.return_value.get_options.return_value = move_options

    # 3. Wywołanie
    app_handler.dialog_handler.move_selected_item()

    # 4. Asercje
    MockMoveDialog.assert_called_once_with(app_handler.main_window, source_path, dest_path)
    app_handler.file_manager.move_item_with_options.assert_called_once_with(source_path, dest_path, move_options)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_move_multiple_items(app_handler, mocker):
    # 1. Przygotowanie
    source_paths = ["/source/file1.txt", "/source/dir1"]
    dest_path = "/dest"
    default_options = {"overwrite": False, "preserve_timestamp": True}

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=source_paths)
    app_handler.ui_state_provider.get_inactive_panel_path = MagicMock(return_value=dest_path)
    MockMoveDialog = mocker.patch('app.dialog_handler.MoveDialog')

    # 3. Wywołanie
    app_handler.dialog_handler.move_selected_item()

    # 4. Asercje
    MockMoveDialog.assert_not_called()
    expected_calls = [call(path, dest_path, default_options) for path in source_paths]
    app_handler.file_manager.move_item_with_options.assert_has_calls(expected_calls, any_order=True)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_move_no_source_selected(app_handler, mocker):
    # 1. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=[])
    app_handler.ui_state_provider.get_current_selected_path = MagicMock(return_value=None)
    mock_show_error = mocker.patch('utils.dialogs.show_error_message')

    # 2. Wywołanie
    with pytest.raises(ValueError):
        app_handler.dialog_handler.move_selected_item()

    # 3. Asercje
    app_handler.file_manager.move_item_with_options.assert_not_called()
