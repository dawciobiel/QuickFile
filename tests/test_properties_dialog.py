import pytest
from PyQt6.QtWidgets import QApplication, QDialog, QTextEdit, QLabel, QDialogButtonBox, QWidget
from PyQt6.QtCore import Qt
from unittest.mock import MagicMock

# Klasa mockująca MainWindow, która dziedziczy po QWidget
class MockMainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder_browser = MagicMock()
        self.status_bar = MagicMock()
        self.settings_manager = MagicMock()
        self.theme_manager = MagicMock()
        self.application_logic_handler = None

# Fixture do przygotowania ApplicationLogicHandler
@pytest.fixture
def app_handler(qtbot, mocker):
    # Importujemy ApplicationLogicHandler TUTAJ, aby uniknąć problemów z kolejnością ładowania
    from app.application_logic_handler import ApplicationLogicHandler

    # Tworzymy instancję MockMainWindow
    mock_main_window = MockMainWindow()

    # Mockujemy translation_manager, aby uniknąć problemów z tłumaczeniami w testach
    mocker.patch('app.translation_manager.translation_manager.translate', side_effect=lambda context, text: text)

    # Tworzymy instancję ApplicationLogicHandler
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

def test_show_properties_dialog_with_file(qtbot, app_handler, mocker):
    # 1. Przygotowanie danych testowych
    test_file_path = "/tmp/test_file.txt"
    mock_properties = {'Full path': test_file_path, 'Size': '123 bytes'}

    # 2. Mockujemy zależności tej metody
    # Mockujemy funkcję, która dostarcza dane
    mock_get_properties = mocker.patch('app.application_logic_handler.get_file_properties', return_value=mock_properties)
    # Mockujemy klasę okna dialogowego, aby nie otwierać prawdziwego okna
    MockPropertiesDialog = mocker.patch('app.application_logic_handler.PropertiesDialog')
    
    # Ustawiamy ścieżkę, która ma być "zaznaczona"
    app_handler.main_window.folder_browser.get_current_selected_path.return_value = test_file_path

    # 3. Wywołanie testowanej metody
    app_handler.show_properties_dialog()

    # 4. Asercje
    # Sprawdzamy, czy próbowano pobrać właściwości dla poprawnej ścieżki
    mock_get_properties.assert_called_once_with(test_file_path)
    # Sprawdzamy, czy próbowano utworzyć okno dialogowe z poprawnymi danymi
    MockPropertiesDialog.assert_called_once_with(mock_properties, app_handler.main_window)
    # Sprawdzamy, czy na instancji okna dialogowego wywołano metodę .exec()
    MockPropertiesDialog.return_value.exec.assert_called_once()

def test_show_properties_dialog_no_selection(qtbot, app_handler, mocker):
    # Mockujemy zależności tej metody
    mock_get_properties = mocker.patch('app.application_logic_handler.get_file_properties')
    MockPropertiesDialog = mocker.patch('app.application_logic_handler.PropertiesDialog')
    mock_show_error = mocker.patch('app.application_logic_handler.show_error_message')

    # Ustawiamy, że żaden plik nie jest "zaznaczony"
    app_handler.main_window.folder_browser.get_current_selected_path.return_value = None

    # Wywołanie testowanej metody
    app_handler.show_properties_dialog()

    # Sprawdzamy, czy pokazano błąd
    mock_show_error.assert_called_once_with(
        app_handler.main_window,
        "Properties Error",
        "No file or folder selected."
    )
    # Sprawdzamy, czy NIE próbowano pobrać właściwości
    mock_get_properties.assert_not_called()
    # Sprawdzamy, czy NIE próbowano otworzyć okna dialogowego
    MockPropertiesDialog.assert_not_called()
