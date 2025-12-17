import pytest
from PyQt6.QtWidgets import QDialog
from unittest.mock import MagicMock, call

# Fixtures are now loaded automatically from conftest.py

def test_copy_single_item_with_dialog(app_handler, mocker):
    # 1. Przygotowanie
    source_path = "/source/file.txt"
    dest_path = "/dest"
    copy_options = {"overwrite": True, "preserve_timestamp": False}

    # 2. Mockowanie
    # Mockujemy metody dostępu do UI
    app_handler.main_window.ui_manager.folder_browser.get_selected_paths.return_value = [source_path]
    mocker.patch.object(app_handler, '_get_inactive_panel_path', return_value=dest_path)

    # Mockujemy dialog i jego zachowanie
    MockCopyDialog = mocker.patch('app.application_logic_handler.CopyDialog')
    MockCopyDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
    MockCopyDialog.return_value.get_options.return_value = copy_options

    # 3. Wywołanie
    app_handler.copy_selected_item()

    # 4. Asercje
    # Sprawdź, czy dialog został utworzony i pokazany
    MockCopyDialog.assert_called_once_with(app_handler.main_window, source_path, dest_path)
    MockCopyDialog.return_value.exec.assert_called_once()

    # Sprawdź, czy operacja kopiowania została wywołana z opcjami z dialogu
    app_handler.file_manager.copy_item_with_options.assert_called_once_with(source_path, dest_path, copy_options)
    
    # Sprawdź, czy pasek stanu i widok zostały odświeżone
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.main_window.ui_manager.folder_browser.refresh_all_views.assert_called_once()

def test_copy_multiple_items(app_handler, mocker):
    # 1. Przygotowanie
    source_paths = ["/source/file1.txt", "/source/dir1"]
    dest_path = "/dest"
    default_options = {"overwrite": False, "preserve_timestamp": True}

    # 2. Mockowanie
    app_handler.main_window.ui_manager.folder_browser.get_selected_paths.return_value = source_paths
    mocker.patch.object(app_handler, '_get_inactive_panel_path', return_value=dest_path)
    MockCopyDialog = mocker.patch('app.application_logic_handler.CopyDialog')

    # 3. Wywołanie
    app_handler.copy_selected_item()

    # 4. Asercje
    # Sprawdź, czy dialog NIE został pokazany
    MockCopyDialog.assert_not_called()

    # Sprawdź, czy operacja kopiowania została wywołana dla każdego pliku z domyślnymi opcjami
    expected_calls = [call(path, dest_path, default_options) for path in source_paths]
    app_handler.file_manager.copy_item_with_options.assert_has_calls(expected_calls, any_order=True)
    assert app_handler.file_manager.copy_item_with_options.call_count == len(source_paths)

    # Sprawdź, czy pasek stanu i widok zostały odświeżone
    app_handler.main_window.statusBar().showMessage.assert_called_once()
    app_handler.main_window.ui_manager.folder_browser.refresh_all_views.assert_called_once()

def test_copy_no_source_selected(app_handler, mocker):
    # 1. Mockowanie
    app_handler.main_window.ui_manager.folder_browser.get_selected_paths.return_value = []
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # 2. Wywołanie
    app_handler.copy_selected_item()

    # 3. Asercje
    # Sprawdź, czy pokazano błąd
    mock_show_error.assert_called_once()
    # Sprawdź, czy NIE próbowano kopiować
    app_handler.file_manager.copy_item_with_options.assert_not_called()
