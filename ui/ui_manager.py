import os
import subprocess
import logging
from PyQt6.QtCore import Qt, QSettings, QEvent, QObject
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLineEdit, QToolButton, QDialog, QMessageBox, QToolBar, QStatusBar
from PyQt6.QtGui import QFileSystemModel
from favorites.favorites_manager import FavoritesManager
from browser.folder_browser import FolderBrowser
from panels.menu_panel import MenuPanel
from panels.function_key_panel import FunctionKeyPanel
from file_operations.file_manager import FileManager
from file_operations.file_comparator import FileComparator
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from app.shortcuts_manager import ShortcutsManager
from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog
from utils.favorites_dialog import FavoritesDialog
from utils.compare_dialog import CompareDialog
from app.translation_manager import translation_manager
from app.application_logic_handler import ApplicationLogicHandler

class UIManager(QObject):
    def __init__(self, main_window, settings_manager, file_manager, file_comparator, archive_manager, directory_synchronizer, favorites_manager, theme_manager: ThemeManager):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings_manager = settings_manager
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.favorites_manager = favorites_manager
        self.theme_manager = theme_manager

        self.folder_browser = None
        self.toolbar = None
        self.search_input = None
        self.add_favorite_button = None
        self.menu_panel = None
        self.status_bar = None
        self.function_key_panel = None

    def _create_folder_browser(self):
        return FolderBrowser(
            view_mode=self.settings_manager.get_setting("view_mode"),
            settings_manager=self.settings_manager,
            theme_manager=self.theme_manager,
            parent=self.main_window
        )

    def _create_search_input(self):
        search_input = QLineEdit(self.main_window)
        search_input.setPlaceholderText(translation_manager.translate("UIManager", "Search files..."))
        return search_input

    def _create_add_favorite_button(self):
        add_favorite_button = QToolButton(self.main_window)
        add_favorite_button.setText("⭐")
        add_favorite_button.setToolTip(translation_manager.translate("UIManager", "Add current directory to favorites"))
        return add_favorite_button

    def _create_menu_panel(self, toolbar: QToolBar, application_logic_handler: ApplicationLogicHandler, shortcuts_manager: ShortcutsManager):
        return MenuPanel(self.main_window, toolbar, application_logic_handler, shortcuts_manager)

    def _create_function_key_panel(self):
        return FunctionKeyPanel(self.main_window)

    def init_ui(self, application_logic_handler: ApplicationLogicHandler, shortcuts_manager: ShortcutsManager):
        self.toolbar = self.main_window.findChild(QToolBar, "mainToolbar")
        if not self.toolbar:
            self.toolbar = self.main_window.addToolBar(translation_manager.translate("UIManager", "Main Tools"))
            self.toolbar.setObjectName("mainToolbar")
        
        self.main_window.mainToolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.folder_browser = self._create_folder_browser()
        self.function_key_panel = self._create_function_key_panel()
        self.search_input = self._create_search_input()
        self.add_favorite_button = self._create_add_favorite_button()

        self.main_window.folder_browser = self.folder_browser
        self.main_window.search_input = self.search_input
        self.main_window.add_favorite_button = self.add_favorite_button

        central_widget_layout = self.main_window.centralwidget.layout()
        if central_widget_layout:
            folder_browser_placeholder = self.main_window.findChild(QWidget, "folder_browser_placeholder")
            if folder_browser_placeholder:
                central_widget_layout.replaceWidget(folder_browser_placeholder, self.folder_browser)
                folder_browser_placeholder.deleteLater()
            
            function_key_panel_placeholder = self.main_window.findChild(QWidget, "function_key_panel_placeholder")
            if function_key_panel_placeholder:
                central_widget_layout.replaceWidget(function_key_panel_placeholder, self.function_key_panel)
                function_key_panel_placeholder.deleteLater()

        self.menu_panel = self._create_menu_panel(self.toolbar, application_logic_handler, shortcuts_manager)
        self.menu_panel.initialize_menus()

        self.toolbar.addWidget(self.search_input)
        self.toolbar.addWidget(self.add_favorite_button)
        
        self.status_bar = self.main_window.statusBar()
        self.status_bar.showMessage(translation_manager.translate("UIManager", "Ready"))

    def connect_signals(self, application_logic_handler: ApplicationLogicHandler):
        self.search_input.returnPressed.connect(application_logic_handler.start_file_search)
        self.folder_browser.file_selected.connect(application_logic_handler.open_file_externally)
        self.folder_browser.current_directory_changed.connect(application_logic_handler.update_status_bar_path)
        self.add_favorite_button.clicked.connect(application_logic_handler.add_favorite)
        self.menu_panel.go_up_requested.connect(self.folder_browser.go_up_directory)
        self.menu_panel.refresh_requested.connect(self.folder_browser.refresh_all_views)
        self.menu_panel.view_mode_changed.connect(self.folder_browser.set_view_mode)

    def load_panel_settings(self):
        if self.folder_browser:
            self.folder_browser.load_panel_settings()

    def save_panel_settings(self):
        if self.folder_browser:
            self.folder_browser.save_panel_settings()
