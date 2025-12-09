import os
import subprocess
import logging
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox
from bookmarks.bookmarks_manager import BookmarksManager
from file_operations.file_manager import FileManager
from file_operations.file_comparator import FileComparator
from utils.dialogs import show_error_message
from utils.search_dialog import SearchDialog
from utils.bookmark_dialog import BookmarkDialog
from utils.compare_dialog import CompareDialog

class ApplicationLogicHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        # References to managers/components from MainWindow
        self.file_manager = FileManager(main_window)
        self.file_comparator = FileComparator()
        self.bookmarks_manager = BookmarksManager()

    def _handle_f3_key(self):
        selected_path = self._get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)
        else:
            self.main_window.status_bar.showMessage(self.main_window.tr("No file selected for preview."))

    def _handle_f4_key(self):
        selected_path = self._get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)  # Currently same as F3
        else:
            self.main_window.status_bar.showMessage(self.main_window.tr("No file selected for editing."))

    def add_bookmark(self):
        """Adds the current directory of the active panel to bookmarks."""
        if self.main_window.folder_browser.active_panel:
            current_path = self.main_window.folder_browser.active_panel.model().filePath(self.main_window.folder_browser.active_panel.model().index(self.main_window.folder_browser.active_panel.model().rootPath()))
            self.bookmarks_manager.add_bookmark(current_path)
            self.main_window.status_bar.showMessage(self.main_window.tr(f"Bookmark added: {current_path}"))

    def update_status_bar_path(self, path):
        self.main_window.status_bar.showMessage(self.main_window.tr("Current directory:") + f" {path}")

    def start_file_search(self):
        search_text = self.main_window.search_input.text()
        if search_text:
            current_path = self.main_window.folder_browser.current_paths.get(self.main_window.folder_browser.active_panel_widget)
            results = self.file_manager.search_files(current_path, search_text)
            self.show_search_results(results)
        else:
            self.main_window.status_bar.showMessage(self.main_window.tr("Enter text to search."))

    def show_search_results(self, results):
        """Displays search results in a dialog window."""
        dialog = SearchDialog(self.main_window, results)
        dialog.exec()

    def open_file_externally(self, file_path):
        """Opens the file using the system's default application."""
        if not os.path.exists(file_path):
            show_error_message(self.main_window, self.main_window.tr("File Opening Error"), self.main_window.tr(f"File '{file_path}' does not exist."))
            return

        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
            self.main_window.status_bar.showMessage(self.main_window.tr(f"File opened: {file_path}"))
        except Exception as e:
            logging.exception(f"Error opening file externally '{file_path}': {e}")
            show_error_message(self.main_window, self.main_window.tr("File Opening Error"), self.main_window.tr(f"Could not open file '{file_path}': {e}"))

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
            QMessageBox.warning(self.main_window, self.main_window.tr("Comparison Error"), self.main_window.tr("Please select items in both panels to compare."))
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
            QMessageBox.warning(self.main_window, self.main_window.tr("Comparison Error"), self.main_window.tr("Cannot compare a file with a directory. Please select two files or two directories."))

    def _compare_files(self, file1_path, file2_path):
        are_identical = self.file_comparator.compare_files(file1_path, file2_path)
        if are_identical:
            QMessageBox.information(self.main_window, self.main_window.tr("File Comparison Result"), self.main_window.tr(f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are identical."))
        else:
            QMessageBox.information(self.main_window, self.main_window.tr("File Comparison Result"), self.main_window.tr(f"Files '{os.path.basename(file1_path)}' and '{os.path.basename(file2_path)}' are different."))

    def _compare_directories(self, dir1_path, dir2_path):
        dircmp_obj = self.file_comparator.compare_directories(dir1_path, dir2_path)
        if dircmp_obj:
            report = self.file_comparator.get_directory_comparison_report(dircmp_obj)
            dialog = CompareDialog(self.main_window, report, dir1_path, dir2_path)
            dialog.exec()
        else:
            logging.error("Directory Comparison Error: Could not compare directories. Ensure both paths are valid directories.")
            QMessageBox.critical(self.main_window, self.main_window.tr("Directory Comparison Error"), self.main_window.tr("Could not compare directories. Ensure both paths are valid directories."))

    def open_bookmark_dialog(self):
        """Opens the bookmarks dialog."""
        dialog = BookmarkDialog(self.bookmarks_manager.bookmarks, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_bookmark:
            self.main_window.folder_browser.navigate_to_path(dialog.selected_bookmark)
