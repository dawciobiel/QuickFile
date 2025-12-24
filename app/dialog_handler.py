import logging
import os

from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog

from app.background_task_manager import BackgroundTaskManager
from app.settings_manager import SettingsManager
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from favorites.favorites_manager import FavoritesManager
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager, FileManagerError
from file_operations.properties_manager import get_file_properties
from utils.favorites_dialog import FavoritesDialog
from utils.compare_dialog import CompareDialog
from utils.copy_dialog import CopyDialog
from utils.delete_dialog import DeleteDialog
from utils.move_dialog import MoveDialog
from utils.properties_dialog import PropertiesDialog
from utils.search_dialog import SearchDialog
from utils.settings_dialog import SettingsDialog
from utils.shortcuts_dialog import ShortcutsDialog
from utils.sync_dialog import SyncDialog


class DialogHandler:
    def __init__(self, main_window, file_manager: FileManager, file_comparator: FileComparator,
                 favorites_manager: FavoritesManager, archive_manager: ArchiveManager,
                 directory_synchronizer: DirectorySynchronizer, ui_state_provider: UIStateProvider,
                 settings_manager: SettingsManager, background_task_manager: BackgroundTaskManager):
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.favorites_manager = favorites_manager
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.ui_state_provider = ui_state_provider
        self.settings_manager = settings_manager
        self.background_task_manager = background_task_manager

    def show_properties_dialog(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No file or folder selected."))
        properties = get_file_properties(selected_path)
        if properties:
            PropertiesDialog(properties, self.main_window).exec()
        else:
            raise ValueError(f"Could not retrieve properties for: {selected_path}")

    def open_general_settings_dialog(self, checked=False):
        dialog = SettingsDialog(self.main_window, self.settings_manager, self.main_window.theme_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            return new_settings
        return None

    def open_shortcuts_dialog(self, checked=False):
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            self.main_window.shortcuts_manager.apply_shortcuts_settings(new_shortcuts)

    def show_search_results(self, results):
        dialog = SearchDialog(self.main_window, results)
        dialog.exec()

    def _compare_files(self, file1_path, file2_path):
        are_identical = self.file_comparator.compare_files(file1_path, file2_path)
        if are_identical:
            QMessageBox.information(self.main_window, "File Comparison Result", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are identical.")
        else:
            QMessageBox.information(self.main_window, "File Comparison Result", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are different.")

    def _compare_directories(self, dir1_path, dir2_path):
        dircmp_obj = self.file_comparator.compare_directories(dir1_path, dir2_path)
        if dircmp_obj:
            report = self.file_comparator.get_directory_comparison_report(dircmp_obj)
            dialog = CompareDialog(self.main_window, report, dir1_path, dir2_path)
            dialog.exec()
        else:
            logging.error("Directory Comparison Error: Could not compare directories.")
            QMessageBox.critical(self.main_window, "Directory Comparison Error", "Could not compare directories. Ensure both paths are valid directories.")

    def open_favorites_dialog(self, checked=False):
        favorites = self.favorites_manager.get_favorites()
        dialog = FavoritesDialog(favorites, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_favorite:
            self.ui_state_provider.folder_browser.navigate_to_path(dialog.selected_favorite)

    def create_archive(self, checked=False):
        paths_to_archive = self.ui_state_provider.get_selected_paths()
        if not paths_to_archive:
            raise ValueError("No file/folder selected for archiving.")
        if len(paths_to_archive) > 1:
            base_dir = self.ui_state_provider.get_active_panel_path()
        else:
            base_dir = os.path.dirname(paths_to_archive[0])
        archive_name, ok = QInputDialog.getText(self.main_window, "Create Archive", "Archive name (without extension):")
        if ok and archive_name:
            archive_path = os.path.join(base_dir, archive_name + ".zip")
            message = self.archive_manager.create_zip_archive(paths_to_archive, archive_path)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def extract_archive(self, checked=False):
        selected_archive_path = self.ui_state_provider.get_current_selected_path()
        if not selected_archive_path:
            raise ValueError("No archive file selected.")
        extract_path, ok = QInputDialog.getText(self.main_window, "Extract Archive", "Destination path:", text=os.path.dirname(selected_archive_path))
        if ok and extract_path:
            message = self.archive_manager.extract_archive(selected_archive_path, extract_path)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def synchronize_directories(self, checked=False):
        left_path = self.ui_state_provider.folder_browser.get_left_panel_widget().file_view.get_current_path()
        right_path = self.ui_state_provider.folder_browser.get_right_panel_widget().file_view.get_current_path()
        if left_path and right_path:
            dialog = SyncDialog(self.main_window, left_path, right_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_options()
                message = self.directory_synchronizer.synchronize(left_path, right_path, options)
                self.main_window.statusBar().showMessage(message)
                self.ui_state_provider.folder_browser.refresh_all_views()
        else:
            raise ValueError("Both panels must have valid paths for synchronization.")

    def create_new_file(self, current_dir=None, checked=False):
        if not current_dir:
            current_dir = self.ui_state_provider.get_active_panel_path()
        name, ok = QInputDialog.getText(self.main_window, "New File", "File name:")
        if ok and name:
            message = self.file_manager.create_file(current_dir, name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def create_new_directory(self, current_dir=None, checked=False):
        if not current_dir:
            current_dir = self.ui_state_provider.get_active_panel_path()
        name, ok = QInputDialog.getText(self.main_window, "New Folder", "Folder name:")
        if ok and name:
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

        dialog = CopyDialog(self.main_window, source_paths[0], destination_path, self.file_manager, self.background_task_manager)
        dialog.exec()
        self.ui_state_provider.folder_browser.refresh_all_views()

    def move_selected_item(self, checked=False):
        paths_to_move = self.ui_state_provider.get_selected_paths()
        if not paths_to_move:
            raise ValueError("No file/folder selected for moving.")
        destination_path = self.ui_state_provider.get_inactive_panel_path()
        if not destination_path:
            raise ValueError("No inactive panel path to move to.")
        
        dialog = MoveDialog(self.main_window, paths_to_move[0], destination_path, self.file_manager, self.background_task_manager)
        dialog.exec()
        self.ui_state_provider.folder_browser.refresh_all_views()

    def paste_item_to_current_dir(self, checked=False):
        current_dir = self.ui_state_provider.get_active_panel_path()
        if not current_dir:
            raise ValueError("Could not determine current directory for active panel.")
        message = self.file_manager.paste_item(current_dir)
        self.main_window.statusBar().showMessage(message)
        self.ui_state_provider.folder_browser.refresh_all_views()

    def delete_selected_item(self, checked=False):
        selected_paths = self.ui_state_provider.get_selected_paths()
        if not selected_paths:
            raise ValueError("No file/folder selected for deletion.")
        
        dialog = DeleteDialog(self.main_window, selected_paths, self.file_manager, self.background_task_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.main_window.statusBar().showMessage(f"Deleted {len(selected_paths)} items.")
            self.ui_state_provider.folder_browser.refresh_all_views()

    def rename_selected_item(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path:
            raise ValueError("No file/folder selected for renaming.")
        old_name = os.path.basename(selected_path)
        new_name, ok = QInputDialog.getText(self.main_window, "Rename", "New name:", text=old_name)
        if ok and new_name:
            message = self.file_manager.rename_item(selected_path, new_name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()
