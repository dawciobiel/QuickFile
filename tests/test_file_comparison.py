import pytest
from PyQt6.QtWidgets import QDialog

def test_compare_no_selection(create_app_handler, mocker):
    # 1. Przygotowanie
    app_handler = create_app_handler()
    
    # Mock get_selected_paths to return empty list or list with wrong number of items
    app_handler.ui_state_provider.get_selected_paths.return_value = []

    # Mock show_error_message instead of QMessageBox directly
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercja
    mock_show_error.assert_called_once()

def test_compare_file_with_directory_error(create_app_handler, mocker):
    # 1. Przygotowanie
    app_handler = create_app_handler()
    file_path = "/path/to/file.txt"
    dir_path = "/path/to/dir"

    app_handler.ui_state_provider.get_selected_paths.return_value = [file_path, dir_path]

    mocker.patch('os.path.isdir', side_effect=lambda p: p == dir_path)
    mocker.patch('os.path.isfile', side_effect=lambda p: p == file_path)

    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercja
    mock_show_error.assert_called_once()

def test_compare_identical_files(create_app_handler, mocker):
    # 1. Przygotowanie
    app_handler = create_app_handler()
    file1_path = "/path/to/file1.txt"
    file2_path = "/path/to/file2.txt"

    app_handler.ui_state_provider.get_selected_paths.return_value = [file1_path, file2_path]

    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('os.path.isfile', return_value=True)
    app_handler.file_comparator.compare_files.return_value = True

    mock_qmessagebox_information = mocker.patch('app.dialog_handler.QMessageBox.information')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercja
    app_handler.file_comparator.compare_files.assert_called_once_with(file1_path, file2_path)
    mock_qmessagebox_information.assert_called_once()
    assert "identical" in mock_qmessagebox_information.call_args[0][2]

def test_compare_different_files(create_app_handler, mocker):
    # 1. Przygotowanie
    app_handler = create_app_handler()
    file1_path = "/path/to/file1.txt"
    file2_path = "/path/to/file2.txt"

    app_handler.ui_state_provider.get_selected_paths.return_value = [file1_path, file2_path]

    mocker.patch('os.path.isdir', return_value=False)
    mocker.patch('os.path.isfile', return_value=True)
    app_handler.file_comparator.compare_files.return_value = False

    mock_qmessagebox_information = mocker.patch('app.dialog_handler.QMessageBox.information')

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercja
    app_handler.file_comparator.compare_files.assert_called_once_with(file1_path, file2_path)
    mock_qmessagebox_information.assert_called_once()
    assert "different" in mock_qmessagebox_information.call_args[0][2]

def test_compare_directories_with_dialog(create_app_handler, mocker):
    # 1. Przygotowanie
    app_handler = create_app_handler()
    dir1_path = "/path/to/dir1"
    dir2_path = "/path/to/dir2"
    mock_dircmp_obj = mocker.MagicMock()
    mock_report = "Comparison Report"

    app_handler.ui_state_provider.get_selected_paths.return_value = [dir1_path, dir2_path]

    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.isfile', return_value=False)
    app_handler.file_comparator.compare_directories.return_value = mock_dircmp_obj
    app_handler.file_comparator.get_directory_comparison_report.return_value = mock_report

    MockCompareDialog = mocker.patch('app.dialog_handler.CompareDialog')
    MockCompareDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted

    # 2. Wywołanie
    app_handler.compare_selected_items()

    # 3. Asercja
    app_handler.file_comparator.compare_directories.assert_called_once_with(dir1_path, dir2_path)
    app_handler.file_comparator.get_directory_comparison_report.assert_called_once_with(mock_dircmp_obj)
    MockCompareDialog.assert_called_once_with(app_handler.main_window, mock_report, dir1_path, dir2_path)
