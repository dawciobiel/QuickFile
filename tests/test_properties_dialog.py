import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QTextEdit
from unittest.mock import MagicMock

# Fixtures (app_handler, MockMainWindow) are now loaded automatically from conftest.py

def test_show_properties_dialog_with_file(qtbot, app_handler, mocker):
    # 1. Przygotowanie danych testowych
    test_file_path = "/tmp/test_file.txt"
    mock_properties = {'Full path': test_file_path, 'Size': '123 bytes'}

    # 2. Mockujemy zależności tej metody
    mock_get_properties = mocker.patch('app.application_logic_handler.get_file_properties', return_value=mock_properties)
    MockPropertiesDialog = mocker.patch('app.application_logic_handler.PropertiesDialog')
    
    # Ustawiamy ścieżkę, która ma być "zaznaczona"
    app_handler.main_window.ui_manager.folder_browser.get_current_selected_path.return_value = test_file_path

    # 3. Wywołanie testowanej metody
    app_handler.show_properties_dialog()

    # 4. Asercje
    mock_get_properties.assert_called_once_with(test_file_path)
    MockPropertiesDialog.assert_called_once_with(mock_properties, app_handler.main_window)
    MockPropertiesDialog.return_value.exec.assert_called_once()

def test_show_properties_dialog_no_selection(qtbot, app_handler, mocker):
    # Mockujemy zależności tej metody
    mock_get_properties = mocker.patch('app.application_logic_handler.get_file_properties')
    MockPropertiesDialog = mocker.patch('app.application_logic_handler.PropertiesDialog')
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # Ustawiamy, że żaden plik nie jest "zaznaczony"
    app_handler.main_window.ui_manager.folder_browser.get_current_selected_path.return_value = None

    # Wywołanie testowanej metody
    app_handler.show_properties_dialog()

    # Sprawdzamy, czy pokazano błąd
    mock_show_error.assert_called_once_with(
        app_handler.main_window,
        "Properties Error",
        "No file or folder selected."
    )
    mock_get_properties.assert_not_called()
    MockPropertiesDialog.assert_not_called()
