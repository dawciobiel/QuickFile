import logging
import os
import subprocess
import shlex
from functools import wraps

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMessageBox

from app.background_task_manager import BackgroundTaskManager
from app.dialog_handler import DialogHandler
from app.settings_handler import SettingsHandler
from app.task_queue_manager import TaskQueueManager
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from favorites.favorites_manager import FavoritesManager
from file_operations.archive_manager import ArchiveManager, UnrarNotInstalledError
from file_operations.directory_synchronizer import DirectorySynchronizer, DirectorySynchronizerError
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager, FileManagerError
from utils.dialogs import show_error_message


def handle_app_logic_error(title_key):
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
                 favorites_manager: FavoritesManager, archive_manager: ArchiveManager,
                 directory_synchronizer: DirectorySynchronizer, theme_manager,
                 ui_state_provider: UIStateProvider, dialog_handler: DialogHandler,
                 settings_handler: SettingsHandler, background_task_manager: BackgroundTaskManager,
                 task_queue_manager: TaskQueueManager = None):
        super().__init__(main_window)
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.favorites_manager = favorites_manager
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.theme_manager = theme_manager
        self.ui_state_provider = ui_state_provider
        self.dialog_handler = dialog_handler
        self.settings_handler = settings_handler
        self.background_task_manager = background_task_manager
        self.task_queue_manager = task_queue_manager

        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    def _get_active_panel_path(self):
        active_panel = self.ui_state_provider.get_active_panel_widget()
        if active_panel:
            return active_panel.file_view.get_current_path()
        return None

    def on_theme_changed(self, theme_path):
        left_panel = self.ui_state_provider.folder_browser.get_left_panel_widget()
        right_panel = self.ui_state_provider.folder_browser.get_right_panel_widget()
        
        if left_panel:
            left_panel.file_view.update_view_settings()
        if right_panel:
            right_panel.file_view.update_view_settings()

    @handle_app_logic_error("Tab Error")
    def new_tab(self, checked=False):
        self.main_window.ui_manager.folder_browser.add_new_tab()

    @handle_app_logic_error("Tab Error")
    def close_tab(self, checked=False):
        self.main_window.ui_manager.folder_browser.close_current_tab()

    def _run_external_command(self, command_template, file_path):
        if not file_path:
            return
        command = command_template.replace("%f", shlex.quote(file_path))
        try:
            subprocess.Popen(shlex.split(command))
        except Exception as e:
            show_error_message(self.main_window, "Error", f"Failed to run command: {command}\n{e}")

    @handle_app_logic_error("File Opening Error")
    def open_file_externally(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' does not exist.")
        command = self.main_window.settings_manager.get_setting("editor_command")
        self._run_external_command(command, file_path)

    @handle_app_logic_error("Preview Error")
    def _handle_f3_key(self, checked=False):
        selected_path = self.ui_state_provider.get_selected_file_path()
        if selected_path:
            command = self.main_window.settings_manager.get_setting("viewer_command")
            self._run_external_command(command, selected_path)
        else:
            self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", "No file selected for preview."))

    @handle_app_logic_error("Edit Error")
    def _handle_f4_key(self, checked=False):
        selected_path = self.ui_state_provider.get_selected_file_path()
        if selected_path:
            command = self.main_window.settings_manager.get_setting("editor_command")
            self._run_external_command(command, selected_path)
        else:
            self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", "No file selected for editing."))

    @handle_app_logic_error("Favorite Error")
    def add_favorite(self, checked=False):
        current_path = self._get_active_panel_path()
        if current_path:
            self.favorites_manager.add_favorite(current_path)
            message = translation_manager.translate("ApplicationLogicHandler", "Favorite added: {path}").format(path=current_path)
            self.main_window.statusBar().showMessage(message)
        else:
            show_error_message(self.main_window, "Favorite Error", "Could not determine current directory.")

    def update_status_bar_path(self, path):
        self.main_window.statusBar().showMessage(f"Current directory: {path}")

    @handle_app_logic_error("Search Error")
    def start_file_search(self, checked=False):
        search_text = self.main_window.search_input.text()
        if search_text:
            current_path = self._get_active_panel_path()
            if not current_path:
                show_error_message(self.main_window, "Search Error", "Could not determine current directory.")
                return
            results, message = self.file_manager.search_files(current_path, search_text)
            self.dialog_handler.show_search_results(results)
            self.main_window.statusBar().showMessage(message)
        else:
            self.main_window.statusBar().showMessage("Enter text to search.")

    @handle_app_logic_error("Comparison Error")
    def compare_selected_items(self, checked=False):
        self.dialog_handler.compare_selected_items()

    @handle_app_logic_error("Open Favorite Error")
    def open_favorites_dialog(self, checked=False):
        self.dialog_handler.open_favorites_dialog()

    @handle_app_logic_error("Create Archive Error")
    def create_archive(self, checked=False):
        self.dialog_handler.create_archive()

    @handle_app_logic_error("Extract Archive Error")
    def extract_archive(self, checked=False):
        self.dialog_handler.extract_archive()

    @handle_app_logic_error("Properties Error")
    def show_properties_dialog(self, checked=False):
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
    def open_general_settings_dialog(self, checked=False):
        new_settings = self.dialog_handler.open_general_settings_dialog()
        if new_settings:
            self.settings_handler.apply_general_settings(new_settings)

    @handle_app_logic_error("Shortcuts Error")
    def open_shortcuts_dialog(self, checked=False):
        self.dialog_handler.open_shortcuts_dialog()

    def set_focus_on_path_edit(self):
        active_panel_widget = self.ui_state_provider.get_active_panel_widget()
        if active_panel_widget:
            active_panel_widget.path_edit.setFocus()
