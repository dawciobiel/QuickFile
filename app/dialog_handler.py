import logging
import os
import subprocess
import sys

from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog

from app.action_logger import action_logger
from app.background_task_manager import BackgroundTaskManager
from app.settings_manager import SettingsManager
from app.task_queue_manager import TaskQueueManager, Task, TaskType
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from favorites.favorites_manager import FavoritesManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager
from file_operations.properties_manager import get_file_properties
from utils.about_dialog import AboutDialog
from utils.checksum_dialog import ChecksumDialog
from utils.compare_dialog import CompareDialog
from utils.copy_dialog import CopyDialog
from utils.create_archive_dialog import CreateArchiveDialog
from utils.delete_dialog import DeleteDialog
from utils.favorites_dialog import FavoritesDialog
from utils.move_dialog import MoveDialog
from utils.properties_dialog import PropertiesDialog
from utils.search_dialog import SearchDialog
from utils.settings_dialog import SettingsDialog
from utils.shortcuts_dialog import ShortcutsDialog
from utils.sync_dialog import SyncDialog


class DialogHandler:
    def __init__(self, main_window, file_manager: FileManager, file_comparator: FileComparator,
                 favorites_manager: FavoritesManager, directory_synchronizer: DirectorySynchronizer, 
                 ui_state_provider: UIStateProvider, settings_manager: SettingsManager, 
                 background_task_manager: BackgroundTaskManager, task_queue_manager: TaskQueueManager = None, theme_manager=None):
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.favorites_manager = favorites_manager
        self.directory_synchronizer = directory_synchronizer
        self.ui_state_provider = ui_state_provider
        self.settings_manager = settings_manager
        self.background_task_manager = background_task_manager
        self.task_queue_manager = task_queue_manager
        self.theme_manager = theme_manager

    def show_about_dialog(self, checked=False):
        action_logger.log_action("show_about")
        dialog = AboutDialog(self.main_window)
        dialog.exec()

    def show_file_viewer_dialog(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path or not os.path.isfile(selected_path):
            raise ValueError(translation_manager.translate("MenuPanel", "No file selected or selected item is a directory."))

        action_logger.log_action("view_file", path=selected_path)

        use_internal = self.settings_manager.get_setting("use_internal_viewer", True)

        if use_internal:
            viewer_plugin = self.task_queue_manager.plugin_manager.get_viewer_for_file(selected_path)
            if viewer_plugin:
                viewer_plugin.view_file(selected_path, self.theme_manager, self.main_window)
            else:
                QMessageBox.warning(self.main_window, "Viewer Not Found", "No suitable built-in viewer plugin found for this file type.")
        else:
            command = self.settings_manager.get_setting("viewer_command")
            if not command:
                QMessageBox.warning(self.main_window, "Command Not Set", "External viewer command is not configured in settings.")
                return

            try:
                full_command = command.replace("%f", f'"{selected_path}"')
                subprocess.Popen(full_command, shell=True)
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to launch external viewer:\n{e}")

    def show_file_editor_dialog(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path or not os.path.isfile(selected_path):
            raise ValueError(translation_manager.translate("MenuPanel", "No file selected or selected item is a directory."))

        action_logger.log_action("edit_file", path=selected_path)

        editor_plugin = self.task_queue_manager.plugin_manager.get_editor_for_file(selected_path)
        
        if editor_plugin:
            editor_plugin.open_editor(selected_path, self.theme_manager, self.main_window)
        else:
             QMessageBox.warning(self.main_window, "Editor Not Found", "No suitable built-in editor plugin found for this file type.")

    def show_properties_dialog(self, checked=False, parent=None):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No file or folder selected."))
        action_logger.log_action("show_properties", path=selected_path)
        properties = get_file_properties(selected_path)

        dialog_parent = parent if parent else self.main_window
        
        if properties:
            PropertiesDialog(properties, dialog_parent).exec()
        else:
            raise ValueError(f"Could not retrieve properties for: {selected_path}")

    def open_general_settings_dialog(self, checked=False):
        action_logger.log_action("open_settings")
        dialog = SettingsDialog(self.main_window, self.settings_manager, self.main_window.theme_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            action_logger.log_action("save_settings", settings=new_settings)
            return new_settings
        return None

    def open_shortcuts_dialog(self, checked=False):
        action_logger.log_action("open_shortcuts")
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            action_logger.log_action("save_shortcuts", shortcuts=new_shortcuts)
            self.main_window.shortcuts_manager.apply_shortcuts_settings(new_shortcuts)

    def _compare_files(self, file1_path, file2_path):
        action_logger.log_action("compare_files", file1=file1_path, file2=file2_path)
        are_identical = self.file_comparator.compare_files(file1_path, file2_path)
        title = translation_manager.translate("DialogHandler", "File Comparison Result")
        if are_identical:
            message = translation_manager.translate("DialogHandler", "Files '{file1}' and '{file2}' are identical.").format(file1=os.path.basename(file1_path), file2=os.path.basename(file2_path))
            QMessageBox.information(self.main_window, title, message)
        else:
            message = translation_manager.translate("DialogHandler", "Files '{file1}' and '{file2}' are different.").format(file1=os.path.basename(file1_path), file2=os.path.basename(file2_path))
            QMessageBox.information(self.main_window, title, message)

    def _compare_directories(self, dir1_path, dir2_path):
        action_logger.log_action("compare_dirs", dir1=dir1_path, dir2=dir2_path)
        dircmp_obj = self.file_comparator.compare_directories(dir1_path, dir2_path)
        if dircmp_obj:
            report = self.file_comparator.get_directory_comparison_report(dircmp_obj)
            dialog = CompareDialog(self.main_window, report, dir1_path, dir2_path)
            dialog.exec()
        else:
            logging.error("Directory Comparison Error: Could not compare directories.")
            QMessageBox.critical(self.main_window, "Directory Comparison Error", "Could not compare directories. Ensure both paths are valid directories.")

    def open_favorites_dialog(self, checked=False):
        action_logger.log_action("open_favorites")
        favorites = self.favorites_manager.get_favorites()
        dialog = FavoritesDialog(favorites, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_favorite:
            action_logger.log_action("navigate_favorite", path=dialog.selected_favorite)
            self.ui_state_provider.folder_browser.navigate_to_path(dialog.selected_favorite)

    def create_archive(self, checked=False):
        paths_to_archive = self.ui_state_provider.get_selected_paths()
        if not paths_to_archive:
            raise ValueError("No file/folder selected for archiving.")

        if len(paths_to_archive) > 1:
            base_dir = self.ui_state_provider.get_active_panel_path()
        else:
            base_dir = os.path.dirname(paths_to_archive[0])

        dialog = CreateArchiveDialog(self.main_window, self.task_queue_manager.plugin_manager, base_dir)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                archive_path = data["destination_path"]
                options = data["options"]

                action_logger.log_action("create_archive", sources=paths_to_archive, destination=archive_path, options=options)

                task = Task(TaskType.CREATE_ARCHIVE, source_paths=paths_to_archive, destination_path=archive_path, options=options)
                self.task_queue_manager.add_task(task)
                self.main_window.statusBar().showMessage("Added archive task to queue.")
                self.ui_state_provider.folder_browser.refresh_all_views()
                self.ui_state_provider.folder_browser.clear_selection()

    def extract_archive(self, checked=False):
        selected_archive_path = self.ui_state_provider.get_current_selected_path()
        if not selected_archive_path:
            raise ValueError("No archive file selected.")
        
        # Find appropriate plugin for extraction based on file extension
        extract_plugin = self.task_queue_manager.plugin_manager.get_archiver_for_file(selected_archive_path)
        if not extract_plugin:
            QMessageBox.warning(self.main_window, "Extraction Error", "No suitable plugin found to extract this archive type.")
            return

        extract_path, ok = QInputDialog.getText(self.main_window, translation_manager.translate("DialogHandler", "Extract Archive"), translation_manager.translate("DialogHandler", "Destination path:"), text=os.path.dirname(selected_archive_path))
        if ok and extract_path:
            action_logger.log_action("extract_archive", source=selected_archive_path, destination=extract_path)

            options = {'plugin_id': extract_plugin.metadata['id']} # Ustawiamy plugin_id
            task = Task(TaskType.EXTRACT_ARCHIVE, source_paths=[selected_archive_path], destination_path=extract_path, options=options)
            self.task_queue_manager.add_task(task)
            self.main_window.statusBar().showMessage("Added extract task to queue.")
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()

    def calculate_checksum(self, checked=False):
        selected_paths = self.ui_state_provider.get_selected_paths()
        if not selected_paths:
            raise ValueError("No file selected for checksum calculation.")
        
        files_only = [p for p in selected_paths if os.path.isfile(p)]
        if not files_only:
            raise ValueError("Checksum can only be calculated for files.")

        algorithms = set()
        for plugin in self.task_queue_manager.plugin_manager.get_checksum_plugins():
            algorithms.update(plugin.get_supported_algorithms())
        
        if not algorithms:
            raise ValueError("No checksum plugins available.")

        dialog = ChecksumDialog(self.main_window, files_only, sorted(list(algorithms)))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            options['plugin_id'] = 'org.quickfile.checksum_standard' # Używamy nowego pluginu
            action_logger.log_action("calculate_checksum", paths=files_only, options=options)
            
            task = Task(TaskType.CHECKSUM, source_paths=files_only, options=options)
            self.task_queue_manager.add_task(task)
            self.main_window.statusBar().showMessage("Added checksum task to queue.")
            self.ui_state_provider.folder_browser.clear_selection()

    def start_search(self, checked=False):
        current_path = self.ui_state_provider.get_active_panel_path()
        if not current_path:
            raise ValueError("Cannot determine search path.")

        dialog = SearchDialog(self.main_window, current_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            options['plugin_id'] = 'org.quickfile.search_standard' # Używamy nowego pluginu
            logging.debug(f"DialogHandler: Options from SearchDialog: {options}")
            query = options.get("file_name")
            start_path = options.get("start_path", current_path)

            if query:
                action_logger.log_action("search", path=start_path, query=query, options=options)
                
                # Clear previous results and switch to search tab
                self.main_window.search_results_panel.clear_results()
                self.main_window.switchToSearchResultsTab()

                # Connect to the plugin's data event signal
                search_plugin = self.task_queue_manager.plugin_manager.get_plugin_by_id("org.quickfile.search_standard")
                if search_plugin:
                    # Disconnect previous handlers to avoid duplicates
                    try:
                        search_plugin.data_event_received.disconnect()
                    except TypeError: # Signal has no slots to disconnect
                        pass
                    
                    search_plugin.data_event_received.connect(self._on_search_item_found)

                task = Task(TaskType.SEARCH, source_paths=[start_path], options=options)
                self.task_queue_manager.add_task(task)
                self.main_window.statusBar().showMessage("Added search task to queue.")

    def _on_search_item_found(self, task_id, event_name, payload):
        if event_name == "item_found":
            self.main_window.search_results_panel.add_search_result(payload['path'])

    def synchronize_directories(self, checked=False):
        left_path = self.ui_state_provider.folder_browser.get_left_panel_widget().file_view.get_current_path()
        right_path = self.ui_state_provider.folder_browser.get_right_panel_widget().file_view.get_current_path()
        if not (left_path and right_path):
            raise ValueError("Both panels must have valid paths for synchronization.")
            
        dialog = SyncDialog(self.main_window, left_path, right_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            options['plugin_id'] = 'org.quickfile.standard_operations'
            action_logger.log_action("sync_dirs", source=left_path, destination=right_path, options=options)
            task = Task(TaskType.SYNC, source_paths=[left_path], destination_path=right_path, options=options)
            self.task_queue_manager.add_task(task)
            self.main_window.statusBar().showMessage("Added sync task to queue.")

    def create_new_file(self, current_dir=None, checked=False):
        if not current_dir:
            current_dir = self.ui_state_provider.get_active_panel_path()
        name, ok = QInputDialog.getText(self.main_window, translation_manager.translate("DialogHandler", "New File"), translation_manager.translate("DialogHandler", "File name:"))
        if ok and name:
            action_logger.log_action("create_file", path=os.path.join(current_dir, name))
            message = self.file_manager.create_file(current_dir, name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def create_new_directory(self, current_dir=None, checked=False):
        if not current_dir:
            current_dir = self.ui_state_provider.get_active_panel_path()
        name, ok = QInputDialog.getText(self.main_window, translation_manager.translate("DialogHandler", "New Folder"), translation_manager.translate("DialogHandler", "Folder name:"))
        if ok and name:
            action_logger.log_action("create_directory", path=os.path.join(current_dir, name))
            message = self.file_manager.create_directory(current_dir, name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def copy_selected_item(self, checked=False):
        source_paths = self.ui_state_provider.get_selected_paths()
        if not source_paths:
            raise ValueError("No file/folder selected for copying.")
        destination_path = self.ui_state_provider.get_inactive_panel_path()
        if not destination_path:
            raise ValueError("No inactive panel path to copy to.")

        dialog = CopyDialog(self.main_window, source_paths, destination_path, self.task_queue_manager, self.background_task_manager, self.theme_manager)
        dialog.exec()

        if dialog.result() == QDialog.DialogCode.Accepted and not dialog.task:
            options = dialog.get_options()
            options['plugin_id'] = 'org.quickfile.copy_operation' # Używamy nowego pluginu
            action_logger.log_action("copy", sources=source_paths, destination=destination_path, options=options)
            task = Task(TaskType.COPY, source_paths, destination_path, options)
            self.task_queue_manager.add_task(task)
            self.main_window.statusBar().showMessage(f"Added copy task to queue.")
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()
        elif dialog.result() == QDialog.DialogCode.Accepted and dialog.task:
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()

    def move_selected_item(self, checked=False):
        paths_to_move = self.ui_state_provider.get_selected_paths()
        if not paths_to_move:
            raise ValueError("No file/folder selected for moving.")
        destination_path = self.ui_state_provider.get_inactive_panel_path()
        if not destination_path:
            raise ValueError("No inactive panel path to move to.")
        
        dialog = MoveDialog(self.main_window, paths_to_move, destination_path, self.task_queue_manager, self.background_task_manager, self.theme_manager)
        dialog.exec()

        if dialog.result() == QDialog.DialogCode.Accepted and not dialog.task:
            options = dialog.get_options()
            options['plugin_id'] = 'org.quickfile.move_operation' # Używamy nowego pluginu
            action_logger.log_action("move", sources=paths_to_move, destination=destination_path, options=options)
            task = Task(TaskType.MOVE, paths_to_move, destination_path, options)
            self.task_queue_manager.add_task(task)
            self.main_window.statusBar().showMessage(f"Added move task to queue.")
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()
        elif dialog.result() == QDialog.DialogCode.Accepted and dialog.task:
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()

    def delete_selected_item(self, checked=False):
        selected_paths = self.ui_state_provider.get_selected_paths()
        if not selected_paths:
            raise ValueError("No file/folder selected for deletion.")
        
        dialog = DeleteDialog(self.main_window, selected_paths, self.task_queue_manager, self.background_task_manager, self.theme_manager)
        dialog.exec()

        if dialog.result() == QDialog.DialogCode.Accepted and not dialog.task:
            options = dialog.get_options()
            options['plugin_id'] = 'org.quickfile.delete_operation' # Używamy nowego pluginu
            action_logger.log_action("delete", paths=selected_paths, options=options)
            task = Task(TaskType.DELETE, selected_paths, options=options)
            self.task_queue_manager.add_task(task)
            self.main_window.statusBar().showMessage(f"Added delete task to queue.")
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()
        elif dialog.result() == QDialog.DialogCode.Accepted and dialog.task:
            self.ui_state_provider.folder_browser.refresh_all_views()
            self.ui_state_provider.folder_browser.clear_selection()

    def rename_selected_item(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path:
            raise ValueError("No file/folder selected for renaming.")
        old_name = os.path.basename(selected_path)
        new_name, ok = QInputDialog.getText(self.main_window, translation_manager.translate("DialogHandler", "Rename"), translation_manager.translate("DialogHandler", "New name:"), text=old_name)
        if ok and new_name:
            action_logger.log_action("rename", path=selected_path, new_name=new_name)
            message = self.file_manager.rename_item(selected_path, new_name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()
