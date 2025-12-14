import os
import subprocess
import logging
from PyQt6.QtCore import Qt, QSettings, QEvent, QObject
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLineEdit, QToolButton, QDialog, QMessageBox, QToolBar, QStatusBar
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
from app.translation_manager import translation_manager # Import our new manager

class UIManager(QObject):
    def __init__(self, main_window, settings_manager, file_manager, file_comparator, archive_manager, directory_synchronizer, bookmarks_manager):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings_manager = settings_manager
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.bookmarks_manager = bookmarks_manager

        # Attributes to hold the created UI components
        self.folder_browser = None
        self.toolbar = None
        self.search_input = None
        self.add_bookmark_button = None
        self.menu_panel = None
        self.status_bar = None
        self.function_key_panel = None

        self._init_ui()
        self._connect_signals()

    def _create_folder_browser(self):
        return FolderBrowser(
            view_mode=self.settings_manager.get_setting("view_mode"),
            settings_manager=self.settings_manager,
            parent=self.main_window
        )

    def _create_toolbar(self):
        toolbar = self.main_window.addToolBar(translation_manager.translate("UIManager", "Main Tools"))
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        return toolbar

    def _create_search_input(self):
        search_input = QLineEdit(self.main_window)
        search_input.setPlaceholderText(translation_manager.translate("UIManager", "Search files..."))
        return search_input

    def _create_add_bookmark_button(self):
        add_bookmark_button = QToolButton(self.main_window)
        add_bookmark_button.setText("⭐")
        add_bookmark_button.setToolTip(translation_manager.translate("UIManager", "Add current directory to bookmarks"))
        return add_bookmark_button

    def _create_menu_panel(self, toolbar: QToolBar):
        return MenuPanel(self.main_window, toolbar)

    def _create_status_bar(self):
        status_bar = self.main_window.statusBar()
        status_bar.showMessage(translation_manager.translate("UIManager", "Ready"))
        return status_bar

    def _create_function_key_panel(self):
        return FunctionKeyPanel(self.main_window)

    def _init_ui(self):
        self.folder_browser = self._create_folder_browser()
        self.toolbar = self._create_toolbar()
        self.search_input = self._create_search_input()
        self.add_bookmark_button = self._create_add_bookmark_button()
        
        # Assign UI components to main_window for external access
        self.main_window.folder_browser = self.folder_browser
        self.main_window.search_input = self.search_input
        self.main_window.add_bookmark_button = self.add_bookmark_button

        # Create MenuPanel and then initialize its menus
        self.menu_panel = self._create_menu_panel(self.toolbar)
        self.menu_panel.initialize_menus() # Call the new initialization method

        self.status_bar = self._create_status_bar()
        self.function_key_panel = self._create_function_key_panel()

        self.toolbar.addWidget(self.search_input)
        self.toolbar.addWidget(self.add_bookmark_button)

        central_widget = QWidget(self.main_window)
        self.main_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.folder_browser, 1)
        layout.addWidget(self.function_key_panel)

    def _connect_signals(self):
        self.search_input.returnPressed.connect(self.main_window.application_logic_handler.start_file_search)
        self.folder_browser.file_selected.connect(self.main_window.application_logic_handler.open_file_externally)
        self.folder_browser.current_directory_changed.connect(self.main_window.application_logic_handler.update_status_bar_path)
        self.add_bookmark_button.clicked.connect(self.main_window.application_logic_handler.add_bookmark)
        self.menu_panel.go_up_requested.connect(self.folder_browser.go_up_directory)
        self.menu_panel.refresh_requested.connect(self.folder_browser.refresh_all_views)
        self.menu_panel.view_mode_changed.connect(self.folder_browser.set_view_mode)

    def load_panel_settings(self):
        """Loads panel paths and active panel using FolderBrowser."""
        if self.folder_browser:
            self.folder_browser.load_panel_settings()

    def save_panel_settings(self):
        """Saves panel paths and active panel using FolderBrowser."""
        if self.folder_browser:
            self.folder_browser.save_panel_settings()
