import logging
import os

from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog

from app.settings_manager import SettingsManager  # Corrected import from app.settings_manager
from app.translation_manager import translation_manager
from app.ui_state_provider import UIStateProvider
from bookmarks.bookmarks_manager import BookmarksManager
from file_operations.archive_manager import ArchiveManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_comparator import FileComparator
from file_operations.file_manager import FileManager, FileManagerError
from file_operations.properties_manager import get_file_properties
from utils.bookmark_dialog import BookmarkDialog
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
                 bookmarks_manager: BookmarksManager, archive_manager: ArchiveManager,
                 directory_synchronizer: DirectorySynchronizer, ui_state_provider: UIStateProvider,
                 settings_manager: SettingsManager): # Changed type hint to SettingsManager
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.bookmarks_manager = bookmarks_manager
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.ui_state_provider = ui_state_provider
        self.settings_manager = settings_manager # Stored as settings_manager

        # Action names for QInputDialog titles (translated)
        self.ACTION_CREATE_ARCHIVE = translation_manager.translate("MenuPanel", "Create Archive")
        self.ACTION_EXTRACT_ARCHIVE = translation_manager.translate("MenuPanel", "Extract Archive")
        self.ACTION_NEW_FILE = translation_manager.translate("MenuPanel", "New File")
        self.ACTION_NEW_FOLDER = translation_manager.translate("MenuPanel", "New Folder")
        self.ACTION_RENAME = translation_manager.translate("MenuPanel", "Rename")

        # Error messages (translated)
        self.ERROR_NO_CURRENT_DIR = translation_manager.translate("MenuPanel", "Could not determine current directory for active panel.")

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
        # Pass self.settings_manager (which is SettingsManager) and self.main_window.theme_manager
        dialog = SettingsDialog(self.main_window, self.settings_manager, self.main_window.theme_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            return new_settings  # Return new settings instead of applying them directly
        return None  # Return None if dialog is cancelled

    def open_shortcuts_dialog(self, checked=False):
        # Pass self.main_window.shortcuts_manager (which is ShortcutsManager)
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            # Apply shortcuts via shortcuts_manager
            self.main_window.shortcuts_manager.apply_shortcuts_settings(new_shortcuts)

    def show_search_results(self, results):
        dialog = SearchDialog(self.main_window, results)
        dialog.exec()

    def _compare_files(self, file1_path, file2_path):
        are_identical = self.file_comparator.compare_files(file1_path, file2_path)
        if are_identical:
            QMessageBox.information(self.main_window, translation_manager.translate("ApplicationLogicHandler", "File Comparison Result"), translation_manager.translate("ApplicationLogicHandler", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are identical."))
        else:
            QMessageBox.information(self.main_window, translation_manager.translate("ApplicationLogicHandler", "File Comparison Result"), translation_manager.translate("ApplicationLogicHandler", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are different."))

    def _compare_directories(self, dir1_path, dir2_path):
        dircmp_obj = self.file_comparator.compare_directories(dir1_path, dir2_path)
        if dircmp_obj:
            report = self.file_comparator.get_directory_comparison_report(dircmp_obj)
            dialog = CompareDialog(self.main_window, report, dir1_path, dir2_path)
            dialog.exec()
        else:
            logging.error("Directory Comparison Error: Could not compare directories. Ensure both paths are valid directories.")
            QMessageBox.critical(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Directory Comparison Error"), translation_manager.translate("ApplicationLogicHandler", "Could not compare directories. Ensure both paths are valid directories."))

    def open_bookmark_dialog(self, checked=False):
        bookmarks = self.bookmarks_manager.get_bookmarks()
        dialog = BookmarkDialog(bookmarks, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_bookmark:
            self.ui_state_provider.folder_browser.navigate_to_path(dialog.selected_bookmark)

    def create_archive(self, checked=False):
        paths_to_archive = self.ui_state_provider.get_selected_paths()
        
        if not paths_to_archive:
            current_selected_path = self.ui_state_provider.get_current_selected_path()
            if current_selected_path:
                paths_to_archive = [current_selected_path]
            else:
                raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for archiving."))

        if len(paths_to_archive) > 1:
            base_dir = self.ui_state_provider.get_active_panel_path()
        else:
            base_dir = os.path.dirname(paths_to_archive[0])

        archive_name, ok = QInputDialog.getText(self.main_window, self.ACTION_CREATE_ARCHIVE, translation_manager.translate("MenuPanel", "Archive name (without extension):"))
        if ok and archive_name:
            archive_path = os.path.join(base_dir, archive_name + ".zip")
            message = self.archive_manager.create_zip_archive(paths_to_archive, archive_path)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def extract_archive(self, checked=False):
        selected_archive_path = self.ui_state_provider.get_current_selected_path()
        if not selected_archive_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No archive file selected."))

        file_extension = os.path.splitext(selected_archive_path)[1].lower()
        
        extract_path, ok = QInputDialog.getText(self.main_window, self.ACTION_EXTRACT_ARCHIVE, translation_manager.translate("MenuPanel", "Destination path:"), text=os.path.dirname(selected_archive_path))
        if ok and extract_path:
            message = ""
            if file_extension == '.zip':
                message = self.archive_manager.extract_zip_archive(selected_archive_path, extract_path)
            elif file_extension in ['.tar', '.gz', '.bz2', '.xz']:
                message = self.archive_manager.extract_tar_archive(selected_archive_path, extract_path)
            elif file_extension == '.rar':
                message = self.archive_manager.extract_rar_archive(selected_archive_path, extract_path)
            else:
                raise ValueError(translation_manager.translate("MenuPanel", "Unsupported archive format."))

            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()

    def synchronize_directories(self, checked=False):
        left_panel = self.ui_state_provider.folder_browser.get_left_panel_widget()
        right_panel = self.ui_state_provider.folder_browser.get_right_panel_widget()
        
        left_path = left_panel.file_view.get_current_path() if left_panel else None
        right_path = right_panel.file_view.get_current_path() if right_panel else None

        if left_path and right_path:
            dialog = SyncDialog(self.main_window, left_path, right_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_options()
                message = self.directory_synchronizer.synchronize(left_path, right_path, options)
                self.main_window.statusBar().showMessage(message)
                self.ui_state_provider.folder_browser.refresh_all_views()
        else:
            raise ValueError(translation_manager.translate("ApplicationLogicHandler", "Both panels must have valid paths for synchronization."))

    def create_new_file(self, current_dir=None, checked=False):
        self._create_new_item("file", current_dir)

    def create_new_directory(self, current_dir=None, checked=False):
        self._create_new_item("directory", current_dir)

    def _create_new_item(self, item_type, current_dir=None):
        if current_dir is None:
            current_dir = self.ui_state_provider.get_active_panel_path()
        
        if not current_dir:
            raise ValueError(self.ERROR_NO_CURRENT_DIR)

        title = self.ACTION_NEW_FILE if item_type == "file" else self.ACTION_NEW_FOLDER
        label = translation_manager.translate("MenuPanel", "File name:") if item_type == "file" else translation_manager.translate("MenuPanel", "Folder name:")
        name, ok = QInputDialog.getText(self.main_window, title, label)

        if ok and name:
            if item_type == "file":
                message = self.file_manager.create_file(current_dir, name)
            else:
                message = self.file_manager.create_directory(current_dir, name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()
        elif ok and not name:
            raise ValueError(translation_manager.translate("MenuPanel", "Name cannot be empty."))

    def copy_selected_item(self, checked=False):
        source_paths = self.ui_state_provider.get_selected_paths()
        if not source_paths:
            raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for copying."))

        destination_path = self.ui_state_provider.get_inactive_panel_path()
        if not destination_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No inactive panel path to copy to."))

        if len(source_paths) == 1:
            dialog = CopyDialog(self.main_window, source_paths[0], destination_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                message = self.file_manager.copy_item_with_options(source_paths[0], destination_path, dialog.get_options())
                self.main_window.statusBar().showMessage(message)
                self.ui_state_provider.folder_browser.refresh_all_views()
        else:
            all_successful = True
            options = {"overwrite": False, "preserve_timestamp": True} 
            for source_path in source_paths:
                self.file_manager.copy_item_with_options(source_path, destination_path, options)
            if all_successful:
                self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", f"Copied {len(source_paths)} items to '{destination_path}'"))
            self.ui_state_provider.folder_browser.refresh_all_views()

    def move_selected_item(self, checked=False):
        paths_to_move = self.ui_state_provider.get_selected_paths()
        
        if not paths_to_move:
            current_selected_path = self.ui_state_provider.get_current_selected_path()
            if current_selected_path:
                paths_to_move = [current_selected_path]
            else:
                raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for moving."))

        destination_path = self.ui_state_provider.get_inactive_panel_path()
        if not destination_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No inactive panel path to move to."))

        if len(paths_to_move) == 1:
            dialog = MoveDialog(self.main_window, paths_to_move[0], destination_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                message = self.file_manager.move_item_with_options(paths_to_move[0], destination_path, dialog.get_options())
                self.main_window.statusBar().showMessage(message)
                self.ui_state_provider.folder_browser.refresh_all_views()
        else:
            all_successful = True
            options = {"overwrite": False, "preserve_timestamp": True} 
            for source_path in paths_to_move:
                self.file_manager.move_item_with_options(source_path, destination_path, options)
            if all_successful:
                self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", f"Moved {len(paths_to_move)} items to '{destination_path}'"))
            self.ui_state_provider.folder_browser.refresh_all_views()

    def paste_item_to_current_dir(self, checked=False):
        current_dir = self.ui_state_provider.get_active_panel_path()
        if not current_dir:
            raise ValueError(self.ERROR_NO_CURRENT_DIR)
        message = self.file_manager.paste_item(current_dir)
        self.main_window.statusBar().showMessage(message)
        self.ui_state_provider.folder_browser.refresh_all_views()

    def delete_selected_item(self, checked=False):
        selected_paths = self.ui_state_provider.get_selected_paths()
        if not selected_paths:
            raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for deletion."))

        dialog = DeleteDialog(self.main_window, selected_paths)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            move_to_trash = dialog.should_move_to_trash() # Get the state of the checkbox
            all_successful = True
            for path in selected_paths:
                try:
                    self.file_manager.delete_item(path, move_to_trash=move_to_trash) # Pass move_to_trash
                except FileManagerError as e:
                    logging.error(f"Error deleting item {path}: {e}")
                    all_successful = False
            if all_successful:
                self.main_window.statusBar().showMessage(translation_manager.translate("ApplicationLogicHandler", f"Deleted {len(selected_paths)} items."))
            self.ui_state_provider.folder_browser.refresh_all_views()

    def rename_selected_item(self, checked=False):
        selected_path = self.ui_state_provider.get_current_selected_path()
        if not selected_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for renaming."))

        old_name = os.path.basename(selected_path)
        new_name, ok = QInputDialog.getText(self.main_window, self.ACTION_RENAME, translation_manager.translate("MenuPanel", "New name:"), text=old_name)
        if ok and new_name:
            message = self.file_manager.rename_item(selected_path, new_name)
            self.main_window.statusBar().showMessage(message)
            self.ui_state_provider.folder_browser.refresh_all_views()
        elif ok and not new_name:
            raise ValueError(translation_manager.translate("MenuPanel", "New name cannot be empty."))
