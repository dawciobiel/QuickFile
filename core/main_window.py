import os
import subprocess
import logging # Dodano import logging
from PyQt6.QtCore import Qt, QSettings, QEvent
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QToolBar, QLineEdit, QToolButton, QDialog, QMessageBox
from PyQt6.QtGui import QFileSystemModel
from bookmarks.bookmarks_manager import BookmarksManager
from browser.folder_browser import FolderBrowser
from panels.menu_panel import MenuPanel
from panels.function_key_panel import FunctionKeyPanel
from file_operations.file_manager import FileManager
from file_operations.file_comparator import FileComparator
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from core.shortcuts_manager import ShortcutsManager
from core.settings_manager import SettingsManager
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog
from utils.bookmark_dialog import BookmarkDialog
from utils.compare_dialog import CompareDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick File")
        self.resize(1200, 800)

        self.shortcuts_manager = ShortcutsManager(self)
        self.settings_manager = SettingsManager()
        self._init_ui()
        self.shortcuts_manager.apply_shortcuts()
        self._connect_signals()
        self.load_settings()

        # Usunięto: self.installEventFilter(self) - filtr zdarzeń jest teraz instalowany globalnie w main.py
        # print(f"Qt.Key_F8 value: {Qt.Key_F8}") # Usunięto komunikat debugujący

    def _init_ui(self):
        # Initialize file manager
        self.file_manager = FileManager(self)
        self.file_comparator = FileComparator()
        self.archive_manager = ArchiveManager(self)
        self.directory_synchronizer = DirectorySynchronizer(self)

        # Inicjalizacja komponentów, które są potrzebne innym
        self.folder_browser = FolderBrowser(view_mode=self.settings_manager.get_setting("view_mode"), parent=self)

        # Inicjalizacja paska narzędzi
        self.toolbar = self.addToolBar("Main Tools")
        self.toolbar.setObjectName("mainToolbar") # Ustawienie objectName
        self.toolbar.setMovable(False)

        self.bookmarks_manager = BookmarksManager()

        # Pole wyszukiwania
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search files...")
        self.toolbar.addWidget(self.search_input)

        # Przycisk do zakładek
        self.add_bookmark_button = QToolButton(self)
        self.add_bookmark_button.setText("⭐") # Użyj emoji jako ikony
        self.add_bookmark_button.setToolTip("Add current directory to bookmarks")
        self.toolbar.addWidget(self.add_bookmark_button)

        # Inicjalizacja paska menu i paska stanu
        self.menu_panel = MenuPanel(self)

        # Akcja porównywania jest teraz tworzona w MenuPanel


        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Pasek adresu
        self.address_bar = QLineEdit(self)
        self.address_bar.setReadOnly(True)

        # Panel klawiszy funkcyjnych
        self.function_key_panel = FunctionKeyPanel(self)

        # Ustawienie centralnego widżetu
        central_widget = QWidget(self)
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
        self.add_bookmark_button.clicked.connect(self.add_bookmark)

    def add_bookmark(self):
        """Adds the current directory of the active panel to bookmarks."""
        if self.folder_browser.active_panel:
            current_path = self.folder_browser.active_panel.model().filePath(self.folder_browser.active_panel.model().index(self.folder_browser.active_panel.model().rootPath()))
            self.bookmarks_manager.add_bookmark(current_path)
            self.status_bar.showMessage(f"Bookmark added: {current_path}")

    def update_status_bar_path(self, path):
        self.status_bar.showMessage(f"Current directory: {path}")

    def navigate_from_address_bar(self):
        path = self.address_bar.text()
        self.folder_browser.navigate_to_path(path)

    def start_file_search(self):
        search_text = self.search_input.text()
        if search_text:
            current_path = self.folder_browser.active_panel.model().filePath(self.folder_browser.active_panel.model().index(self.folder_browser.active_panel.model().rootPath()))
            results = self.file_manager.search_files(current_path, search_text)
            self.show_search_results(results)
        else:
            self.status_bar.showMessage("Enter text to search.")

    def show_search_results(self, results):
        """Displays search results in a dialog window."""
        dialog = SearchDialog(self, results)
        dialog.exec()

    def open_file_externally(self, file_path):
        """Opens the file using the system's default application."""
        if not os.path.exists(file_path):
            show_error_message(self, "File Opening Error", f"File '{file_path}' does not exist.")
            return

        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
            self.status_bar.showMessage(f"File opened: {file_path}")
        except Exception as e:
            logging.exception(f"Error opening file externally '{file_path}': {e}")
            show_error_message(self, "File Opening Error", f"Could not open file '{file_path}': {e}")

    def _get_selected_file_path(self):
        """Returns the path to the selected file, if it is a file."""
        selected_path = self.folder_browser.current_selected_path
        if selected_path and os.path.isfile(selected_path):
            return selected_path
        return None

    def _compare_selected_items(self):
        left_selected_path = self.folder_browser.left_panel.get_selected_path()
        right_selected_path = self.folder_browser.right_panel.get_selected_path()

        if not left_selected_path or not right_selected_path:
            logging.warning("Comparison Error: User tried to compare without selecting items in both panels.")
            QMessageBox.warning(self, "Comparison Error", "Please select items in both panels to compare.")
            return

        is_left_dir = os.path.isdir(left_selected_path)
        is_right_dir = os.path.isdir(right_selected_path)

        if is_left_dir and is_right_dir:
            # Compare directories
            self._compare_directories(left_selected_path, right_selected_path)
        elif not is_left_dir and not is_right_dir:
            # Compare files
            self._compare_files(left_selected_path, right_selected_path)
        else:
            logging.warning("Comparison Error: User tried to compare a file with a directory.")
            QMessageBox.warning(self, "Comparison Error", "Cannot compare a file with a directory. Please select two files or two directories.")

    def _compare_files(self, file1_path, file2_path):
        are_identical = self.file_comparator.compare_files(file1_path, file2_path)
        if are_identical:
            QMessageBox.information(self, "File Comparison Result", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are identical.")
        else:
            QMessageBox.information(self, "File Comparison Result", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are different.")

    def _compare_directories(self, dir1_path, dir2_path):
        dircmp_obj = self.file_comparator.compare_directories(dir1_path, dir2_path)
        if dircmp_obj:
            report = self.file_comparator.get_directory_comparison_report(dircmp_obj)
            dialog = CompareDialog(self, report, dir1_path, dir2_path)
            dialog.exec()
        else:
            logging.error("Directory Comparison Error: Could not compare directories. Ensure both paths are valid directories.")
            QMessageBox.critical(self, "Directory Comparison Error", "Could not compare directories. Ensure both paths are valid directories.")

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            # print(f"MainWindow eventFilter: KeyPress event detected. Key: {event.key()}, Source: {source.objectName() if source.objectName() else source.__class__.__name__}")
            key = event.key()
            if key == Qt.Key.Key_F1:
                self.status_bar.showMessage("F1: Help (not implemented)")
                return True
            elif key == Qt.Key.Key_F2:
                self.menu_panel.rename_selected_item()
                return True
            elif key == Qt.Key.Key_F3:
                selected_path = self._get_selected_file_path()
                if selected_path:
                    self.open_file_externally(selected_path)
                else:
                    self.status_bar.showMessage("No file selected for preview.")
                return True
            elif key == Qt.Key.Key_F4:
                selected_path = self._get_selected_file_path()
                if selected_path:
                    self.open_file_externally(selected_path) # Na razie to samo co F3
                else:
                    self.status_bar.showMessage("No file selected for editing.")
                return True
            elif key == Qt.Key.Key_F5:
                # print("MainWindow eventFilter: Calling copy_selected_item for F5") # Usunięto komunikat debugujący
                self.menu_panel.copy_selected_item()
                return True
            elif key == Qt.Key.Key_F6:
                # print("MainWindow eventFilter: Calling move_selected_item for F6") # Usunięto komunikat debugujący
                self.menu_panel.move_selected_item()
                return True
            elif key == Qt.Key.Key_F7:
                self.menu_panel.create_new_directory()
                return True
            elif key == Qt.Key.Key_F8:
                # print(f"MainWindow eventFilter: F8 key ({key}) detected. Calling delete_selected_item.") # Usunięto komunikat debugujący
                self.menu_panel.delete_selected_item()
                return True
            elif key == Qt.Key.Key_F9:
                self._compare_selected_items()
                return True
            elif key == Qt.Key.Key_F10:
                self.close()
                return True
            elif event.key() == Qt.Key.Key_B and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.open_bookmark_dialog()
                return True
        return super().eventFilter(source, event)

    def open_bookmark_dialog(self):
        """Opens the bookmarks dialog."""
        dialog = BookmarkDialog(self.bookmarks_manager.bookmarks, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_bookmark:
            self.folder_browser.navigate_to_path(dialog.selected_bookmark)

    def load_settings(self):
        # Restore window geometry and state (using QSettings as it's built-in for this)
        settings = QSettings("QuickFile", "QuickFile")
        geometry = settings.value("geometry", self.saveGeometry())
        self.restoreGeometry(geometry)
        window_state = settings.value("windowState", self.saveState())
        self.restoreState(window_state)

        # Load panel paths using SettingsManager
        default_path = os.path.expanduser("~")
        
        left_panel_path = self.settings_manager.get_setting("leftPanelPath", default_path)
        right_panel_path = self.settings_manager.get_setting("rightPanelPath", default_path)
            
        self.folder_browser.navigate_to_path(left_panel_path, self.folder_browser.left_panel)
        self.folder_browser.navigate_to_path(right_panel_path, self.folder_browser.right_panel)

        # Load and restore active panel
        active_panel_id = self.settings_manager.get_setting("activePanel", "left") # Default to 'left'
        self.folder_browser.set_active_panel_by_id(active_panel_id)

        # Signal that the initial load is complete
        self.folder_browser.initial_load_done()

    def save_settings(self):
        # Save window geometry and state (using QSettings)
        settings = QSettings("QuickFile", "QuickFile")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

        # Save panel paths and active panel using SettingsManager
        default_path = os.path.expanduser("~")
        
        left_panel_model = self.folder_browser.left_panel.model()
        left_panel_root_index = self.folder_browser.left_panel.rootIndex()
        if isinstance(left_panel_model, QFileSystemModel): # For tree view
            left_panel_path = left_panel_model.filePath(left_panel_root_index) if left_panel_root_index.isValid() else default_path
        else: # For flat view (FlatFileSystemModel)
            left_panel_path = self.folder_browser.current_paths.get(self.folder_browser.left_panel, default_path)
        
        right_panel_model = self.folder_browser.right_panel.model()
        right_panel_root_index = self.folder_browser.right_panel.rootIndex()
        if isinstance(right_panel_model, QFileSystemModel): # For tree view
            right_panel_path = right_panel_model.filePath(right_panel_root_index) if right_panel_root_index.isValid() else default_path
        else: # For flat view (FlatFileSystemModel)
            right_panel_path = self.folder_browser.current_paths.get(self.folder_browser.right_panel, default_path)

        # Use SettingsManager to save
        self.settings_manager.set_setting("leftPanelPath", left_panel_path)
        self.settings_manager.set_setting("rightPanelPath", right_panel_path)
        self.settings_manager.set_setting("activePanel", self.folder_browser.get_active_panel_id())

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
