import pytest
from unittest.mock import MagicMock

# Fixtures are now loaded automatically from conftest.py

def test_file_search_with_valid_path(app_handler, mocker):
    # 1. Przygotowanie
    search_path = "/some/test/path"
    search_term = "nohup.out"
    search_results = ["/some/test/path/nohup.out"]
    
    # 2. Mockowanie
    app_handler.ui_state_provider.get_active_panel_path = MagicMock(return_value=search_path)
    app_handler.main_window.search_input.text.return_value = search_term
    app_handler.file_manager.search_files.return_value = (search_results, "Found 1 item.")
    
    mock_show_search_results = mocker.patch.object(app_handler.dialog_handler, 'show_search_results')

    # 3. Wywołanie
    app_handler.start_file_search()

    # 4. Asercje
    app_handler.file_manager.search_files.assert_called_once_with(search_path, search_term)
    mock_show_search_results.assert_called_once_with(search_results)
    app_handler.main_window.statusBar().showMessage.assert_called_once_with("Found 1 item.")

def test_file_search_with_none_path(app_handler, mocker):
    # 1. Mockowanie
    app_handler.ui_state_provider.get_active_panel_path = MagicMock(return_value=None)
    app_handler.main_window.search_input.text.return_value = "nohup.out"
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # 2. Wywołanie
    app_handler.start_file_search()

    # 3. Asercje
    app_handler.file_manager.search_files.assert_not_called()
    mock_show_error.assert_called_once()

def test_file_search_empty_search_text(app_handler, mocker):
    # 1. Mockowanie
    app_handler.main_window.search_input.text.return_value = "" # Empty search text
    
    # 2. Wywołanie
    app_handler.start_file_search()

    # 3. Asercje
    app_handler.file_manager.search_files.assert_not_called()
    app_handler.main_window.statusBar().showMessage.assert_called_once_with("Enter text to search.")
