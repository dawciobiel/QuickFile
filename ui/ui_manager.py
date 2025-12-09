import os
import subprocess
import logging
from PyQt6.QtCore import Qt, QSettings, QEvent, QObject
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLineEdit, QToolButton, QDialog, QMessageBox
from PyQt6.QtGui import QFileSystemModel
from bookmarks.bookmarks_manager import BookmarksManager
from browser.folder_browser import FolderBrowser
from panels.menu_panel import MenuPanel
from panels.function_key_panel import FunctionKeyPanel
from file_operations.file_manager import FileManager
from file_operations.file_comparator import FileComparator
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from app.shortcuts_manager import ShortcutsManager
from app.settings_manager import SettingsManager
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog
from utils.bookmark_dialog import BookmarkDialog
from utils.compare_dialog import CompareDialog

class UIManager(QObject):
    def __init__(self, main_window, settings_manager):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings_manager = settings_manager
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # Initialize file manager
        self.main_window.file_manager = FileManager(self.main_window)
        self.main_window.file_comparator = FileComparator()
        self.main_window.archive_manager = ArchiveManager(self.main_window)
        self.main_window.directory_synchronizer = DirectorySynchronizer(self.main_window)

        # Inicjalizacja komponentów, które są potrzebne innym
        self.main_window.folder_browser = FolderBrowser(
            view_mode=self.settings_manager.get_setting("view_mode"),
            settings_manager=self.settings_manager,
            parent=self.main_window
        )

        # Inicjalizacja paska narzędzi
        self.main_window.toolbar = self.main_window.addToolBar(self.main_window.tr("Main Tools"))
        self.main_window.toolbar.setObjectName("mainToolbar")
        self.main_window.toolbar.setMovable(False)

        self.main_window.bookmarks_manager = BookmarksManager()

        # Pole wyszukiwania
        self.main_window.search_input = QLineEdit(self.main_window)
        self.main_window.search_input.setPlaceholderText(self.main_window.tr("Search files..."))
        self.main_window.toolbar.addWidget(self.main_window.search_input)

        # Przycisk do zakładek
        self.main_window.add_bookmark_button = QToolButton(self.main_window)
        self.main_window.add_bookmark_button.setText("⭐")
        self.main_window.add_bookmark_button.setToolTip(self.main_window.tr("Add current directory to bookmarks"))
        self.main_window.toolbar.addWidget(self.main_window.add_bookmark_button)

        # Inicjalizacja paska menu i paska stanu
        self.main_window.menu_panel = MenuPanel(self.main_window)

        self.main_window.status_bar = self.main_window.statusBar()
        self.main_window.status_bar.showMessage(self.main_window.tr("Ready"))

        # Panel klawiszy funkcyjnych
        self.main_window.function_key_panel = FunctionKeyPanel(self.main_window)

        # Ustawienie centralnego widżetu
        central_widget = QWidget(self.main_window)
        self.main_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.main_window.folder_browser, 1)
        layout.addWidget(self.main_window.function_key_panel)

    def _connect_signals(self):
        self.main_window.search_input.returnPressed.connect(self.main_window.start_file_search)
        self.main_window.folder_browser.file_selected.connect(self.main_window.open_file_externally)
        self.main_window.folder_browser.current_directory_changed.connect(self.main_window.update_status_bar_path)
        self.main_window.add_bookmark_button.clicked.connect(self.main_window.add_bookmark)
        self.main_window.menu_panel.go_up_requested.connect(self.main_window.folder_browser.go_up_directory)
        self.main_window.menu_panel.refresh_requested.connect(self.main_window.folder_browser.refresh_all_views)
        self.main_window.menu_panel.view_mode_changed.connect(self.main_window.folder_browser.set_view_mode)
