from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QLineEdit, QMenu

from app.translation_manager import translation_manager
from browser.folder_browser import FolderBrowser
from panels.function_key_panel import FunctionKeyPanel
from panels.menu_panel import MenuPanel


class UIManager:
    def __init__(self, main_window, settings_manager, file_manager, file_comparator,
                 directory_synchronizer, favorites_manager, theme_manager, plugin_manager):
        self.main_window = main_window
        self.settings_manager = settings_manager
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.directory_synchronizer = directory_synchronizer
        self.favorites_manager = favorites_manager
        self.theme_manager = theme_manager
        self.plugin_manager = plugin_manager

    def init_ui(self, app_logic_handler, shortcuts_manager):
        self.main_window.centralWidget().layout().setContentsMargins(5, 5, 5, 5)
        
        self.folder_browser = FolderBrowser(
            settings_manager=self.settings_manager,
            theme_manager=self.theme_manager,
            plugin_manager=self.plugin_manager,
            parent=self.main_window
        )
        self.main_window.browser_tab.layout().addWidget(self.folder_browser)

        self.main_window.mainToolbar.setMovable(False)
        self.main_window.mainToolbar.setObjectName("MainToolBar")
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.mainToolbar)

        self.menu_panel = MenuPanel(
            main_window=self.main_window,
            toolbar=self.main_window.mainToolbar,
            app_logic_handler=app_logic_handler,
            shortcuts_manager=shortcuts_manager,
            theme_manager=self.theme_manager
        )
        self.menu_panel.initialize_ui()

        self.bottom_panel = FunctionKeyPanel(self.main_window)
        self.main_window.centralWidget().layout().addWidget(self.bottom_panel)

        # Connect signals
        self.folder_browser.file_selected.connect(app_logic_handler._handle_f3_key)
        self.folder_browser.current_directory_changed.connect(app_logic_handler.update_status_bar_path)

    def load_panel_settings(self):
        self.folder_browser.load_panel_settings()

    def save_panel_settings(self):
        self.folder_browser.save_panel_settings()
