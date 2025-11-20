import os
import subprocess
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QToolBar, QLineEdit
from browser.folder_browser import FolderBrowser
from panels.menu_panel import MenuPanel
from panels.function_key_panel import FunctionKeyPanel
from file_operations.file_manager import FileManager
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick File")
        self.resize(1200, 800)

        self._init_ui()
        self._connect_signals()
        self.load_settings()

    def _init_ui(self):
        # Inicjalizacja menedżera plików
        self.file_manager = FileManager(self)

        # Inicjalizacja komponentów, które są potrzebne innym
        self.folder_browser = FolderBrowser()

        # Inicjalizacja paska narzędzi
        self.toolbar = self.addToolBar("Główne narzędzia")
        self.toolbar.setObjectName("mainToolbar") # Ustawienie objectName
        self.toolbar.setMovable(False)

        # Pole wyszukiwania
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Szukaj plików...")
        self.toolbar.addWidget(self.search_input)

        # Inicjalizacja paska menu i paska stanu
        self.menu_panel = MenuPanel(self)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Gotowy")

        # Pasek adresu
        self.address_bar = QLineEdit()
        self.address_bar.setReadOnly(True)

        # Panel klawiszy funkcyjnych
        self.function_key_panel = FunctionKeyPanel(self)

        # Ustawienie centralnego widżetu
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0) # Usunięcie marginesów
        layout.setSpacing(0) # Usunięcie odstępów między widżetami

        layout.addWidget(self.address_bar)
        layout.addWidget(self.folder_browser, 1) # Rozciągnij folder_browser
        layout.addWidget(self.function_key_panel) # function_key_panel zachowa swoją naturalną wysokość

    def _connect_signals(self):
        self.search_input.returnPressed.connect(self.start_file_search)
        self.address_bar.returnPressed.connect(self.navigate_from_address_bar)
        self.folder_browser.file_selected.connect(self.open_file_externally)
        self.folder_browser.current_directory_changed.connect(self.update_status_bar_path)
        self.folder_browser.current_directory_changed.connect(self.address_bar.setText)

    def update_status_bar_path(self, path):
        self.status_bar.showMessage(f"Aktualny katalog: {path}")

    def navigate_from_address_bar(self):
        path = self.address_bar.text()
        self.folder_browser.navigate_to_path(path)

    def start_file_search(self):
        search_text = self.search_input.text()
        if search_text:
            current_path = self.folder_browser.active_panel.model().filePath(self.folder_browser.current_paths[self.folder_browser.active_panel])
            results = self.file_manager.search_files(current_path, search_text)
            self.show_search_results(results)
        else:
            self.status_bar.showMessage("Wprowadź tekst do wyszukania.")

    def show_search_results(self, results):
        """Wyświetla wyniki wyszukiwania w oknie dialogowym."""
        dialog = SearchDialog(self, results)
        dialog.exec_()

    def open_file_externally(self, file_path):
        """Otwiera plik za pomocą domyślnego programu systemowego."""
        if not os.path.exists(file_path):
            show_error_message(self, "Błąd otwierania pliku", f"Plik '{file_path}' nie istnieje.")
            return

        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
            self.status_bar.showMessage(f"Otwarto plik: {file_path}")
        except Exception as e:
            show_error_message(self, "Błąd otwierania pliku", f"Nie można otworzyć pliku '{file_path}': {e}")

    def _get_selected_file_path(self):
        """Zwraca ścieżkę do zaznaczonego pliku, jeśli jest to plik."""
        selected_path = self.folder_browser.current_selected_path
        if selected_path and os.path.isfile(selected_path):
            return selected_path
        return None

    def keyPressEvent(self, event):
        key_actions = {
            Qt.Key_F1: lambda: self.status_bar.showMessage("F1: Pomoc (niezaimplementowana)"),
            Qt.Key_F2: self.menu_panel.rename_selected_item,
            Qt.Key_F3: lambda: self.open_file_externally(self._get_selected_file_path()) if self._get_selected_file_path() else self.status_bar.showMessage("Nie wybrano pliku do podglądu."),
            Qt.Key_F4: lambda: self.open_file_externally(self._get_selected_file_path()) if self._get_selected_file_path() else self.status_bar.showMessage("Nie wybrano pliku do edycji."),
            Qt.Key_F5: self.menu_panel.copy_selected_item,
            Qt.Key_F6: self.menu_panel.cut_selected_item,
            Qt.Key_F7: self.menu_panel.create_new_directory,
            Qt.Key_F8: self.menu_panel.delete_selected_item,
            Qt.Key_F9: lambda: self.status_bar.showMessage("F9: (niezaimplementowana)"),
            Qt.Key_F10: self.close,
        }

        action = key_actions.get(event.key())
        if action:
            action()
        else:
            super().keyPressEvent(event)

    def load_settings(self):
        settings = QSettings("QuickFile", "QuickFile")
        geometry = settings.value("geometry", self.saveGeometry())
        self.restoreGeometry(geometry)
        window_state = settings.value("windowState", self.saveState())
        self.restoreState(window_state)

        # Wczytanie ścieżek dla paneli
        left_panel_path = settings.value("leftPanelPath", os.path.expanduser("~"))
        right_panel_path = settings.value("rightPanelPath", os.path.expanduser("~"))
        self.folder_browser.set_panel_path(self.folder_browser.left_panel, left_panel_path)
        self.folder_browser.set_panel_path(self.folder_browser.right_panel, right_panel_path)

    def save_settings(self):
        settings = QSettings("QuickFile", "QuickFile")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

        # Zapisanie ścieżek dla paneli
        left_panel_path = self.folder_browser.active_panel.model().filePath(self.folder_browser.current_paths[self.folder_browser.left_panel])
        right_panel_path = self.folder_browser.active_panel.model().filePath(self.folder_browser.current_paths[self.folder_browser.right_panel])
        settings.setValue("leftPanelPath", left_panel_path)
        settings.setValue("rightPanelPath", right_panel_path)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
