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
    # Import the class under test inside the fixture to ensure
    # patches are applied before the class is imported.
    from app.application_logic_handler import ApplicationLogicHandler

    # Create the mock window instance
    mock_main_window = MockMainWindow()

    # Mock the translation manager to avoid dealing with translation files
    mocker.patch('app.translation_manager.translation_manager.translate', side_effect=lambda context, text: text)

    # Create the handler instance with mocked dependencies
    handler = ApplicationLogicHandler(
        main_window=mock_main_window,
        file_manager=MagicMock(),
        file_comparator=MagicMock(),
        bookmarks_manager=MagicMock(),
        archive_manager=MagicMock(),
        directory_synchronizer=MagicMock(),
        theme_manager=mock_main_window.theme_manager
    )
    mock_main_window.application_logic_handler = handler
    
    return handler
