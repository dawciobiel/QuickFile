import pytest
from PyQt6.QtWidgets import QDialog
from unittest.mock import MagicMock, call

# Fixtures are now loaded automatically from conftest.py

def test_delete_items_confirmed(app_handler, mocker):
    # 1. Przygotowanie
    source_paths = ["/source/file1.txt", "/source/dir1"]

    # 2. Mockowanie
    app_handler.ui_state_provider.get_selected_paths = MagicMock(return_value=source_paths)
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    MockDeleteDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted

    # 3. Wywołanie
    app_handler.dialog_handler.delete_selected_item()

    # 4. Asercje
    MockDeleteDialog.assert_called_once_with(app_handler.main_window, source_paths)
    expected_calls = [call(path) for path in source_paths]
    app_handler.file_manager.delete_item.assert_has_calls(expected_calls, any_order=True)
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.ui_state_provider.folder_browser.refresh_all_views.assert_called_once()

def test_delete_items_cancelled(app_handler, mocker):
    # 1. Przygotowanie
    source_paths = ["/source/file1.txt"]

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
    mock_show_error = mocker.patch('utils.dialogs.show_error_message')

    # 2. Wywołanie
    with pytest.raises(ValueError):
        app_handler.dialog_handler.delete_selected_item()

    # 3. Asercje
    app_handler.file_manager.delete_item.assert_not_called()
