import logging

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QToolButton, QToolBar

from app.application_logic_handler import ApplicationLogicHandler
from app.shortcuts_manager import ShortcutsManager
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager
from browser.folder_browser import FolderBrowser
from panels.function_key_panel import FunctionKeyPanel
from panels.menu_panel import MenuPanel


class UIManager(QObject):
    def __init__(self, main_window, settings_manager, file_manager, file_comparator, archive_manager, directory_synchronizer, bookmarks_manager, theme_manager: ThemeManager):
        super().__init__(main_window)
        self.main_window = main_window
        self.settings_manager = settings_manager
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.bookmarks_manager = bookmarks_manager
        self.theme_manager = theme_manager

        # Attributes to hold the created UI components
        self.folder_browser = None
        self.toolbar = None
        self.add_bookmark_button = None
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

    def _create_add_bookmark_button(self):
        add_bookmark_button = QToolButton(self.main_window)
        add_bookmark_button.setText("⭐")
        add_bookmark_button.setToolTip(translation_manager.translate("UIManager", "Add current directory to bookmarks"))
        return add_bookmark_button

    def _create_menu_panel(self, toolbar: QToolBar, application_logic_handler: ApplicationLogicHandler, shortcuts_manager: ShortcutsManager):
        return MenuPanel(self.main_window, toolbar, application_logic_handler, shortcuts_manager)

    def _create_function_key_panel(self):
        return FunctionKeyPanel(self.main_window)

    def init_ui(self, application_logic_handler: ApplicationLogicHandler, shortcuts_manager: ShortcutsManager):
        # Retrieve widgets from the loaded UI
        self.toolbar = self.main_window.mainToolbar
        self.status_bar = self.main_window.statusbar

        # Create custom widgets
        self.folder_browser = self._create_folder_browser()
        self.function_key_panel = self._create_function_key_panel()
        self.add_bookmark_button = self._create_add_bookmark_button()

        # Replace placeholders with actual widgets
        self._replace_placeholder("folder_browser_placeholder", self.folder_browser)
        self._replace_placeholder("function_key_panel_placeholder", self.function_key_panel)

        # Assign UI components to main_window for external access
        self.main_window.folder_browser = self.folder_browser
        self.main_window.add_bookmark_button = self.add_bookmark_button

        # Create MenuPanel and then initialize its menus
        self.menu_panel = self._create_menu_panel(self.toolbar, application_logic_handler, shortcuts_manager)
        self.menu_panel.initialize_menus()

        # Add bookmark button to toolbar (search input removed as requested)
        self.toolbar.addWidget(self.add_bookmark_button)

        # Initialize status bar message
        self.status_bar.showMessage(translation_manager.translate("UIManager", "Ready"))

    def _replace_placeholder(self, placeholder_name, new_widget):
        """Replaces a placeholder widget in the layout with a new widget."""
        placeholder = getattr(self.main_window, placeholder_name, None)
        if placeholder:
            layout = placeholder.parent().layout()
            if layout:
                layout.replaceWidget(placeholder, new_widget)
                placeholder.deleteLater()
            else:
                logging.error(f"Placeholder {placeholder_name} has no parent layout.")
        else:
            logging.error(f"Placeholder {placeholder_name} not found in MainWindow.")

    def connect_signals(self, application_logic_handler: ApplicationLogicHandler):
        self.folder_browser.file_selected.connect(application_logic_handler.open_file_externally)
        self.folder_browser.current_directory_changed.connect(application_logic_handler.update_status_bar_path)
        self.add_bookmark_button.clicked.connect(application_logic_handler.add_bookmark)
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
