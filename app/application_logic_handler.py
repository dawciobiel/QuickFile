import logging
import os
import subprocess
from functools import wraps

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMessageBox

from app.dialog_handler import DialogHandler
from app.settings_handler import SettingsHandler
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from bookmarks.bookmarks_manager import BookmarksManager
from file_operations.archive_manager import ArchiveManager, UnrarNotInstalledError
from file_operations.directory_synchronizer import DirectorySynchronizer, DirectorySynchronizerError
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager, FileManagerError
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog


def handle_app_logic_error(title_key):
    """
    A decorator to wrap application logic methods, catching common exceptions
    and displaying an error message to the user.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except (FileManagerError, UnrarNotInstalledError, DirectorySynchronizerError,
                    FileNotFoundError, FileExistsError, ValueError, IsADirectoryError, NotADirectoryError) as e:
                show_error_message(self.main_window, translation_manager.translate("ApplicationLogicHandler", title_key), str(e))
                logging.exception(f"Error in {func.__name__}: {e}")
            except Exception as e:
                show_error_message(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Unexpected Error"), str(e))
                logging.exception(f"An unexpected error occurred in {func.__name__}: {e}")
        return wrapper
    return decorator

class ApplicationLogicHandler(QObject):
    def __init__(self, main_window, file_manager: FileManager, file_comparator: FileComparator,
                 bookmarks_manager: BookmarksManager, archive_manager: ArchiveManager,
                 directory_synchronizer: DirectorySynchronizer, theme_manager,
                 ui_state_provider: UIStateProvider, dialog_handler: DialogHandler,
                 settings_handler: SettingsHandler): # Added new dependencies
        super().__init__(main_window)
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.bookmarks_manager = bookmarks_manager
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.theme_manager = theme_manager
        self.ui_state_provider = ui_state_provider # Store new dependency
        self.dialog_handler = dialog_handler       # Store new dependency
        self.settings_handler = settings_handler   # Store new dependency

        self.theme_manager.theme_changed.connect(self.on_theme_changed)

        self.ACTION_COMPARE = translation_manager.translate("MenuPanel", "Compare")
        self.ACTION_PROPERTIES = translation_manager.translate("MenuPanel", "Properties")
        self.ACTION_EXIT = translation_manager.translate("MenuPanel", "Exit")
        self.ACTION_CREATE_ARCHIVE = translation_manager.translate("MenuPanel", "Create Archive")
        self.ACTION_EXTRACT_ARCHIVE = translation_manager.translate("MenuPanel", "Extract Archive")
        self.ACTION_GO_UP = translation_manager.translate("MenuPanel", "Go Up")
        self.ACTION_REFRESH = translation_manager.translate("MenuPanel", "Refresh")
        self.ACTION_NEW_FILE = translation_manager.translate("MenuPanel", "New File")
        self.ACTION_NEW_FOLDER = translation_manager.translate("MenuPanel", "New Folder")
        self.ACTION_SEARCH = translation_manager.translate("MenuPanel", "Search")
        self.ACTION_COPY = translation_manager.translate("MenuPanel", "Copy")
        self.ACTION_PASTE = translation_manager.translate("MenuPanel", "Paste")
        self.ACTION_MOVE = translation_manager.translate("MenuPanel", "Move")
        self.ACTION_RENAME = translation_manager.translate("MenuPanel", "Rename")
        self.ACTION_DELETE = translation_manager.translate("MenuPanel", "Delete")
        self.ACTION_SYNCHRONIZE = translation_manager.translate("MenuPanel", "Synchronize")

        self.ERROR_NO_ACTIVE_PANEL = translation_manager.translate("MenuPanel", "No active panel.")
        self.ERROR_NO_CURRENT_DIR = translation_manager.translate("MenuPanel", "Could not determine current directory for active panel.")
        self.ERROR_FILE_CREATION = translation_manager.translate("MenuPanel", "File Creation Error")
        self.ERROR_FOLDER_CREATION = translation_manager.translate("MenuPanel", "Folder Creation Error")

    def _get_active_panel_widget(self):
        """
        Returns the currently active PanelWidget.
        """
        return self.main_window.ui_manager.folder_browser.active_panel_widget

    def _get_active_panel_path(self):
        """Returns the current path of the active panel, or None if no active panel."""
        active_panel = self._get_active_panel_widget()
        if active_panel:
            return active_panel.file_view.get_current_path()
        return None

    def _get_inactive_panel_path(self):
        """Returns the current path of the inactive panel, or None if no inactive panel."""
        inactive_panel = self.main_window.ui_manager.folder_browser.get_inactive_panel_widget()
        if inactive_panel:
            return inactive_panel.file_view.get_current_path()
        return None

    def _get_selected_file_path(self):
        """Returns the path of the single selected file in the active panel, or None."""
        selected_path = self.main_window.ui_manager.folder_browser.get_current_selected_path()
        if selected_path and os.path.isfile(selected_path):
            return selected_path
        return None

    def on_theme_changed(self, theme_path):
        self.main_window.ui_manager.folder_browser.refresh_all_views()

    @handle_app_logic_error("Preview Error")
    def _handle_f3_key(self, checked=False):
        selected_path = self.ui_state_provider.get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)
        else:
            self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", "No file selected for preview."))

    @handle_app_logic_error("Edit Error")
    def _handle_f4_key(self, checked=False):
        selected_path = self.ui_state_provider.get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)
        else:
            self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", "No file selected for editing."))

    @handle_app_logic_error("Bookmark Error")
    def add_bookmark(self, checked=False):
        current_path = self.ui_state_provider.get_active_panel_path()
        if current_path:
            self.bookmarks_manager.add_bookmark(current_path)
            self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", f"Bookmark added: {current_path}"))
        else:
            show_error_message(self.main_window, self.ACTION_CREATE_ARCHIVE, self.ERROR_NO_CURRENT_DIR)


    def update_status_bar_path(self, path):
        self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", "Current directory:") + f" {path}")

    @handle_app_logic_error("Search Error")
    def start_file_search(self, checked=False):
        current_path = self.ui_state_provider.get_active_panel_path()
        if not current_path:
            show_error_message(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Search Error"),
                               self.ERROR_NO_CURRENT_DIR)
            return

        # Open the search dialog directly
        dialog = SearchDialog(current_path, self.file_manager, self.main_window)
        if dialog.exec():
            # If the user clicked "Go to", navigate to the selected file
            selected_file = dialog.selected_file
            if selected_file:
                self.main_window.ui_manager.folder_browser.navigate_to_path(os.path.dirname(selected_file))

    @handle_app_logic_error("File Opening Error")
    def open_file_externally(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(translation_manager.translate("ApplicationLogicHandler", f"File '{file_path}' does not exist."))

        if os.name == 'nt':
            os.startfile(file_path)
        elif os.uname().sysname == 'Darwin':
            subprocess.call(('open', file_path))
        else:
            subprocess.call(('xdg-open', file_path))
        self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", f"File opened: {file_path}"))

    @handle_app_logic_error("Comparison Error")
    def compare_selected_items(self, checked=False):
        self._compare_selected_items_logic()

    def _compare_selected_items_logic(self):
        left_panel = self.main_window.ui_manager.folder_browser.get_left_panel_widget()
        right_panel = self.main_window.ui_manager.folder_browser.get_right_panel_widget()

        if not left_panel or not right_panel:
            logging.warning("Comparison Error: One or both panels are missing.")
            QMessageBox.warning(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Comparison Error"),
                                translation_manager.translate("ApplicationLogicHandler",
                                                              "Cannot perform comparison, one or both panels are missing."))
            return

        left_selected_path = left_panel.file_view.get_current_path()
        right_selected_path = right_panel.file_view.get_current_path()

        if not left_selected_path or not right_selected_path:
            logging.warning("Comparison Error: User tried to compare without selecting items in both panels.")
            QMessageBox.warning(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Comparison Error"), translation_manager.translate("ApplicationLogicHandler", "Please select items in both panels to compare."))
            return

        is_left_dir = os.path.isdir(left_selected_path)
        is_right_dir = os.path.isdir(right_selected_path)

        if is_left_dir and is_right_dir:
            self.dialog_handler._compare_directories(left_selected_path, right_selected_path)
        elif not is_left_dir and not is_right_dir:
            self.dialog_handler._compare_files(left_selected_path, right_selected_path)
        else:
            logging.warning("Comparison Error: User tried to compare a file with a directory.")
            QMessageBox.warning(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Comparison Error"), translation_manager.translate("ApplicationLogicHandler", "Cannot compare a file with a directory. Please select two files or two directories."))

    @handle_app_logic_error("Open Bookmark Error")
    def open_bookmark_dialog(self, checked=False):
        self.dialog_handler.open_bookmark_dialog()

    @handle_app_logic_error("Create Archive Error")
    def create_archive(self, checked=False):
        self.dialog_handler.create_archive()

    @handle_app_logic_error("Extract Archive Error")
    def extract_archive(self, checked=False):
        self.dialog_handler.extract_archive()

    @handle_app_logic_error("Properties Error")
    def show_properties_dialog(self, checked=False): # Added checked=False
        self.dialog_handler.show_properties_dialog()

    @handle_app_logic_error("Synchronization Error")
    def synchronize_directories(self, checked=False):
        self.dialog_handler.synchronize_directories()

    def create_new_file(self, current_dir=None, checked=False):
        self.dialog_handler.create_new_file(current_dir)

    def create_new_directory(self, current_dir=None, checked=False):
        self.dialog_handler.create_new_directory(current_dir)

    @handle_app_logic_error("Copy Error")
    def copy_selected_item(self, checked=False):
        self.dialog_handler.copy_selected_item()

    @handle_app_logic_error("Move Error")
    def move_selected_item(self, checked=False):
        self.dialog_handler.move_selected_item()

    @handle_app_logic_error("Paste Error")
    def paste_item_to_current_dir(self, checked=False):
        self.dialog_handler.paste_item_to_current_dir()

    @handle_app_logic_error("Delete Error")
    def delete_selected_item(self, checked=False):
        self.dialog_handler.delete_selected_item()

    @handle_app_logic_error("Rename Error")
    def rename_selected_item(self, checked=False):
        self.dialog_handler.rename_selected_item()

    @handle_app_logic_error("Settings Error")
    def open_general_settings_dialog(self, checked=False): # Added checked=False
        new_settings = self.dialog_handler.open_general_settings_dialog()
        if new_settings:
            self.settings_handler.apply_general_settings(new_settings)

    @handle_app_logic_error("Shortcuts Error")
    def open_shortcuts_dialog(self, checked=False): # Added checked=False
        self.dialog_handler.open_shortcuts_dialog()

    def apply_general_settings(self, new_settings: dict):
        self.settings_handler.apply_general_settings(new_settings)

    def apply_shortcuts_settings(self, new_shortcuts):
        self.settings_handler.apply_shortcuts_settings(new_shortcuts)

    def set_focus_on_path_edit(self):
        active_panel_widget = self.ui_state_provider.get_active_panel_widget()
        if active_panel_widget:
            active_panel_widget.path_edit.setFocus()

    @handle_app_logic_error("Tab Error")
    def open_new_tab(self, checked=False):
        """Opens a new tab in the active panel."""
        self.main_window.ui_manager.folder_browser.add_new_tab()

    @handle_app_logic_error("Tab Error")
    def close_current_tab(self, checked=False):
        """Closes the current tab in the active panel."""
        self.main_window.ui_manager.folder_browser.close_current_tab()
