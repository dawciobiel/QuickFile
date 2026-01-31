# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging

from PyQt6 import uic
from PyQt6.QtCore import Qt, QEvent, QPoint
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMainWindow, QWidget, QMenu, QVBoxLayout

from __version__ import __version__
from app.action_logger import action_logger
from app.application_logic_handler import ApplicationLogicHandler
from app.enums import TaskType, TaskStatus
from app.keyboard_event_handler import KeyboardEventManager
from app.settings_manager import SettingsManager
from app.shortcuts_manager import ShortcutsManager
from app.task_queue_manager import TaskQueueManager
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from browser.folder_browser import FolderBrowser
from favorites.favorites_manager import FavoritesManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager
from panels.function_key_panel import FunctionKeyPanel
from panels.search_results_panel import SearchResultsPanel
from panels.task_queue_panel import TaskQueuePanel
from panels.menu_panel import MenuPanel
from utils.dialogs import show_error_message
from utils.resource_path import get_resource_path


class MainWindow(QMainWindow):
    def __init__(self, background_task_manager, task_queue_manager: TaskQueueManager, file_manager: FileManager, directory_synchronizer: DirectorySynchronizer, notification_manager, file_association_manager):
        super().__init__()
        logging.info("MainWindow initializing...")
        self.background_task_manager = background_task_manager
        self.task_queue_manager = task_queue_manager
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.notification_manager = notification_manager
        self.file_association_manager = file_association_manager
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager(self.settings_manager)
        self.favorites_manager = FavoritesManager()
        self.shortcuts_manager = ShortcutsManager(self)
        self.ui_state_provider = None # Initialized later
        self.dialog_handler = None
        self.app_handler = None
        self.menu_panel = None
        self.search_results_panel = None
        self.keyboard_event_manager = None

        self._init_ui()
        self._post_init_ui()
        self._connect_signals()
        self._apply_initial_settings()
        # Event filters are now installed by FolderBrowser on its sub-widgets
        logging.info("MainWindow initialization complete.")

    def _init_ui(self):
        logging.info("MainWindow _init_ui started.")
        uic.loadUi(get_resource_path("ui/main_window.ui"), self)
        self.setWindowTitle(f"QuickFile v{__version__}")
        self.setWindowIcon(QIcon(get_resource_path("resources/icons/app_icon.png")))

        # Initialize KeyboardEventManager early, as FolderBrowser needs it.
        # The dependent objects (app_handler, folder_browser) will be set later.
        self.keyboard_event_manager = KeyboardEventManager(self, None, None) 
        
        # --- Browser Tab ---
        self.folder_browser = FolderBrowser(self.settings_manager, self.theme_manager, self.task_queue_manager.plugin_manager, self.notification_manager, self.keyboard_event_manager, self)
        self.browser_layout.addWidget(self.folder_browser)
        self.ui_state_provider = UIStateProvider(self.folder_browser)
        
        # Now that folder_browser is created, set it in keyboard_event_manager
        self.keyboard_event_manager.folder_browser = self.folder_browser

        # --- Queue Tab ---
        self.task_queue_panel = TaskQueuePanel(self.task_queue_manager, self.theme_manager, self)
        self.queue_layout.addWidget(self.task_queue_panel)
        
        # --- Search Tab ---
        # self.search_tab and self.search_layout are already loaded from the UI file
        self.search_results_panel = SearchResultsPanel(self)
        self.search_layout.addWidget(self.search_results_panel)
        
        # Hide search tab initially
        self.mainTabWidget.setTabVisible(self.mainTabWidget.indexOf(self.search_tab), False)
        
        logging.info("MainWindow _init_ui finished.")

    def _post_init_ui(self):
        logging.info("MainWindow _post_init_ui started.")
        self.dialog_handler = self.create_dialog_handler()
        self.app_handler = self.create_app_handler()
        self.menu_panel = MenuPanel(self, self.mainToolbar, self.app_handler, self.shortcuts_manager, self.theme_manager)
        self.menu_panel.initialize_ui()
        
        # Replace placeholder with the actual FunctionKeyPanel
        self.function_keys_panel = FunctionKeyPanel(self, self.menu_panel.actions)
        self.verticalLayout.replaceWidget(self.function_key_panel_placeholder, self.function_keys_panel)
        self.function_key_panel_placeholder.deleteLater()

        # Now that app_handler is created, set it in keyboard_event_manager
        self.keyboard_event_manager.application_logic_handler = self.app_handler
        
        logging.info("MainWindow _post_init_ui finished.")

    def create_dialog_handler(self):
        from app.dialog_handler import DialogHandler
        return DialogHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=FileComparator(),
            favorites_manager=self.favorites_manager,
            directory_synchronizer=self.directory_synchronizer,
            ui_state_provider=self.ui_state_provider,
            settings_manager=self.settings_manager,
            background_task_manager=self.background_task_manager,
            task_queue_manager=self.task_queue_manager,
            theme_manager=self.theme_manager
        )

    def create_app_handler(self):
        from app.settings_handler import SettingsHandler
        settings_handler = SettingsHandler(
            main_window=self,
            settings_manager=self.settings_manager,
            shortcuts_manager=self.shortcuts_manager,
            theme_manager=self.theme_manager
        )
        return ApplicationLogicHandler(
            main_window=self,
            file_manager=self.file_manager,
            file_comparator=FileComparator(),
            favorites_manager=self.favorites_manager,
            directory_synchronizer=self.directory_synchronizer,
            theme_manager=self.theme_manager,
            ui_state_provider=self.ui_state_provider,
            dialog_handler=self.dialog_handler,
            settings_handler=settings_handler,
            background_task_manager=self.background_task_manager,
            task_queue_manager=self.task_queue_manager,
            file_association_manager=self.file_association_manager
        )

    def _connect_signals(self):
        self.folder_browser.file_selected.connect(self.app_handler.update_status_bar_path)
        self.folder_browser.status_message_requested.connect(self.statusBar().showMessage)
        self.task_queue_manager.task_completed.connect(self.on_task_completed)
        self.task_queue_manager.task_finished.connect(self.folder_browser.handle_task_completion)

    def _apply_initial_settings(self):
        self.app_handler.settings_handler.apply_all_settings()

    def _install_event_filters(self):
        # KeyboardEventManager is now installed by FolderBrowser on its file views
        # No global event filter on MainWindow needed for keyboard events
        pass

    def on_task_completed(self, task):
        if task.status == TaskStatus.FINISHED:
            if task.type == TaskType.SEARCH:
                self.switchToSearchResultsTab()
            elif task.type == TaskType.CHECKSUM:
                self.dialog_handler.show_checksum_results(task.source_paths, task.result)
        elif task.status == TaskStatus.ERROR:
            show_error_message(self.notification_manager, "Task Error", f"Task '{task.type.name}' failed: {task.details}")

    def switchToSearchResultsTab(self):
        if self.search_tab:
            index = self.mainTabWidget.indexOf(self.search_tab)
            if index != -1:
                self.mainTabWidget.setTabVisible(index, True)
                self.mainTabWidget.setCurrentIndex(index)

    def closeEvent(self, event):
        action_logger.log_action("close_app")
        self.app_handler.settings_handler.save_window_state()
        self.folder_browser.save_panel_settings()
        self.background_task_manager.shutdown()
        self.task_queue_manager.plugin_manager.shutdown()
        super().closeEvent(event)

    def eventFilter(self, source, event):
        # This eventFilter is no longer used for keyboard events,
        # as KeyboardEventManager is installed directly on file views.
        # It can be removed or left to call super() for other event types.
        return super().eventFilter(source, event)

    def contextMenuEvent(self, event: QEvent):
        active_panel = self.ui_state_provider.get_active_panel_view()
        if not active_panel:
            return

        menu = QMenu(self)
        
        # Standard actions
        copy_action = QAction(translation_manager.translate("ContextMenu", "Copy"), self)
        copy_action.triggered.connect(self.app_handler.copy_selected_item)
        menu.addAction(copy_action)

        move_action = QAction(translation_manager.translate("ContextMenu", "Move"), self)
        move_action.triggered.connect(self.app_handler.move_selected_item)
        menu.addAction(move_action)

        delete_action = QAction(translation_manager.translate("ContextMenu", "Delete"), self)
        delete_action.triggered.connect(self.app_handler.delete_selected_item)
        menu.addAction(delete_action)
        
        menu.addSeparator()

        # Plugin actions
        selected_paths = self.ui_state_provider.get_selected_paths()
        if selected_paths:
            context_menu_plugins = self.task_queue_manager.plugin_manager.get_context_menu_plugins_for_paths(selected_paths)
            for plugin, actions in context_menu_plugins.items():
                plugin_menu = menu.addMenu(plugin.name)
                for action_info in actions:
                    action = QAction(action_info['text'], self)
                    action.triggered.connect(lambda checked=False, p=plugin, a=action_info: self.app_handler.execute_plugin_action(p, a))
                    plugin_menu.addAction(action)

        menu.exec(self.mapToGlobal(event.pos()))
