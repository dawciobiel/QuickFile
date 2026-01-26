# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
import os
from PyQt6.QtWidgets import QDialog

# Dodajemy importy dla nowych testów
from app.task_queue_manager import Task, TaskType
from tests.conftest import async_plugin_test_env

def test_copy_single_item_with_dialog(create_app_handler, mocker):
    # Patch CopyDialog BEFORE creating the handler
    MockCopyDialog = mocker.patch('app.dialog_handler.CopyDialog')
    mock_dialog_instance = MockCopyDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"overwrite": False}

    # Create handler
    app_handler = create_app_handler()

    # Setup mocks
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/to/source"]
    app_handler.ui_state_provider.get_inactive_panel_path.return_value = "/path/to/dest"

    # Execute
    app_handler.copy_selected_item()

    # Assert
    MockCopyDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/to/source"],
        "/path/to/dest",
        app_handler.task_queue_manager,
        app_handler.background_task_manager,
        app_handler.dialog_handler.theme_manager
    )

def test_copy_multiple_items(create_app_handler, mocker):
    MockCopyDialog = mocker.patch('app.dialog_handler.CopyDialog')
    mock_dialog_instance = MockCopyDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"overwrite": True}

    app_handler = create_app_handler()

    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1", "/path/2"]
    app_handler.ui_state_provider.get_inactive_panel_path.return_value = "/dest"

    app_handler.copy_selected_item()

    MockCopyDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1", "/path/2"],
        "/dest",
        app_handler.task_queue_manager,
        app_handler.background_task_manager,
        app_handler.dialog_handler.theme_manager
    )

def test_copy_no_source_selected(create_app_handler, mocker):
    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = []
    
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')
    
    app_handler.copy_selected_item()
    
    mock_show_error.assert_called_once()

def test_copy_operation_logic(tmp_path, async_plugin_test_env):
    """
    Testuje logikę kopiowania pliku z wykorzystaniem asynchronicznej architektury pluginów.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.standard_operations")

    # 1. Przygotowanie pliku źródłowego i katalogu docelowego
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "file_to_copy.txt"
    source_file.write_text("This is a test file.")
    
    dest_dir = tmp_path / "destination"
    dest_dir.mkdir()

    # 2. Opcje
    options = {
        "overwrite": False,
        "plugin_id": "org.quickfile.standard_operations"
    }
    
    # 3. Tworzenie obiektu Task
    task = Task(TaskType.COPY, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)
    
    # 4. Uruchomienie kopiowania asynchronicznie i czekanie na zakończenie
    async_helper.run_plugin_method_async(
        task,
        "copy_items",
        source_paths=[str(source_file)],
        destination_path=str(dest_dir),
        options=options
    )
    
    # 5. Weryfikacja wyników
    dest_file = dest_dir / "file_to_copy.txt"
    assert dest_file.exists()
    assert dest_file.read_text() == "This is a test file."
