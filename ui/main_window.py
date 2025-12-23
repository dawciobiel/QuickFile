from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow

from __version__ import __version__
from app.application_logic_handler import ApplicationLogicHandler
from app.dialog_handler import DialogHandler
from app.keyboard_event_handler import KeyboardEventManager
from app.settings_handler import SettingsHandler
from app.settings_manager import SettingsManager
from app.shortcuts_manager import ShortcutsManager
from app.theme_manager import ThemeManager
from app.ui_state_provider import UIStateProvider
from bookmarks.bookmarks_manager import BookmarksManager
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager
from ui.ui_manager import UIManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle(f"QuickFile v{__version__}")

        # Initialize managers
        self.shortcuts_manager = ShortcutsManager(self)
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager()
        
        self.file_manager = FileManager()
        self.file_comparator = FileComparator()
        self.archive_manager = ArchiveManager()
        self.directory_synchronizer = DirectorySynchronizer()
        self.bookmarks_manager = BookmarksManager()

        # Initialize SettingsHandler
        self.settings_handler = SettingsHandler(
            main_window=self,
            settings_manager=self.settings_manager,
            shortcuts_manager=self.shortcuts_manager,
            theme_manager=self.theme_manager
        )

        # Then initialize UIManager, passing managers as dependencies
        self.ui_manager = UIManager(
            main_window=self,
            settings_manager=self.settings_manager,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            bookmarks_manager=self.bookmarks_manager,
            theme_manager=self.theme_manager
        )
        
        # Initialize ApplicationLogicHandler
        self.application_logic_handler = ApplicationLogicHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            bookmarks_manager=self.bookmarks_manager,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            theme_manager=self.theme_manager,
            ui_state_provider=None,
            dialog_handler=None,
            settings_handler=self.settings_handler
        )

        # Initialize the UI
        self.ui_manager.init_ui(self.application_logic_handler, self.shortcuts_manager)

        # Initialize UIStateProvider and DialogHandler AFTER UIManager
        self.ui_state_provider = UIStateProvider(self.ui_manager.folder_browser)
        self.dialog_handler = DialogHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            bookmarks_manager=self.bookmarks_manager,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            ui_state_provider=self.ui_state_provider,
            settings_manager=self.settings_manager
        )

        # Now that ui_state_provider and dialog_handler are initialized, update application_logic_handler
        self.application_logic_handler.ui_state_provider = self.ui_state_provider
        self.application_logic_handler.dialog_handler = self.dialog_handler

        self.ui_manager.connect_signals(self.application_logic_handler)

        # Initialize KeyboardEventManager AFTER ui_manager has set up folder_browser
        self.keyboard_event_manager = KeyboardEventManager(
            self,
            self.application_logic_handler,
            self.ui_manager.folder_browser
        )

        self.shortcuts_manager.apply_shortcuts()
        self.load_settings()
        
        # Apply initial theme
        initial_theme = self.settings_manager.get_setting("theme", "dark")
        self.theme_manager.apply_theme(initial_theme)

    def load_settings(self):
        # Restore window geometry and state using SettingsManager
        self.settings_manager.load_window_settings(self)

        # Load panel paths and active panel using UIManager
        self.ui_manager.load_panel_settings()

    def save_settings(self):
        # Save window geometry and state using SettingsManager
        self.settings_manager.save_window_settings(self)

        # Save panel paths and active panel using UIManager
        self.ui_manager.save_panel_settings()

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)
