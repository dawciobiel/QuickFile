import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication, QMainWindow
from unittest.mock import MagicMock

# Add the project root directory to sys.path so imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def qapp():
    """
    Fixture to provide a QApplication instance.
    PyQt requires a QApplication to be running for widgets to work.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def main_window(qapp, qtbot):
    """
    Fixture to provide a mocked MainWindow.
    """
    window = QMainWindow()
    qtbot.addWidget(window)
    return window

@pytest.fixture
def create_app_handler(qtbot, mocker):
    """
    Returns a factory function to create ApplicationLogicHandler.
    This allows tests to patch dependencies (like Dialog classes) BEFORE the handler is created.
    """
    def _create():
        # Import necessary classes inside the fixture
        from app.application_logic_handler import ApplicationLogicHandler
        from app.ui_state_provider import UIStateProvider
        from app.dialog_handler import DialogHandler
        from app.settings_manager import SettingsManager
        from favorites.favorites_manager import FavoritesManager
        from file_operations.file_manager import FileManager
        from file_operations.file_comparator import FileComparator
        from file_operations.directory_synchronizer import DirectorySynchronizer
        from app.theme_manager import ThemeManager
        from app.background_task_manager import BackgroundTaskManager
        from app.task_queue_manager import TaskQueueManager

        # Mock MainWindow
        mock_main_window = mocker.Mock(spec=QMainWindow)
        mock_main_window.statusBar = mocker.Mock()
        mock_main_window.statusBar().showMessage = mocker.Mock()
        
        # Mock dependencies
        mock_file_manager = mocker.Mock(spec=FileManager)
        mock_file_comparator = mocker.Mock(spec=FileComparator)
        mock_favorites_manager = mocker.Mock(spec=FavoritesManager)
        mock_directory_synchronizer = mocker.Mock(spec=DirectorySynchronizer)
        mock_theme_manager = mocker.Mock(spec=ThemeManager)
        
        # Mock UIStateProvider with nested structure
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

        # Create REAL DialogHandler with mocks
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

        # Create the handler with mocks and the real dialog handler
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
        
        # Attach dependencies to handler for easy access in tests
        handler.ui_state_provider = mock_ui_state_provider
        handler.file_manager = mock_file_manager
        
        return handler

    return _create

@pytest.fixture
def app_handler(create_app_handler):
    """
    Backward compatibility fixture for tests that don't need delayed creation.
    """
    return create_app_handler()
