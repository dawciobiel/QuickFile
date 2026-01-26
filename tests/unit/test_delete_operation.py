# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
import os
from PyQt6.QtWidgets import QDialog

# Dodajemy importy dla nowych testów
from app.task_queue_manager import Task, TaskType
from tests.conftest import async_plugin_test_env

def test_delete_items_to_trash(create_app_handler, mocker):
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"move_to_trash": True}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1", "/path/2"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1", "/path/2"],
        app_handler.task_queue_manager,
        app_handler.background_task_manager,
        app_handler.dialog_handler.theme_manager
    )

def test_delete_items_permanently(create_app_handler, mocker):
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"move_to_trash": False}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once_with(
        app_handler.main_window,
        ["/path/1"],
        app_handler.task_queue_manager,
        app_handler.background_task_manager,
        app_handler.dialog_handler.theme_manager
    )

def test_delete_items_cancelled(create_app_handler, mocker):
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Rejected

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once()
    # TaskQueueManager should NOT be called (we can't easily verify this without mocking TQM inside handler)

def test_delete_items_confirmed(create_app_handler, mocker):
    # This is essentially duplicate of test_delete_items_to_trash but let's keep it consistent
    MockDeleteDialog = mocker.patch('app.dialog_handler.DeleteDialog')
    mock_dialog_instance = MockDeleteDialog.return_value
    mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
    mock_dialog_instance.get_options.return_value = {"move_to_trash": True}

    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = ["/path/1"]

    app_handler.delete_selected_item()

    MockDeleteDialog.assert_called_once()

def test_delete_no_source_selected(create_app_handler, mocker):
    app_handler = create_app_handler()
    app_handler.ui_state_provider.get_selected_paths.return_value = []
    
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')
    
    app_handler.delete_selected_item()
    
    mock_show_error.assert_called_once()

def test_delete_operation_logic(tmp_path, async_plugin_test_env):
    """
    Testuje logikę usuwania pliku z wykorzystaniem asynchronicznej architektury pluginów.
    """
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.standard_operations")

    # 1. Przygotowanie pliku do usunięcia
    file_to_delete = tmp_path / "file_to_delete.txt"
    file_to_delete.write_text("Delete me.")
    
    # 2. Opcje
    options = {
        "move_to_trash": False, # Permanent delete
        "plugin_id": "org.quickfile.standard_operations"
    }
    
    # 3. Tworzenie obiektu Task
    task = Task(TaskType.DELETE, source_paths=[str(file_to_delete)], options=options)
    
    # 4. Uruchomienie usuwania asynchronicznie i czekanie na zakończenie
    async_helper.run_plugin_method_async(
        task,
        "delete_items",
        item_paths=[str(file_to_delete)],
        options=options
    )
    
    # 5. Weryfikacja wyników
    assert not file_to_delete.exists()
