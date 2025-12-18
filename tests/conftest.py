import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QWidget

# --- Reusable Mocks and Fixtures for the entire test suite ---

class MockMainWindow(QWidget):
    """
    A mock MainWindow that inherits from QWidget to be a valid parent 
    for other Qt objects and has MagicMock attributes for its components.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder_browser = MagicMock()
        self._status_bar = MagicMock()
        self.settings_manager = MagicMock()
        self.theme_manager = MagicMock()
        self.ui_manager = MagicMock()
        self.search_input = MagicMock() # Dodano search_input
        self.application_logic_handler = None

        # Ensure ui_manager has a folder_browser attribute
        self.ui_manager.folder_browser = self.folder_browser

    def statusBar(self):
        """Mocks the statusBar() method of QMainWindow."""
        return self._status_bar

@pytest.fixture
def app_handler(qtbot, mocker):
    """
    Provides a fully mocked ApplicationLogicHandler instance for testing.
    - Mocks external dependencies like file managers and dialogs.
    - Uses a MockMainWindow that behaves like the real window for parenting.
    """
    # Import necessary classes inside the fixture
    from app.application_logic_handler import ApplicationLogicHandler
    from app.ui_state_provider import UIStateProvider
    from app.dialog_handler import DialogHandler
    from app.settings_handler import SettingsHandler
    from bookmarks.bookmarks_manager import BookmarksManager
    from file_operations.file_manager import FileManager
    from file_operations.file_comparator import FileComparator
    from file_operations.archive_manager import ArchiveManager
    from file_operations.directory_synchronizer import DirectorySynchronizer


    # Create the mock window instance
    mock_main_window = MockMainWindow()

    # Mock the translation manager
    mocker.patch('app.translation_manager.translation_manager.translate', side_effect=lambda context, text: text)

    # Create mocks for managers that DialogHandler and ApplicationLogicHandler depend on
    mock_file_manager = MagicMock(spec=FileManager)
    mock_file_comparator = MagicMock(spec=FileComparator)
    mock_bookmarks_manager = MagicMock(spec=BookmarksManager)
    mock_archive_manager = MagicMock(spec=ArchiveManager)
    mock_directory_synchronizer = MagicMock(spec=DirectorySynchronizer)
    mock_theme_manager = MagicMock() # Use a mock for theme_manager here

    # Create instances of the new handlers, passing mocks as dependencies
    mock_ui_state_provider = UIStateProvider(mock_main_window.ui_manager.folder_browser)
    mock_settings_manager = MagicMock() # Mock SettingsManager directly
    mock_shortcuts_manager = MagicMock() # Mock ShortcutsManager directly
    mock_settings_handler = SettingsHandler(mock_main_window, mock_settings_manager, mock_shortcuts_manager, mock_theme_manager)

    mock_dialog_handler = DialogHandler(
        main_window=mock_main_window,
        file_manager=mock_file_manager,
        file_comparator=mock_file_comparator,
        bookmarks_manager=mock_bookmarks_manager,
        archive_manager=mock_archive_manager,
        directory_synchronizer=mock_directory_synchronizer,
        ui_state_provider=mock_ui_state_provider,
        settings_handler=mock_settings_handler
    )

    # Create the main handler instance
    handler = ApplicationLogicHandler(
        main_window=mock_main_window,
        file_manager=mock_file_manager,
        file_comparator=mock_file_comparator,
        bookmarks_manager=mock_bookmarks_manager,
        archive_manager=mock_archive_manager,
        directory_synchronizer=mock_directory_synchronizer,
        theme_manager=mock_theme_manager,
        ui_state_provider=mock_ui_state_provider,
        dialog_handler=mock_dialog_handler,
        settings_handler=mock_settings_handler
    )
    mock_main_window.application_logic_handler = handler
    
    # Attach mocks to the handler for easy access in tests
    handler.file_manager = mock_file_manager
    handler.file_comparator = mock_file_comparator
    handler.bookmarks_manager = mock_bookmarks_manager
    handler.archive_manager = mock_archive_manager
    handler.directory_synchronizer = mock_directory_synchronizer
    handler.theme_manager = mock_theme_manager
    handler.ui_state_provider = mock_ui_state_provider
    handler.dialog_handler = mock_dialog_handler
    handler.settings_handler = mock_settings_handler

    return handler
