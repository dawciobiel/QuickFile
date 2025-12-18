import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QTextEdit
from unittest.mock import MagicMock

# Fixtures (app_handler, MockMainWindow) are now loaded automatically from conftest.py

def test_show_properties_dialog_with_file(qtbot, app_handler, mocker):
    # 1. Przygotowanie danych testowych
    test_file_path = "/tmp/test_file.txt"
    mock_properties = {'Full path': test_file_path, 'Size': '123 bytes'}

    # 2. Mockujemy zależności tej metody
    mock_get_properties = mocker.patch('app.dialog_handler.get_file_properties', return_value=mock_properties)
    MockPropertiesDialog = mocker.patch('app.dialog_handler.PropertiesDialog')
    
    # Ustawiamy ścieżkę, która ma być "zaznaczona"
    app_handler.ui_state_provider.get_current_selected_path = MagicMock(return_value=test_file_path)

    # 3. Wywołanie testowanej metody
    app_handler.dialog_handler.show_properties_dialog()

    # 4. Asercje
    mock_get_properties.assert_called_once_with(test_file_path)
    MockPropertiesDialog.assert_called_once_with(mock_properties, app_handler.main_window)
    MockPropertiesDialog.return_value.exec.assert_called_once()

def test_show_properties_dialog_no_selection(qtbot, app_handler, mocker):
    # Mockujemy zależności tej metody
    mock_get_properties = mocker.patch('app.dialog_handler.get_file_properties')
    MockPropertiesDialog = mocker.patch('app.dialog_handler.PropertiesDialog')
    mock_show_error = mocker.patch('utils.dialogs.show_error_message')

    # Ustawiamy, że żaden plik nie jest "zaznaczony"
    app_handler.ui_state_provider.get_current_selected_path = MagicMock(return_value=None)

    # Wywołanie testowanej metody
    with pytest.raises(ValueError):
        app_handler.dialog_handler.show_properties_dialog()

    # Sprawdzamy, czy NIE próbowano pobrać właściwości ani otworzyć okna
    mock_get_properties.assert_not_called()
    MockPropertiesDialog.assert_not_called()
