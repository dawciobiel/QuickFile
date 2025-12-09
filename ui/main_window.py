import os
import subprocess
import logging
from __version__ import __version__
from PyQt6.QtCore import Qt, QSettings, QEvent
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
from ui.ui_manager import UIManager
from app.keyboard_event_handler import KeyboardEventHandler
from app.application_logic_handler import ApplicationLogicHandler


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"QuickFile v{__version__}")
        self.resize(1200, 800)

        self.shortcuts_manager = ShortcutsManager(self)
        self.settings_manager = SettingsManager()
        
        # Initialize all managers here without passing 'self' if they don't need it
        self.file_manager = FileManager()
        self.file_comparator = FileComparator()
        self.archive_manager = ArchiveManager()
        self.directory_synchronizer = DirectorySynchronizer()
        self.bookmarks_manager = BookmarksManager()

        # Initialize ApplicationLogicHandler FIRST, as UIManager and MenuPanel depend on it
        self.application_logic_handler = ApplicationLogicHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            bookmarks_manager=self.bookmarks_manager,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer
        )

        # Then initialize UIManager, passing managers as dependencies
        self.ui_manager = UIManager(
            main_window=self,
            settings_manager=self.settings_manager,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            bookmarks_manager=self.bookmarks_manager
        )

        self.shortcuts_manager.apply_shortcuts()
        self.load_settings()
        
        # Initialize KeyboardEventHandler
        self.keyboard_event_handler = KeyboardEventHandler(self)
        # The event filter will be installed in main.py

    def load_settings(self):
        # Restore window geometry and state using SettingsManager
        self.settings_manager.load_window_settings(self)

        # Load panel paths and active panel using FolderBrowser
        self.folder_browser.load_panel_settings()

    def save_settings(self):
        # Save window geometry and state using SettingsManager
        self.settings_manager.save_window_settings(self)

        # Save panel paths and active panel using FolderBrowser
        self.folder_browser.save_panel_settings()

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
