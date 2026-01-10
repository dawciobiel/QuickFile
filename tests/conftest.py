# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import shutil
import sys
import pytest
from PyQt6.QtWidgets import QApplication

# Add the project root directory to sys.path so imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.background_task_manager import BackgroundTaskManager
from app.plugin_manager import PluginManager
from app.task_queue_manager import TaskQueueManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_manager import FileManager
from ui.main_window import MainWindow

@pytest.fixture(scope="session")
def qapp():
    """Provides a single QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def isolated_env(tmp_path_factory):
    """Creates an isolated environment with temporary directories for tests."""
    base_dir = tmp_path_factory.mktemp("quickfile_test_run")
    
    plugin_dir = base_dir / "plugins"
    plugin_dir.mkdir()
    
    config_dir = base_dir / "config"
    config_dir.mkdir()

    search_data_dir = base_dir / "search_data"
    search_data_dir.mkdir()
    (search_data_dir / "found_me.txt").touch()
    (search_data_dir / "another_file.log").touch()

    bundled_plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins'))
    if os.path.exists(bundled_plugin_path):
        shutil.copytree(bundled_plugin_path, plugin_dir, dirs_exist_ok=True)

    return {
        "plugin_dir": str(plugin_dir),
        "config_dir": str(config_dir),
        "search_data_dir": str(search_data_dir)
    }

@pytest.fixture
def main_window(qapp, qtbot, isolated_env, monkeypatch):
    """
    Fixture to provide a fully initialized, real MainWindow instance for E2E tests.
    """
    # This mock correctly handles both string and bytes paths, fixing the
    # "Can't mix strings and bytes" TypeError from the send2trash library.
    def mock_expanduser(path):
        config_dir_str = str(isolated_env["config_dir"])
        if isinstance(path, bytes):
            return config_dir_str.encode('utf-8')
        return config_dir_str
    
    monkeypatch.setattr(os.path, 'expanduser', mock_expanduser)

    # Initialize core components with the isolated plugin path
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

    # Create the main window
    window = MainWindow(
        background_task_manager=background_task_manager,
        task_queue_manager=task_queue_manager,
        file_manager=file_manager,
        directory_synchronizer=directory_synchronizer
    )
    
    qtbot.addWidget(window)
    window.show()

    yield window, isolated_env

    window.close()
