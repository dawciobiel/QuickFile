from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication, QProgressBar, QLabel, QPushButton

from __version__ import __version__
from app.application_logic_handler import ApplicationLogicHandler
from app.dialog_handler import DialogHandler
from app.keyboard_event_handler import KeyboardEventManager
from app.settings_handler import SettingsHandler
from app.settings_manager import SettingsManager
from app.shortcuts_manager import ShortcutsManager
from app.task_queue_manager import TaskQueueManager
from app.theme_manager import ThemeManager
from app.ui_state_provider import UIStateProvider
from favorites.favorites_manager import FavoritesManager
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager
from panels.task_queue_panel import TaskQueuePanel
from ui.progress_bar_manager import ProgressBarManager
from ui.ui_manager import UIManager


class MainWindow(QMainWindow):
    def __init__(self, background_task_manager, task_queue_manager: TaskQueueManager, file_manager: FileManager, directory_synchronizer: DirectorySynchronizer):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle(f"QuickFile v{__version__}")
        self.background_task_manager = background_task_manager
        self.task_queue_manager = task_queue_manager
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer

        self.shortcuts_manager = ShortcutsManager(self)
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager(self.settings_manager)
        
        self.file_comparator = FileComparator()
        self.archive_manager = ArchiveManager()
        self.favorites_manager = FavoritesManager()

        self.settings_handler = SettingsHandler(
            main_window=self,
            settings_manager=self.settings_manager,
            shortcuts_manager=self.shortcuts_manager,
            theme_manager=self.theme_manager
        )

        self.ui_manager = UIManager(
            main_window=self,
            settings_manager=self.settings_manager,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            favorites_manager=self.favorites_manager,
            theme_manager=self.theme_manager
        )
        
        self.application_logic_handler = ApplicationLogicHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            favorites_manager=self.favorites_manager,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            theme_manager=self.theme_manager,
            ui_state_provider=None,
            dialog_handler=None,
            settings_handler=self.settings_handler,
            background_task_manager=self.background_task_manager,
            task_queue_manager=self.task_queue_manager
        )

        self.ui_manager.init_ui(self.application_logic_handler, self.shortcuts_manager)

        self.ui_state_provider = UIStateProvider(self.ui_manager.folder_browser)
        self.dialog_handler = DialogHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            favorites_manager=self.favorites_manager,
            archive_manager=self.archive_manager,
            directory_synchronizer=self.directory_synchronizer,
            ui_state_provider=self.ui_state_provider,
            settings_manager=self.settings_manager,
            background_task_manager=self.background_task_manager,
            task_queue_manager=self.task_queue_manager
        )

        self.application_logic_handler.ui_state_provider = self.ui_state_provider
        self.application_logic_handler.dialog_handler = self.dialog_handler

        self.ui_manager.connect_signals(self.application_logic_handler)

        self.keyboard_event_manager = KeyboardEventManager(
            self,
            self.application_logic_handler,
            self.ui_manager.folder_browser
        )

        self.progress_label = QLabel("Operation in progress...")
        self.progressBar = QProgressBar()
        self.cancel_button = QPushButton("Cancel")
        self.statusBar().addPermanentWidget(self.progress_label)
        self.statusBar().addPermanentWidget(self.progressBar, 1)
        self.statusBar().addPermanentWidget(self.cancel_button)

        self.progress_bar_manager = ProgressBarManager(self)
        self.cancel_button.clicked.connect(self.background_task_manager.cancel_current_task)

        self.shortcuts_manager.apply_shortcuts()
        self.load_settings()
        
        initial_theme = self.settings_manager.get_setting("theme", "dark")
        self.theme_manager.apply_theme(initial_theme)
        
        self.task_queue_panel = TaskQueuePanel(self.task_queue_manager)
        self.ui_manager.folder_browser.add_custom_tab(self.task_queue_panel, "Queue", "right")

    def load_settings(self):
        self.settings_manager.load_window_settings(self)
        self.ui_manager.load_panel_settings()

    def save_settings(self):
        self.settings_manager.save_window_settings(self)
        self.ui_manager.save_panel_settings()

    def closeEvent(self, event):
        if hasattr(self, 'keyboard_event_manager'):
            QApplication.instance().removeEventFilter(self.keyboard_event_manager)
        self.background_task_manager.thread_pool.waitForDone()
        self.save_settings()
        super().closeEvent(event)
