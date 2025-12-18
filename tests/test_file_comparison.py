import pytest
from PyQt6.QtWidgets import QDialog, QMessageBox
from unittest.mock import MagicMock, call
import os

# Fixtures (app_handler) are now loaded automatically from conftest.py

def test_compare_no_selection(app_handler, mocker):
    # 1. Przygotowanie
    # Mock the specific methods that return the selected paths
    mocker.patch.object(app_handler.ui_state_provider.folder_browser.left_panel_widget.file_view, 'get_current_path', return_value=None)
    mocker.patch.object(app_handler.ui_state_provider.folder_browser.right_panel_widget.file_view, 'get_current_path', return_value="/path/to/right")
    
    mock_qmessagebox_warning = mocker.patch('app.application_logic_handler.QMessageBox.warning')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercje
    mock_qmessagebox_warning.assert_called_once_with(
        app_handler.main_window,
        "Comparison Error",
        "Please select items in both panels to compare."
    )

def test_compare_file_with_directory_error(app_handler, mocker):
    # 1. Przygotowanie
    file_path = "/path/to/file.txt"
    dir_path = "/path/to/dir"

    mocker.patch.object(app_handler.ui_state_provider.folder_browser.left_panel_widget.file_view, 'get_current_path', return_value=file_path)
    mocker.patch.object(app_handler.ui_state_provider.folder_browser.right_panel_widget.file_view, 'get_current_path', return_value=dir_path)

    mocker.patch('os.path.isdir', side_effect=lambda p: p == dir_path)
    mocker.patch('os.path.isfile', side_effect=lambda p: p == file_path)
    mock_qmessagebox_warning = mocker.patch('app.application_logic_handler.QMessageBox.warning')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercje
    mock_qmessagebox_warning.assert_called_once_with(
        app_handler.main_window,
        "Comparison Error",
        "Cannot compare a file with a directory. Please select two files or two directories."
    )

def test_compare_identical_files(app_handler, mocker):
    # 1. Przygotowanie
    file1_path = "/path/to/file1.txt"
    file2_path = "/path/to/file2.txt"

    mocker.patch.object(app_handler.ui_state_provider.folder_browser.left_panel_widget.file_view, 'get_current_path', return_value=file1_path)
    mocker.patch.object(app_handler.ui_state_provider.folder_browser.right_panel_widget.file_view, 'get_current_path', return_value=file2_path)

    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('os.path.isfile', return_value=True)
    app_handler.file_comparator.compare_files.return_value = True

    mock_qmessagebox_information = mocker.patch('app.dialog_handler.QMessageBox.information')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercje
    app_handler.file_comparator.compare_files.assert_called_once_with(file1_path, file2_path)
    mock_qmessagebox_information.assert_called_once()

def test_compare_different_files(app_handler, mocker):
    # 1. Przygotowanie
    file1_path = "/path/to/file1.txt"
    file2_path = "/path/to/file2.txt"

    mocker.patch.object(app_handler.ui_state_provider.folder_browser.left_panel_widget.file_view, 'get_current_path', return_value=file1_path)
    mocker.patch.object(app_handler.ui_state_provider.folder_browser.right_panel_widget.file_view, 'get_current_path', return_value=file2_path)

    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('os.path.isfile', return_value=True)
    app_handler.file_comparator.compare_files.return_value = False

    mock_qmessagebox_information = mocker.patch('app.dialog_handler.QMessageBox.information')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercje
    app_handler.file_comparator.compare_files.assert_called_once_with(file1_path, file2_path)
    mock_qmessagebox_information.assert_called_once()

def test_compare_directories_with_dialog(app_handler, mocker):
    # 1. Przygotowanie
    dir1_path = "/path/to/dir1"
    dir2_path = "/path/to/dir2"
    mock_dircmp_obj = MagicMock()
    mock_report = "Comparison Report"

    mocker.patch.object(app_handler.ui_state_provider.folder_browser.left_panel_widget.file_view, 'get_current_path', return_value=dir1_path)
    mocker.patch.object(app_handler.ui_state_provider.folder_browser.right_panel_widget.file_view, 'get_current_path', return_value=dir2_path)

    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.isfile', return_value=False)
    app_handler.file_comparator.compare_directories.return_value = mock_dircmp_obj
    app_handler.file_comparator.get_directory_comparison_report.return_value = mock_report

    MockCompareDialog = mocker.patch('app.dialog_handler.CompareDialog')
    MockCompareDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercje
    app_handler.file_comparator.compare_directories.assert_called_once_with(dir1_path, dir2_path)
    MockCompareDialog.assert_called_once_with(app_handler.main_window, mock_report, dir1_path, dir2_path)
    MockCompareDialog.return_value.exec.assert_called_once()
