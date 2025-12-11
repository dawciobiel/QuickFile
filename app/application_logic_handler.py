import os
import subprocess
import logging
from PyQt6.QtCore import QObject, Qt, QCoreApplication
from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog
from bookmarks.bookmarks_manager import BookmarksManager
from file_operations.file_manager import FileManager, FileManagerError
from file_operations.file_comparator import FileComparator
from file_operations.archive_manager import ArchiveManager, UnrarNotInstalledError
from file_operations.directory_synchronizer import DirectorySynchronizer, DirectorySynchronizerError
from file_operations.properties_manager import get_file_properties
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog
from utils.bookmark_dialog import BookmarkDialog
from utils.compare_dialog import CompareDialog
from utils.copy_dialog import CopyDialog
from utils.move_dialog import MoveDialog
from utils.delete_dialog import DeleteDialog
from utils.sync_dialog import SyncDialog
from utils.properties_dialog import PropertiesDialog


class ApplicationLogicHandler(QObject):
    def __init__(self, main_window, file_manager, file_comparator, bookmarks_manager, archive_manager, directory_synchronizer):
        super().__init__(main_window)
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.bookmarks_manager = bookmarks_manager
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer

        # Constants for repeated strings (from MenuPanel)
        self.ACTION_COMPARE = QCoreApplication.translate("MenuPanel", "Compare")
        self.ACTION_PROPERTIES = QCoreApplication.translate("MenuPanel", "Properties")
        self.ACTION_EXIT = QCoreApplication.translate("MenuPanel", "Exit")
        self.ACTION_CREATE_ARCHIVE = QCoreApplication.translate("MenuPanel", "Create Archive")
        self.ACTION_EXTRACT_ARCHIVE = QCoreApplication.translate("MenuPanel", "Extract Archive")
        self.ACTION_GO_UP = QCoreApplication.translate("MenuPanel", "Go Up")
        self.ACTION_REFRESH = QCoreApplication.translate("MenuPanel", "Refresh")
        self.ACTION_NEW_FILE = QCoreApplication.translate("MenuPanel", "New File")
        self.ACTION_NEW_FOLDER = QCoreApplication.translate("MenuPanel", "New Folder")
        self.ACTION_SEARCH = QCoreApplication.translate("MenuPanel", "Search")
        self.ACTION_COPY = QCoreApplication.translate("MenuPanel", "Copy")
        self.ACTION_PASTE = QCoreApplication.translate("MenuPanel", "Paste")
        self.ACTION_MOVE = QCoreApplication.translate("MenuPanel", "Move")
        self.ACTION_RENAME = QCoreApplication.translate("MenuPanel", "Rename")
        self.ACTION_DELETE = QCoreApplication.translate("MenuPanel", "Delete")
        self.ACTION_SYNCHRONIZE = QCoreApplication.translate("MenuPanel", "Synchronize")

        self.ERROR_NO_ACTIVE_PANEL = QCoreApplication.translate("MenuPanel", "No active panel.")
        self.ERROR_NO_CURRENT_DIR = QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel.")
        self.ERROR_FILE_CREATION = QCoreApplication.translate("MenuPanel", "File Creation Error")
        self.ERROR_FOLDER_CREATION = QCoreApplication.translate("MenuPanel", "Folder Creation Error")


    def _handle_f3_key(self):
        selected_path = self._get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)
        else:
            self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", "No file selected for preview."))

    def _handle_f4_key(self):
        selected_path = self._get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)  # Currently same as F3
        else:
            self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", "No file selected for editing."))

    def add_bookmark(self):
        """Adds the current directory of the active panel to bookmarks."""
        if self.main_window.folder_browser.active_panel:
            current_path = self.main_window.folder_browser.active_panel.model().filePath(self.main_window.folder_browser.active_panel.model().index(self.main_window.folder_browser.active_panel.model().rootPath()))
            self.bookmarks_manager.add_bookmark(current_path)
            self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", f"Bookmark added: {current_path}"))

    def update_status_bar_path(self, path):
        self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", "Current directory:") + f" {path}")

    def start_file_search(self):
        search_text = self.main_window.search_input.text()
        if search_text:
            current_path = self.main_window.folder_browser.current_paths.get(self.main_window.folder_browser.active_panel_widget)
            try:
                results, message = self.file_manager.search_files(current_path, search_text)
                self.show_search_results(results)
                self.main_window.status_bar.showMessage(message)
            except (FileNotFoundError, FileManagerError) as e:
                show_error_message(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "Search Error"), str(e))
        else:
            self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", "Enter text to search."))

    def show_search_results(self, results):
        """Displays search results in a dialog window."""
        dialog = SearchDialog(self.main_window, results)
        dialog.exec()

    def open_file_externally(self, file_path):
        """Opens the file using the system's default application."""
        if not os.path.exists(file_path):
            show_error_message(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "File Opening Error"), QCoreApplication.translate("ApplicationLogicHandler", f"File '{file_path}' does not exist."))
            return

        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
            self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", f"File opened: {file_path}"))
        except Exception as e:
            logging.exception(f"Error opening file externally '{file_path}': {e}")
            show_error_message(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "File Opening Error"), QCoreApplication.translate("ApplicationLogicHandler", f"Could not open file '{file_path}': {e}"))

    def _get_selected_file_path(self):
        """Returns the path to the selected file, if it is a file."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path and os.path.isfile(selected_path):
            return selected_path
        return None

    def compare_selected_items(self):
        self._compare_selected_items_logic()

    def _compare_selected_items_logic(self):
        left_selected_path = self.main_window.folder_browser.get_selected_path_for_panel(self.main_window.folder_browser.left_panel)
        right_selected_path = self.main_window.folder_browser.get_selected_path_for_panel(self.main_window.folder_browser.right_panel)

        if not left_selected_path or not right_selected_path:
            logging.warning("Comparison Error: User tried to compare without selecting items in both panels.")
            QMessageBox.warning(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "Comparison Error"), QCoreApplication.translate("ApplicationLogicHandler", "Please select items in both panels to compare."))
            return

        is_left_dir = os.path.isdir(left_selected_path)
        is_right_dir = os.path.isdir(right_selected_path)

        if is_left_dir and is_right_dir:
            # Compare directories
            self._compare_directories(left_selected_path, right_selected_path)
        elif not is_left_dir and not is_right_dir:
            # Compare files
            self._compare_files(left_selected_path, right_selected_path)
        else:
            logging.warning("Comparison Error: User tried to compare a file with a directory.")
            QMessageBox.warning(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "Comparison Error"), QCoreApplication.translate("ApplicationLogicHandler", "Cannot compare a file with a directory. Please select two files or two directories."))

    def _compare_files(self, file1_path, file2_path):
        are_identical = self.file_comparator.compare_files(file1_path, file2_path)
        if are_identical:
            QMessageBox.information(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "File Comparison Result"), QCoreApplication.translate("ApplicationLogicHandler", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are identical."))
        else:
            QMessageBox.information(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "File Comparison Result"), QCoreApplication.translate("ApplicationLogicHandler", f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are different."))

    def _compare_directories(self, dir1_path, dir2_path):
        dircmp_obj = self.file_comparator.compare_directories(dir1_path, dir2_path)
        if dircmp_obj:
            report = self.file_comparator.get_directory_comparison_report(dircmp_obj)
            dialog = CompareDialog(self.main_window, report, dir1_path, dir2_path)
            dialog.exec()
        else:
            logging.error("Directory Comparison Error: Could not compare directories. Ensure both paths are valid directories.")
            QMessageBox.critical(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "Directory Comparison Error"), QCoreApplication.translate("ApplicationLogicHandler", "Could not compare directories. Ensure both paths are valid directories."))

    def open_bookmark_dialog(self):
        """Opens the bookmarks dialog."""
        dialog = BookmarkDialog(self.bookmarks_manager.bookmarks, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_bookmark:
            self.main_window.folder_browser.navigate_to_path(dialog.selected_bookmark)

    def create_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            show_error_message(self.main_window, self.ACTION_CREATE_ARCHIVE, QCoreApplication.translate("MenuPanel", "No file/folder selected for archiving."))
            return

        archive_name, ok = QInputDialog.getText(self.main_window, self.ACTION_CREATE_ARCHIVE, QCoreApplication.translate("MenuPanel", "Archive name (without extension):"))
        if ok and archive_name:
            archive_path = os.path.join(os.path.dirname(selected_path), archive_name + ".zip")
            try:
                message = self.archive_manager.create_zip_archive(selected_path, archive_path)
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
            except Exception as e:
                show_error_message(self.main_window, self.ACTION_CREATE_ARCHIVE, str(e))

    def extract_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path or not any(selected_path.endswith(ext) for ext in ['.zip', '.tar', '.gz', '.bz2', '.xz', '.rar']):
            show_error_message(self.main_window, self.ACTION_EXTRACT_ARCHIVE, QCoreApplication.translate("MenuPanel", "No archive file selected or unsupported format."))
            return

        extract_path, ok = QInputDialog.getText(self.main_window, self.ACTION_EXTRACT_ARCHIVE, QCoreApplication.translate("MenuPanel", "Destination path:"), text=os.path.dirname(selected_path))
        if ok and extract_path:
            try:
                message = self.archive_manager.extract_archive(selected_path, extract_path)
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
            except (UnrarNotInstalledError, Exception) as e:
                show_error_message(self.main_window, self.ACTION_EXTRACT_ARCHIVE, str(e))

    def show_properties_dialog(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            show_error_message(self.main_window, self.ACTION_PROPERTIES, QCoreApplication.translate("MenuPanel", "No file or folder selected."))
            return
        properties = get_file_properties(selected_path)
        if properties:
            PropertiesDialog(properties, self.main_window).exec()
        else:
            show_error_message(self.main_window, self.ACTION_PROPERTIES, f"Could not retrieve properties for: {selected_path}")

    def synchronize_directories(self):
        left_path = self.main_window.folder_browser.current_paths.get(self.main_window.folder_browser.left_panel_widget)
        right_path = self.main_window.folder_browser.current_paths.get(self.main_window.folder_browser.right_panel_widget)
        if left_path and right_path:
            dialog = SyncDialog(self.main_window, left_path, right_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_options()
                try:
                    message = self.directory_synchronizer.synchronize(left_path, right_path, options)
                    self.main_window.status_bar.showMessage(message)
                    self.main_window.folder_browser.refresh_all_views()
                except Exception as e:
                    show_error_message(self.main_window, QCoreApplication.translate("ApplicationLogicHandler", "Synchronization Error"), str(e))

    def create_new_file(self):
        self._create_new_item("file")

    def create_new_directory(self):
        self._create_new_item("directory")

    def _create_new_item(self, item_type):
        active_panel = self.main_window.folder_browser.active_panel_widget
        if not active_panel:
            show_error_message(self.main_window, self.ERROR_FILE_CREATION if item_type == "file" else self.ERROR_FOLDER_CREATION, self.ERROR_NO_ACTIVE_PANEL)
            return

        current_dir = self.main_window.folder_browser.current_paths.get(active_panel)
        if not current_dir:
            show_error_message(self.main_window, self.ERROR_FILE_CREATION if item_type == "file" else self.ERROR_FOLDER_CREATION, self.ERROR_NO_CURRENT_DIR)
            return

        title = self.ACTION_NEW_FILE if item_type == "file" else self.ACTION_NEW_FOLDER
        label = QCoreApplication.translate("MenuPanel", "File name:") if item_type == "file" else QCoreApplication.translate("MenuPanel", "Folder name:")
        name, ok = QInputDialog.getText(self.main_window, title, label)

        if ok and name:
            try:
                if item_type == "file":
                    message = self.file_manager.create_file(current_dir, name)
                else:
                    message = self.file_manager.create_directory(current_dir, name)
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
            except (FileNotFoundError, FileExistsError, ValueError, FileManagerError) as e:
                show_error_message(self.main_window, title, str(e))

    def copy_selected_item(self):
        source_paths = self.main_window.folder_browser.get_selected_paths()
        if not source_paths:
            show_error_message(self.main_window, self.ACTION_COPY, QCoreApplication.translate("MenuPanel", "No file/folder selected for copying."))
            return

        active_widget = self.main_window.folder_browser.active_panel_widget
        inactive_widget = self.main_window.folder_browser.right_panel_widget if active_widget == self.main_window.folder_browser.left_panel_widget else self.main_window.folder_browser.left_panel_widget
        destination_path = self.main_window.folder_browser.current_paths.get(inactive_widget)

        if len(source_paths) == 1:
            dialog = CopyDialog(self.main_window, source_paths[0], destination_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    message = self.file_manager.copy_item_with_options(source_paths[0], destination_path, dialog.get_options())
                    self.main_window.status_bar.showMessage(message)
                    self.main_window.folder_browser.refresh_all_views()
                except (FileNotFoundError, FileExistsError, FileManagerError) as e:
                    show_error_message(self.main_window, self.ACTION_COPY, str(e))
        else:
            for source_path in source_paths:
                try:
                    self.file_manager.copy_item_with_options(source_path, destination_path, {"overwrite": False, "preserve_timestamp": True})
                except (FileNotFoundError, FileExistsError, FileManagerError) as e:
                    show_error_message(self.main_window, self.ACTION_COPY, f"Error copying {os.path.basename(source_path)}: {str(e)}")
                    return # Stop on first error
            self.main_window.status_bar.showMessage(QCoreApplication.translate("ApplicationLogicHandler", f"Copied {len(source_paths)} items to '{destination_path}'"))
            self.main_window.folder_browser.refresh_all_views()

    def move_selected_item(self):
        source_path = self.main_window.folder_browser.current_selected_path
        if not source_path:
            show_error_message(self.main_window, self.ACTION_MOVE, QCoreApplication.translate("MenuPanel", "No file/folder selected for moving."))
            return

        active_widget = self.main_window.folder_browser.active_panel_widget
        inactive_widget = self.main_window.folder_browser.right_panel_widget if active_widget == self.main_window.folder_browser.left_panel_widget else self.main_window.folder_browser.left_panel_widget
        destination_path = self.main_window.folder_browser.current_paths.get(inactive_widget)

        dialog = MoveDialog(self.main_window, source_path, destination_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                message = self.file_manager.move_item_with_options(source_path, destination_path, dialog.get_options())
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
            except (FileNotFoundError, FileExistsError, IsADirectoryError, FileManagerError) as e:
                show_error_message(self.main_window, self.ACTION_MOVE, str(e))

    def paste_item_to_current_dir(self):
        active_widget = self.main_window.folder_browser.active_panel_widget
        if not active_widget:
            show_error_message(self.main_window, self.ACTION_PASTE, self.ERROR_NO_ACTIVE_PANEL)
            return
        current_dir = self.main_window.folder_browser.current_paths.get(active_widget)
        if not current_dir:
            show_error_message(self.main_window, self.ACTION_PASTE, self.ERROR_NO_CURRENT_DIR)
            return
        try:
            message = self.file_manager.paste_item(current_dir)
            self.main_window.status_bar.showMessage(message)
            self.main_window.folder_browser.refresh_all_views()
        except (ValueError, FileNotFoundError, FileManagerError) as e:
            show_error_message(self.main_window, self.ACTION_PASTE, str(e))

    def delete_selected_item(self):
        selected_paths = self.main_window.folder_browser.get_selected_paths()
        if not selected_paths:
            show_error_message(self.main_window, self.ACTION_DELETE, QCoreApplication.translate("MenuPanel", "No file/folder selected for deletion."))
            return

        dialog = DeleteDialog(self.main_window, selected_paths)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for path in selected_paths:
                try:
                    message = self.file_manager.delete_item(path)
                    self.main_window.status_bar.showMessage(message)
                except (FileNotFoundError, FileManagerError) as e:
                    show_error_message(self.main_window, self.ACTION_DELETE, f"Error deleting {os.path.basename(path)}: {str(e)}")
                    return # Stop on first error
            self.main_window.folder_browser.refresh_all_views()

    def rename_selected_item(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            show_error_message(self.main_window, self.ACTION_RENAME, QCoreApplication.translate("MenuPanel", "No file/folder selected for renaming."))
            return

        old_name = os.path.basename(selected_path)
        new_name, ok = QInputDialog.getText(self.main_window, self.ACTION_RENAME, QCoreApplication.translate("MenuPanel", "New name:"), text=old_name)
        if ok and new_name:
            try:
                message = self.file_manager.rename_item(selected_path, new_name)
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
            except (FileNotFoundError, FileExistsError, ValueError, FileManagerError) as e:
                show_error_message(self.main_window, self.ACTION_RENAME, str(e))
        elif not new_name:
            show_error_message(self.main_window, self.ACTION_RENAME, QCoreApplication.translate("MenuPanel", "New name cannot be empty."))

    def apply_general_settings(self, new_view_mode, new_show_dot_files):
        # new_view_mode is now None, as it's no longer set in SettingsDialog
        if new_show_dot_files is not None: # Check if it's actually passed
            current_show_dot_files = self.main_window.settings_manager.get_setting("showDotFiles")
            if new_show_dot_files != current_show_dot_files:
                self.main_window.settings_manager.set_setting("showDotFiles", new_show_dot_files)
                self.main_window.folder_browser.set_show_dot_files(new_show_dot_files)

    def apply_shortcuts_settings(self, new_shortcuts):
        self.main_window.shortcuts_manager.save_shortcuts(new_shortcuts)
