# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
import shutil
import sys
import pytest
import time
from PyQt6.QtCore import QTimer, QEventLoop, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow
from unittest.mock import MagicMock

# Suppress PyQt6.uic debug logs
logging.getLogger("PyQt6.uic").setLevel(logging.WARNING)

# Add the project root directory to sys.path so imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.background_task_manager import BackgroundTaskManager
from app.plugin_manager import PluginManager
from app.task_queue_manager import TaskQueueManager, Task, TaskType
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_manager import FileManager
from ui.main_window import MainWindow
from app.plugin_sandbox import SandboxedPluginWrapper

# Importujemy get_latest_plugin_path
from tests.plugin_helpers import get_latest_plugin_path


# --- Nowe fixtury dla testowania asynchronicznych pluginów ---

class AsyncTestHelper(QObject):
    """
    Helper for testing asynchronous plugin operations.
    Collects signals and provides methods to wait for task completion.
    """
    def __init__(self, plugin_wrapper: SandboxedPluginWrapper, background_task_manager: BackgroundTaskManager):
        super().__init__()
        self.plugin_wrapper = plugin_wrapper
        self.background_task_manager = background_task_manager
        self.received_progress = []
        self.finished_result = None
        self.failed_error = None
        self.task_finished_event = QEventLoop()

        # Connect to plugin_wrapper signals
        self.plugin_wrapper.progress_updated.connect(self._on_progress_updated)
        self.plugin_wrapper.method_finished.connect(self._on_method_finished)
        self.plugin_wrapper.method_failed.connect(self._on_method_failed)
        self.plugin_wrapper.critical_error.connect(self._on_critical_error)

    def _on_progress_updated(self, task_id, percentage):
        self.received_progress.append((task_id, percentage))

    def _on_method_finished(self, task_id, result):
        self.finished_result = (task_id, result)
        self.task_finished_event.exit(0) # Exit the event loop with success code

    def _on_method_failed(self, task_id, error, traceback_str):
        self.failed_error = (task_id, error, traceback_str)
        self.task_finished_event.exit(1) # Exit the event loop with failure code

    def _on_critical_error(self, error_message):
        self.failed_error = ("CRITICAL", error_message, "")
        self.task_finished_event.exit(2) # Exit the event loop with critical error code

    def run_plugin_method_async(self, task: Task, method_name: str, *args, **kwargs):
        """
        Runs a plugin method asynchronously and waits for its completion.
        """
        # Clear previous results
        self.received_progress = []
        self.finished_result = None
        self.failed_error = None

        # Call the method via the wrapper. The wrapper itself returns immediately.
        # The actual execution happens in the sandboxed process.
        method_to_call = getattr(self.plugin_wrapper, method_name)
        method_to_call(task=task, **kwargs) # Pass task as kwarg for async calls

        # Wait for the task to finish (via method_finished or method_failed signal)
        # Use a QTimer to prevent indefinite blocking in case of no signal
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.task_finished_event.exit(3)) # Timeout code
        timer.start(30000) # 30 seconds timeout

        exit_code = self.task_finished_event.exec() # Blocks until exit() is called

        timer.stop() # Stop the timer if task finished before timeout

        if exit_code == 3:
            pytest.fail(f"Timeout waiting for plugin method '{method_name}' to finish for task {task.id}")
        elif exit_code == 1:
            task_id, error, traceback_str = self.failed_error
            # Re-raise the actual exception from the plugin
            # We need to parse the error string to get the exception type if possible
            # For now, we'll just raise a generic Exception with the error message
            raise Exception(f"Plugin method '{method_name}' failed for task {task_id}: {error}\n{traceback_str}")
        elif exit_code == 2:
            task_id, error, traceback_str = self.failed_error
            raise RuntimeError(f"Plugin process critical error for task {task_id}: {error}\n{traceback_str}")
        
        return self.finished_result[1] if self.finished_result else None


@pytest.fixture(scope="session")
def qapp():
    """Provides a single QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(scope="function")
def async_plugin_test_env(qapp, qtbot):
    """
    Provides a setup for testing asynchronous plugin operations.
    Returns a tuple: (plugin_manager, background_task_manager, async_test_helper_factory)
    """
    plugin_manager = PluginManager()
    background_task_manager = BackgroundTaskManager()
    
    # Factory function to create AsyncTestHelper for a specific plugin
    def _async_test_helper_factory(plugin_id: str):
        plugin_wrapper = plugin_manager.get_plugin_by_id(plugin_id)
        if not plugin_wrapper or not isinstance(plugin_wrapper, SandboxedPluginWrapper):
            pytest.fail(f"Plugin '{plugin_id}' not found or not sandboxed.")
        
        # Ensure the plugin is started
        if not plugin_wrapper.process or not plugin_wrapper.process.is_alive():
            plugin_wrapper.start()
            # Give it a moment to fully start
            time.sleep(0.1)
        
        return AsyncTestHelper(plugin_wrapper, background_task_manager)

    yield plugin_manager, background_task_manager, _async_test_helper_factory

    # Teardown: Stop all sandboxed plugins
    plugin_manager.shutdown()
    background_task_manager.thread_pool.waitForDone()


# --- Fixtures for E2E tests ---

@pytest.fixture
def isolated_env(tmp_path_factory):
    """Creates an isolated environment with temporary directories for all E2E tests."""
    base_dir = tmp_path_factory.mktemp("quickfile_test_run")
    
    # --- Setup for all tests ---
    plugin_dir = base_dir / "plugins"
    plugin_dir.mkdir()
    config_dir = base_dir / "config"
    config_dir.mkdir()

    # --- Test-specific directories ---
    search_data_dir = base_dir / "search_data"
    search_data_dir.mkdir()
    (search_data_dir / "found_me.txt").touch()

    source_dir = base_dir / "source"
    source_dir.mkdir()
    (source_dir / "file_to_copy.txt").write_text("This is a test file.")
    destination_dir = base_dir / "destination"
    destination_dir.mkdir()

    sync_source_dir = base_dir / "sync_source"
    sync_source_dir.mkdir()
    (sync_source_dir / "file_to_sync.txt").write_text("Sync me.")
    sync_dest_dir = base_dir / "sync_dest"
    sync_dest_dir.mkdir()

    delete_dir = base_dir / "delete_dir"
    delete_dir.mkdir()
    (delete_dir / "file_to_delete.txt").write_text("Delete me.")

    move_source_dir = base_dir / "move_source"
    move_source_dir.mkdir()
    (move_source_dir / "file_to_move.txt").write_text("Move me.")
    move_dest_dir = base_dir / "move_dest"
    move_dest_dir.mkdir()

    rename_dir = base_dir / "rename_dir"
    rename_dir.mkdir()
    (rename_dir / "file_to_rename.txt").touch()

    creation_dir = base_dir / "creation_dir"
    creation_dir.mkdir()

    # --- Copy bundled plugins ---
    bundled_plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins'))
    if os.path.exists(bundled_plugin_path):
        shutil.copytree(bundled_plugin_path, plugin_dir, dirs_exist_ok=True)

    return {
        "plugin_dir": str(plugin_dir),
        "config_dir": str(config_dir),
        "search_data_dir": str(search_data_dir),
        "source_dir": str(source_dir),
        "destination_dir": str(destination_dir),
        "sync_source_dir": str(sync_source_dir),
        "sync_dest_dir": str(sync_dest_dir),
        "delete_dir": str(delete_dir),
        "move_source_dir": str(move_source_dir),
        "move_dest_dir": str(move_dest_dir),
        "rename_dir": str(rename_dir),
        "creation_dir": str(creation_dir),
    }

@pytest.fixture
def main_window(qapp, qtbot, isolated_env, monkeypatch):
    """Fixture to provide a fully initialized, real MainWindow for E2E tests."""
    def mock_expanduser(path):
        config_dir_str = str(isolated_env["config_dir"])
        if isinstance(path, bytes):
            return config_dir_str.encode('utf-8')
        return config_dir_str
    
    monkeypatch.setattr(os.path, 'expanduser', mock_expanduser)

    background_task_manager = BackgroundTaskManager()
    plugin_manager = PluginManager(plugin_dirs=[isolated_env["plugin_dir"]])
    file_manager = FileManager()
    directory_synchronizer = DirectorySynchronizer()
    
    task_queue_manager = TaskQueueManager(
        file_manager=file_manager,
        directory_synchronizer=directory_synchronizer,
        plugin_manager=plugin_manager,
        background_task_manager=background_task_manager
    )

    window = MainWindow(
        background_task_manager=background_task_manager,
        task_queue_manager=task_queue_manager,
        file_manager=file_manager,
        directory_synchronizer=directory_synchronizer
    )
    
    qtbot.addWidget(window)
    window.show()

    yield window, isolated_env

    # Teardown
    window.close()
    plugin_manager.shutdown()
    background_task_manager.thread_pool.waitForDone()

@pytest.fixture
def handle_modal_dialog():
    """
    A helper fixture to handle modal dialogs in E2E tests.
    It uses a QTimer to run the interaction logic after the dialog appears.
    """
    def _handler(trigger_action, interaction_logic, delay=100):
        QTimer.singleShot(delay, interaction_logic)
        trigger_action.trigger()
    return _handler

# --- Fixtures for older, unit-style tests ---

@pytest.fixture
def create_app_handler(qtbot, mocker):
    """
    Returns a factory function to create a mocked ApplicationLogicHandler.
    """
    def _create():
        from app.application_logic_handler import ApplicationLogicHandler
        from app.ui_state_provider import UIStateProvider
        from app.dialog_handler import DialogHandler
        from app.settings_manager import SettingsManager
        from favorites.favorites_manager import FavoritesManager
        from file_operations.file_comparator import FileComparator
        from app.theme_manager import ThemeManager
        from app.notification_manager import NotificationManager

        mock_main_window = mocker.Mock(spec=QMainWindow)
        mock_main_window.statusBar = mocker.Mock()
        mock_main_window.statusBar().showMessage = mocker.Mock()
        mock_main_window.notification_manager = mocker.Mock(spec=NotificationManager)
        
        mock_file_manager = mocker.Mock(spec=FileManager)
        mock_file_comparator = mocker.Mock(spec=FileComparator)
        mock_favorites_manager = mocker.Mock(spec=FavoritesManager)
        mock_directory_synchronizer = mocker.Mock(spec=DirectorySynchronizer)
        mock_theme_manager = mocker.Mock(spec=ThemeManager)
        
        mock_ui_state_provider = mocker.Mock(spec=UIStateProvider)
        mock_folder_browser = mocker.Mock()
        mock_left_panel = mocker.Mock()
        mock_file_view = mocker.Mock()
        mock_left_panel.file_view = mock_file_view
        mock_folder_browser.left_panel_widget = mock_left_panel
        mock_folder_browser.get_left_panel_widget.return_value = mock_left_panel
        mock_ui_state_provider.folder_browser = mock_folder_browser
        
        mock_settings_handler = mocker.Mock()
        mock_background_task_manager = mocker.Mock(spec=BackgroundTaskManager)
        mock_task_queue_manager = mocker.Mock(spec=TaskQueueManager)
        mock_settings_manager = mocker.Mock(spec=SettingsManager)

        real_dialog_handler = DialogHandler(
            main_window=mock_main_window,
            file_manager=mock_file_manager,
            file_comparator=mock_file_comparator,
            favorites_manager=mock_favorites_manager,
            directory_synchronizer=mock_directory_synchronizer,
            ui_state_provider=mock_ui_state_provider,
            settings_manager=mock_settings_manager,
            background_task_manager=mock_background_task_manager,
            task_queue_manager=mock_task_queue_manager
        )

        handler = ApplicationLogicHandler(
            main_window=mock_main_window,
            file_manager=mock_file_manager,
            file_comparator=mock_file_comparator,
            favorites_manager=mock_favorites_manager,
            directory_synchronizer=mock_directory_synchronizer,
            theme_manager=mock_theme_manager,
            ui_state_provider=mock_ui_state_provider,
            dialog_handler=real_dialog_handler,
            settings_handler=mock_settings_handler,
            background_task_manager=mock_background_task_manager,
            task_queue_manager=mock_task_queue_manager
        )
        
        handler.ui_state_provider = mock_ui_state_provider
        handler.file_manager = mock_file_manager
        
        return handler

    return _create

@pytest.fixture
def app_handler(create_app_handler):
    """Backward compatibility fixture."""
    return create_app_handler()
