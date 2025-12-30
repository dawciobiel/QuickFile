import functools
import logging
import os
import subprocess

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMessageBox

from app.task_queue_manager import Task, TaskType, TaskStatus
from app.translation_manager import translation_manager
from utils.dialogs import show_error_message


def handle_error(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logging.exception(f"An unexpected error occurred in {func.__name__}: {e}")
            show_error_message(self.main_window, translation_manager.translate("Global", "Error"), str(e))
    return wrapper


class ApplicationLogicHandler(QObject):
    def __init__(self, main_window, file_manager, file_comparator, favorites_manager, directory_synchronizer, theme_manager, ui_state_provider, dialog_handler, settings_handler, background_task_manager, task_queue_manager):
        super().__init__()
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.favorites_manager = favorites_manager
        self.directory_synchronizer = directory_synchronizer
        self.theme_manager = theme_manager
        self.ui_state_provider = ui_state_provider
        self.dialog_handler = dialog_handler
        self.settings_handler = settings_handler
        self.background_task_manager = background_task_manager
        self.task_queue_manager = task_queue_manager
        
        self.task_queue_manager.task_completed.connect(self._on_task_completed)

    def _on_task_completed(self, task):
        if task.type == TaskType.CALCULATE_SIZE and task.status == TaskStatus.FINISHED:
            path = task.source_paths[0]
            size = task.result
            self.ui_state_provider.folder_browser.update_directory_size(path, size)

    @handle_error
    def _handle_f3_key(self, checked=False):
        self.dialog_handler.show_file_viewer_dialog()

    @handle_error
    def _handle_f4_key(self):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if selected_path and os.path.isfile(selected_path):
            editor_command = self.settings_handler.settings_manager.get_setting("editor_command", "xdg-open %f")
            try:
                if "%f" in editor_command:
                    command = editor_command.replace("%f", selected_path)
                    subprocess.Popen(command, shell=True)
                else:
                    subprocess.Popen([editor_command, selected_path])
            except Exception as e:
                logging.error(f"Failed to edit file {selected_path}: {e}")
                show_error_message(self.main_window, translation_manager.translate("Global", "Error"), f"Failed to edit file: {e}")

    @handle_error
    def change_owner(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No file or folder selected."))

        plugin = self.task_queue_manager.plugin_manager.get_attribute_editor_plugin()
        if plugin:
            plugin.open_editor(selected_path, self.main_window)
        else:
            QMessageBox.warning(self.main_window, "Not Supported", "Attribute editing is not supported on this system.")

    @handle_error
    def update_status_bar_path(self, path):
        self.main_window.statusBar().showMessage(path)

    @handle_error
    def start_file_search(self, checked=False):
        self.dialog_handler.start_search()

    @handle_error
    def add_favorite(self, checked=False):
        current_path = self.ui_state_provider.get_active_panel_path()
        if current_path:
            self.favorites_manager.add_favorite(current_path)
            self.main_window.statusBar().showMessage(translation_manager.translate("MenuPanel", f"Added to favorites: {current_path}"))

    @handle_error
    def open_favorites_dialog(self, checked=False):
        self.dialog_handler.open_favorites_dialog()

    @handle_error
    def create_new_file(self, current_dir=None, checked=False):
        self.dialog_handler.create_new_file(current_dir)

    @handle_error
    def create_new_directory(self, current_dir=None, checked=False):
        self.dialog_handler.create_new_directory(current_dir)

    @handle_error
    def copy_selected_item(self, checked=False):
        self.dialog_handler.copy_selected_item()

    @handle_error
    def move_selected_item(self, checked=False):
        self.dialog_handler.move_selected_item()

    @handle_error
    def delete_selected_item(self, checked=False):
        self.dialog_handler.delete_selected_item()

    @handle_error
    def rename_selected_item(self, checked=False):
        self.dialog_handler.rename_selected_item()

    @handle_error
    def paste_item_to_current_dir(self, checked=False):
        self.dialog_handler.paste_item_to_current_dir()

    @handle_error
    def open_general_settings_dialog(self, checked=False):
        new_settings = self.dialog_handler.open_general_settings_dialog()
        if new_settings:
            self.settings_handler.apply_general_settings(new_settings)

    @handle_error
    def open_shortcuts_dialog(self, checked=False):
        self.dialog_handler.open_shortcuts_dialog()

    @handle_error
    def show_properties_dialog(self, checked=False):
        self.dialog_handler.show_properties_dialog()

    @handle_error
    def show_about_dialog(self, checked=False):
        self.dialog_handler.show_about_dialog()

    @handle_error
    def compare_selected_items(self, checked=False):
        selected_paths = self.ui_state_provider.get_selected_paths()
        
        if len(selected_paths) == 2:
            path1, path2 = selected_paths
            if os.path.isfile(path1) and os.path.isfile(path2):
                self.dialog_handler._compare_files(path1, path2)
            elif os.path.isdir(path1) and os.path.isdir(path2):
                self.dialog_handler._compare_directories(path1, path2)
            else:
                show_error_message(self.main_window, translation_manager.translate("Global", "Error"), translation_manager.translate("MenuPanel", "Cannot compare a file with a directory."))
        elif len(selected_paths) == 1:
            # Compare with item in other panel
            path1 = selected_paths[0]
            other_panel_path = self.ui_state_provider.get_inactive_panel_path()
            if other_panel_path:
                # Try to find item with same name in other panel
                path2 = os.path.join(other_panel_path, os.path.basename(path1))
                if os.path.exists(path2):
                     if os.path.isfile(path1) and os.path.isfile(path2):
                        self.dialog_handler._compare_files(path1, path2)
                     elif os.path.isdir(path1) and os.path.isdir(path2):
                        self.dialog_handler._compare_directories(path1, path2)
                     else:
                        show_error_message(self.main_window, translation_manager.translate("Global", "Error"), translation_manager.translate("MenuPanel", "Cannot compare a file with a directory."))
                else:
                     show_error_message(self.main_window, translation_manager.translate("Global", "Error"), translation_manager.translate("MenuPanel", "Item not found in the other panel."))
            else:
                 show_error_message(self.main_window, translation_manager.translate("Global", "Error"), translation_manager.translate("MenuPanel", "No other panel active."))
        else:
            show_error_message(self.main_window, translation_manager.translate("Global", "Error"), translation_manager.translate("MenuPanel", "Select exactly two items to compare, or one item to compare with the other panel."))

    @handle_error
    def create_archive(self, checked=False):
        self.dialog_handler.create_archive()

    @handle_error
    def extract_archive(self, checked=False):
        self.dialog_handler.extract_archive()

    @handle_error
    def synchronize_directories(self, checked=False):
        self.dialog_handler.synchronize_directories()

    @handle_error
    def calculate_checksum(self, checked=False):
        self.dialog_handler.calculate_checksum()

    @handle_error
    def calculate_directory_size(self, checked=False):
        path = self.ui_state_provider.get_current_selected_path()
        if path and os.path.isdir(path):
            task = Task(TaskType.CALCULATE_SIZE, [path])
            self.task_queue_manager.add_task(task)

    @handle_error
    def new_tab(self, checked=False):
        self.ui_state_provider.folder_browser.add_new_tab()

    @handle_error
    def close_tab(self, checked=False):
        self.ui_state_provider.folder_browser.close_current_tab()

    @handle_error
    def set_focus_on_path_edit(self):
        if self.ui_state_provider.folder_browser.active_panel_widget:
            self.ui_state_provider.folder_browser.active_panel_widget.path_edit.setFocus()
            self.ui_state_provider.folder_browser.active_panel_widget.path_edit.selectAll()

    @handle_error
    def create_link(self, checked=False):
        self.dialog_handler.create_link()

    @handle_error
    def modify_symbolic_link(self, checked=False):
        self.dialog_handler.modify_symbolic_link()

    @handle_error
    def refresh_all_views(self, checked=False):
        self.ui_state_provider.folder_browser.refresh_all_views()

    @handle_error
    def go_up_directory(self, checked=False):
        self.ui_state_provider.folder_browser.go_up_directory()

    def _get_active_panel_path(self):
        return self.ui_state_provider.get_active_panel_path()
