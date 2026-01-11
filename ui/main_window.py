from PyQt6 import uic, sip
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QTabWidget, QToolBar, QMessageBox

from __version__ import __version__
from app.application_logic_handler import ApplicationLogicHandler
from app.dialog_handler import DialogHandler
from app.keyboard_event_handler import KeyboardEventManager
from app.notification_manager import NotificationManager
from app.settings_handler import SettingsHandler
from app.settings_manager import SettingsManager
from app.shortcuts_manager import ShortcutsManager
from app.task_queue_manager import TaskQueueManager, Task, TaskType, TaskStatus
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from favorites.favorites_manager import FavoritesManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager
from panels.search_results_panel import SearchResultsPanel
from panels.task_queue_panel import TaskQueuePanel
from ui.ui_manager import UIManager
from utils.checksum_result_dialog import ChecksumResultDialog
from utils.resource_path import get_resource_path


class MainWindow(QMainWindow):
    def __init__(self, background_task_manager, task_queue_manager: TaskQueueManager, file_manager: FileManager, directory_synchronizer: DirectorySynchronizer):
        super().__init__()

        # --- Declare UI attributes for linter ---
        self.mainTabWidget: QTabWidget | None = None
        self.browser_tab: QWidget | None = None
        self.queue_tab: QWidget | None = None
        self.search_tab: QWidget | None = None
        self.mainToolbar: QToolBar | None = None
        # -----------------------------------------
        
        uic.loadUi(get_resource_path("ui/main_window.ui"), self)
        self.setWindowTitle(f"QuickFile v{__version__}")
        self.background_task_manager = background_task_manager
        self.task_queue_manager = task_queue_manager
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer

        self.shortcuts_manager = ShortcutsManager(self)
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager(self.settings_manager)
        self.notification_manager = NotificationManager(self, self.settings_manager)
        
        # Apply theme BEFORE initializing UI components that might need theme data
        initial_theme = self.settings_manager.get_setting("theme", "dark")
        self.theme_manager.apply_theme(initial_theme)
        
        self.file_comparator = FileComparator()
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
            directory_synchronizer=self.directory_synchronizer,
            favorites_manager=self.favorites_manager,
            theme_manager=self.theme_manager,
            plugin_manager=self.task_queue_manager.plugin_manager
        )
        
        self.application_logic_handler = ApplicationLogicHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            favorites_manager=self.favorites_manager,
            directory_synchronizer=self.directory_synchronizer,
            theme_manager=self.theme_manager,
            ui_state_provider=None,
            dialog_handler=None,
            settings_handler=self.settings_handler,
            background_task_manager=self.background_task_manager,
            task_queue_manager=self.task_queue_manager
        )

        self.ui_manager.init_ui(self.application_logic_handler, self.shortcuts_manager)
        
        # Initialize UI plugins AFTER the main UI is built
        self.application_logic_handler.initialize_ui_plugins()

        self.ui_state_provider = UIStateProvider(self.ui_manager.folder_browser)
        self.dialog_handler = DialogHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=self.file_comparator,
            favorites_manager=self.favorites_manager,
            directory_synchronizer=self.directory_synchronizer,
            ui_state_provider=self.ui_state_provider,
            settings_manager=self.settings_manager,
            background_task_manager=self.background_task_manager,
            task_queue_manager=self.task_queue_manager,
            theme_manager=self.theme_manager
        )

        self.application_logic_handler.ui_state_provider = self.ui_state_provider
        self.application_logic_handler.dialog_handler = self.dialog_handler

        self.keyboard_event_manager = KeyboardEventManager(
            self,
            self.application_logic_handler,
            self.ui_manager.folder_browser
        )
        QApplication.instance().installEventFilter(self.keyboard_event_manager)

        self.task_queue_panel = TaskQueuePanel(self.task_queue_manager, self.theme_manager)
        self.queue_tab.layout().addWidget(self.task_queue_panel)
        
        self.search_results_panel = SearchResultsPanel()
        self.search_tab.layout().addWidget(self.search_results_panel)
        
        self.mainTabWidget.tabBar().setTabsClosable(False)

        self.active_task_panels = {}  # task.id -> list of panels
        self.panel_busy_counters = {} # panel -> busy count

        self.task_queue_manager.task_added.connect(self.on_task_added)
        self.task_queue_manager.task_completed.connect(self.on_task_completed)
        self.task_queue_manager.task_finished.connect(self.on_task_finished)
        self.ui_manager.folder_browser.status_message_requested.connect(self.show_status_message)

        self.shortcuts_manager.apply_shortcuts()
        self.load_settings()
        
        self.retranslate_ui()

    def retranslate_ui(self):
        self.mainTabWidget.setTabText(self.mainTabWidget.indexOf(self.browser_tab), translation_manager.translate("MainWindow", "Browser"))
        self.mainTabWidget.setTabText(self.mainTabWidget.indexOf(self.queue_tab), translation_manager.translate("MainWindow", "Queue"))
        self.mainTabWidget.setTabText(self.mainTabWidget.indexOf(self.search_tab), translation_manager.translate("MainWindow", "Search Results"))

    def switchToSearchResultsTab(self):
        self.mainTabWidget.setCurrentWidget(self.search_tab)

    def on_task_added(self, task: Task):
        task.directory_changed.connect(self.ui_manager.folder_browser.refresh_path)
        
        affected_paths = set(task.source_paths)
        if task.destination_path:
            affected_paths.add(task.destination_path)
        
        task_panels = []
        for path in affected_paths:
            panels = self.ui_manager.folder_browser.find_panels_by_path(path)
            for panel in panels:
                if panel not in task_panels:
                    task_panels.append(panel)
                    
                    current_count = self.panel_busy_counters.get(panel, 0)
                    if current_count == 0:
                        self.ui_manager.folder_browser.set_tab_busy_indicator(panel, True)
                    self.panel_busy_counters[panel] = current_count + 1
        
        if task_panels:
            self.active_task_panels[task.id] = task_panels

    def on_task_completed(self, task: Task):
        """This slot is called only when a task completes successfully."""
        if task.type == TaskType.CHECKSUM and task.result:
            if task.options.get("show_in_dialog", True):
                dialog = ChecksumResultDialog(self, "Checksum Result", str(task.result))
                dialog.exec()
        elif task.type == TaskType.SEARCH and task.result is not None:
            self.search_results_panel.set_results(task.result)
            self.mainTabWidget.setCurrentWidget(self.search_tab)
        elif task.type == TaskType.SYNC:
            self.ui_manager.folder_browser.refresh_all_views()
        elif task.type == TaskType.SPLIT_FILE:
            if task.destination_path:
                self.ui_manager.folder_browser.refresh_path(task.destination_path)
        elif task.type == TaskType.JOIN_FILES:
            if task.destination_path:
                self.ui_manager.folder_browser.refresh_path(task.destination_path)
        
        self.ui_manager.folder_browser.handle_task_completion(task)

    def on_task_finished(self, task: Task):
        """This slot is called when a task finishes, regardless of status (success, error, cancelled)."""
        if task.status == TaskStatus.FINISHED:
            self.notification_manager.show_success(f"Task '{task.type.name}' completed.")
        elif task.status == TaskStatus.ERROR:
            self.notification_manager.show_error(f"Task '{task.type.name}' failed: {task.details}")
            task_name = task.type.name.replace('_', ' ').capitalize()
            QMessageBox.critical(self, translation_manager.translate("MainWindow", "Task Failed"), 
                                 f"{task_name}: {task.details}")
        elif task.status == TaskStatus.CANCELLED:
            self.notification_manager.show_info(f"Task '{task.type.name}' cancelled.")

        if task.id not in self.active_task_panels:
            return

        panels_for_this_task = self.active_task_panels.pop(task.id)

        for panel in panels_for_this_task:
            if sip.isdeleted(panel):
                self.panel_busy_counters.pop(panel, None)
                continue

            if panel not in self.panel_busy_counters:
                self.ui_manager.folder_browser.set_tab_busy_indicator(panel, False)
                continue

            self.panel_busy_counters[panel] -= 1

            if self.panel_busy_counters[panel] <= 0:
                self.ui_manager.folder_browser.set_tab_busy_indicator(panel, False)
                del self.panel_busy_counters[panel]

    def show_status_message(self, message):
        self.statusBar().showMessage(message, 5000)

    def load_settings(self):
        self.settings_manager.load_window_settings(self)
        self.ui_manager.load_panel_settings()

        toolbar_visible = self.settings_manager.get_setting("toolbar_visible", True)
        self.mainToolbar.setVisible(toolbar_visible)
        show_toolbar_action = self.ui_manager.menu_panel.actions.get("view.show_toolbar")
        if show_toolbar_action:
            show_toolbar_action.setChecked(toolbar_visible)

        last_active_panel = self.settings_manager.get_setting("lastActivePanel", "left")
        if last_active_panel == "right":
            self.ui_manager.folder_browser.set_active_panel(self.ui_manager.folder_browser.get_right_panel_widget())
        else:
            self.ui_manager.folder_browser.set_active_panel(self.ui_manager.folder_browser.get_left_panel_widget())

    def save_settings(self):
        self.settings_manager.save_window_settings(self)
        self.ui_manager.save_panel_settings()

    def closeEvent(self, event):
        if hasattr(self, 'keyboard_event_manager'):
            QApplication.instance().removeEventFilter(self.keyboard_event_manager)
        self.background_task_manager.thread_pool.waitForDone()
        self.save_settings()
        super().closeEvent(event)
