import os
import subprocess
import logging
from functools import wraps
from PyQt6.QtCore import QObject, Qt
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
from app.translation_manager import translation_manager

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
    def __init__(self, main_window, file_manager, file_comparator, bookmarks_manager, archive_manager, directory_synchronizer, theme_manager):
        super().__init__(main_window)
        self.main_window = main_window
        self.file_manager = file_manager
        self.file_comparator = file_comparator
        self.bookmarks_manager = bookmarks_manager
        self.archive_manager = archive_manager
        self.directory_synchronizer = directory_synchronizer
        self.theme_manager = theme_manager
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
        """Returns the currently active PanelWidget."""
        return self.main_window.folder_browser.active_panel_widget

    def _get_active_panel_path(self):
        """Returns the current path of the active panel, or None if no active panel."""
        active_panel = self._get_active_panel_widget()
        if active_panel:
            return active_panel.file_view.get_current_path()
        return None

    def _get_inactive_panel_path(self):
        """Returns the current path of the inactive panel, or None if no inactive panel."""
        active_panel = self._get_active_panel_widget()
        if active_panel == self.main_window.folder_browser.left_panel_widget:
            return self.main_window.folder_browser.right_panel_widget.file_view.get_current_path()
        elif active_panel == self.main_window.folder_browser.right_panel_widget:
            return self.main_window.folder_browser.left_panel_widget.file_view.get_current_path()
        return None

    def _get_selected_file_path(self):
        """Returns the path of the single selected file in the active panel, or None."""
        selected_path = self.main_window.folder_browser.get_current_selected_path()
        if selected_path and os.path.isfile(selected_path):
            return selected_path
        return None

    def on_theme_changed(self, theme_path):
        # Instead of calling load_file_styles on the model,
        # call update_view_settings on the file_view, which will refresh the model and delegate.
        self.main_window.folder_browser.left_panel_widget.file_view.update_view_settings()
        self.main_window.folder_browser.right_panel_widget.file_view.update_view_settings()

    @handle_app_logic_error("Preview Error")
    def _handle_f3_key(self):
        selected_path = self._get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)
        else:
            self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", "No file selected for preview."))

    @handle_app_logic_error("Edit Error")
    def _handle_f4_key(self):
        selected_path = self._get_selected_file_path()
        if selected_path:
            self.open_file_externally(selected_path)
        else:
            self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", "No file selected for editing."))

    @handle_app_logic_error("Bookmark Error")
    def add_bookmark(self):
        current_path = self._get_active_panel_path()
        if current_path:
            self.bookmarks_manager.add_bookmark(current_path)
            self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", f"Bookmark added: {current_path}"))
        else:
            show_error_message(self.main_window, self.ACTION_CREATE_ARCHIVE, self.ERROR_NO_CURRENT_DIR)


    def update_status_bar_path(self, path):
        self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", "Current directory:") + f" {path}")

    @handle_app_logic_error("Search Error")
    def start_file_search(self):
        search_text = self.main_window.search_input.text()
        if search_text:
            current_path = self._get_active_panel_path()
            if not current_path:
                show_error_message(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Search Error"), self.ERROR_NO_CURRENT_DIR)
                return
            results, message = self.file_manager.search_files(current_path, search_text)
            self.show_search_results(results)
            self.main_window.status_bar.showMessage(message)
        else:
            self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", "Enter text to search."))

    def show_search_results(self, results):
        dialog = SearchDialog(self.main_window, results)
        dialog.exec()

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
        self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", f"File opened: {file_path}"))

    @handle_app_logic_error("Comparison Error")
    def compare_selected_items(self):
        self._compare_selected_items_logic()

    def _compare_selected_items_logic(self):
        left_selected_path = self.main_window.folder_browser.left_panel_widget.file_view.get_current_selected_path()
        right_selected_path = self.main_window.folder_browser.right_panel_widget.file_view.get_current_selected_path()

        if not left_selected_path or not right_selected_path:
            logging.warning("Comparison Error: User tried to compare without selecting items in both panels.")
            QMessageBox.warning(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Comparison Error"), translation_manager.translate("ApplicationLogicHandler", "Please select items in both panels to compare."))
            return

        is_left_dir = os.path.isdir(left_selected_path)
        is_right_dir = os.path.isdir(right_selected_path)

        if is_left_dir and is_right_dir:
            self._compare_directories(left_selected_path, right_selected_path)
        elif not is_left_dir and not is_right_dir:
            self._compare_files(left_selected_path, right_selected_path)
        else:
            logging.warning("Comparison Error: User tried to compare a file with a directory.")
            QMessageBox.warning(self.main_window, translation_manager.translate("ApplicationLogicHandler", "Comparison Error"), translation_manager.translate("ApplicationLogicHandler", "Cannot compare a file with a directory. Please select two files or two directories."))

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

    @handle_app_logic_error("Open Bookmark Error")
    def open_bookmark_dialog(self):
        bookmarks = self.bookmarks_manager.get_bookmarks()
        dialog = BookmarkDialog(bookmarks, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_bookmark:
            self.main_window.folder_browser.navigate_to_path(dialog.selected_bookmark)

    @handle_app_logic_error("Create Archive Error")
    def create_archive(self):
        paths_to_archive = self.main_window.folder_browser.get_selected_paths()
        
        if not paths_to_archive:
            current_selected_path = self.main_window.folder_browser.get_current_selected_path()
            if current_selected_path:
                paths_to_archive = [current_selected_path]
            else:
                raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for archiving."))

        if len(paths_to_archive) > 1:
            base_dir = self._get_active_panel_path()
        else:
            base_dir = os.path.dirname(paths_to_archive[0])

        archive_name, ok = QInputDialog.getText(self.main_window, self.ACTION_CREATE_ARCHIVE, translation_manager.translate("MenuPanel", "Archive name (without extension):"))
        if ok and archive_name:
            archive_path = os.path.join(base_dir, archive_name + ".zip")
            message = self.archive_manager.create_zip_archive(paths_to_archive, archive_path)
            self.main_window.status_bar.showMessage(message)
            self.main_window.folder_browser.refresh_all_views()

    @handle_app_logic_error("Extract Archive Error")
    def extract_archive(self):
        selected_archive_path = self.main_window.folder_browser.get_current_selected_path()
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

            self.main_window.status_bar.showMessage(message)
            self.main_window.folder_browser.refresh_all_views()

    @handle_app_logic_error("Properties Error")
    def show_properties_dialog(self):
        selected_path = self.main_window.folder_browser.get_current_selected_path()
        if not selected_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No file or folder selected."))
        properties = get_file_properties(selected_path)
        if properties:
            PropertiesDialog(properties, self.main_window).exec()
        else:
            raise ValueError(f"Could not retrieve properties for: {selected_path}")

    @handle_app_logic_error("Synchronization Error")
    def synchronize_directories(self):
        left_path = self.main_window.folder_browser.left_panel_widget.file_view.get_current_path()
        right_path = self.main_window.folder_browser.right_panel_widget.file_view.get_current_path()
        if left_path and right_path:
            dialog = SyncDialog(self.main_window, left_path, right_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_options()
                message = self.directory_synchronizer.synchronize(left_path, right_path, options)
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
        else:
            raise ValueError(translation_manager.translate("ApplicationLogicHandler", "Both panels must have valid paths for synchronization."))

    def create_new_file(self, current_dir=None):
        self._create_new_item("file", current_dir)

    def create_new_directory(self, current_dir=None):
        self._create_new_item("directory", current_dir)

    @handle_app_logic_error("Create Item Error")
    def _create_new_item(self, item_type, current_dir=None):
        if current_dir is None:
            current_dir = self._get_active_panel_path()
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
            self.main_window.status_bar.showMessage(message)
            self.main_window.folder_browser.refresh_all_views()
        elif not name:
            raise ValueError(translation_manager.translate("MenuPanel", "Name cannot be empty."))

    @handle_app_logic_error("Copy Error")
    def copy_selected_item(self):
        source_paths = self.main_window.folder_browser.get_selected_paths()
        if not source_paths:
            raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for copying."))

        destination_path = self._get_inactive_panel_path()
        if not destination_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No inactive panel path to copy to."))

        if len(source_paths) == 1:
            dialog = CopyDialog(self.main_window, source_paths[0], destination_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                message = self.file_manager.copy_item_with_options(source_paths[0], destination_path, dialog.get_options())
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
        else:
            all_successful = True
            options = {"overwrite": False, "preserve_timestamp": True} 
            for source_path in source_paths:
                self.file_manager.copy_item_with_options(source_path, destination_path, options)
            if all_successful:
                self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", f"Copied {len(source_paths)} items to '{destination_path}'"))
            self.main_window.folder_browser.refresh_all_views()

    @handle_app_logic_error("Move Error")
    def move_selected_item(self):
        paths_to_move = self.main_window.folder_browser.get_selected_paths()
        
        if not paths_to_move:
            current_selected_path = self.main_window.folder_browser.get_current_selected_path()
            if current_selected_path:
                paths_to_move = [current_selected_path]
            else:
                raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for moving."))

        destination_path = self._get_inactive_panel_path()
        if not destination_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No inactive panel path to move to."))

        if len(paths_to_move) == 1:
            dialog = MoveDialog(self.main_window, paths_to_move[0], destination_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                message = self.file_manager.move_item_with_options(paths_to_move[0], destination_path, dialog.get_options())
                self.main_window.status_bar.showMessage(message)
                self.main_window.folder_browser.refresh_all_views()
        else:
            all_successful = True
            options = {"overwrite": False, "preserve_timestamp": True} 
            for source_path in paths_to_move:
                self.file_manager.move_item_with_options(source_path, destination_path, options)
            if all_successful:
                self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", f"Moved {len(paths_to_move)} items to '{destination_path}'"))
            self.main_window.folder_browser.refresh_all_views()

    @handle_app_logic_error("Paste Error")
    def paste_item_to_current_dir(self):
        current_dir = self._get_active_panel_path()
        if not current_dir:
            raise ValueError(self.ERROR_NO_CURRENT_DIR)
        message = self.file_manager.paste_item(current_dir)
        self.main_window.status_bar.showMessage(message)
        self.main_window.folder_browser.refresh_all_views()

    @handle_app_logic_error("Delete Error")
    def delete_selected_item(self):
        selected_paths = self.main_window.folder_browser.get_selected_paths()
        if not selected_paths:
            raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for deletion."))

        dialog = DeleteDialog(self.main_window, selected_paths)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            all_successful = True
            for path in selected_paths:
                self.file_manager.delete_item(path)
            if all_successful:
                self.main_window.status_bar.showMessage(translation_manager.translate("ApplicationLogicHandler", f"Deleted {len(selected_paths)} items."))
            self.main_window.folder_browser.refresh_all_views()

    @handle_app_logic_error("Rename Error")
    def rename_selected_item(self):
        selected_path = self.main_window.folder_browser.get_current_selected_path()
        if not selected_path:
            raise ValueError(translation_manager.translate("MenuPanel", "No file/folder selected for renaming."))

        old_name = os.path.basename(selected_path)
        new_name, ok = QInputDialog.getText(self.main_window, self.ACTION_RENAME, translation_manager.translate("MenuPanel", "New name:"), text=old_name)
        if ok and new_name:
            message = self.file_manager.rename_item(selected_path, new_name)
            self.main_window.status_bar.showMessage(message)
            self.main_window.folder_browser.refresh_all_views()
        elif not new_name:
            raise ValueError(translation_manager.translate("MenuPanel", "New name cannot be empty."))

    def apply_general_settings(self, new_settings: dict):
        settings_changed = False
        language_settings_changed = False

        # Helper to update setting and trigger folder_browser update if needed
        def update_setting(setting_key, folder_browser_method=None):
            nonlocal settings_changed
            nonlocal language_settings_changed
            current_value = self.main_window.settings_manager.get_setting(setting_key)
            new_value = new_settings.get(setting_key)
            if new_value is not None and new_value != current_value:
                self.main_window.settings_manager.set_setting(setting_key, new_value)
                if folder_browser_method:
                    getattr(self.main_window.folder_browser, folder_browser_method)(new_value)
                settings_changed = True
                if setting_key in ["language_mode", "manual_language"]:
                    language_settings_changed = True

        update_setting("showDotFiles", "set_show_dot_files")
        update_setting("file_permissions_display_mode", "set_file_permissions_display_mode")
        update_setting("show_uid_column", "set_show_uid_column")
        update_setting("show_gid_column", "set_show_gid_column")
        update_setting("language_mode")
        update_setting("manual_language")
        
        # Theme is handled separately due to theme_manager.apply_theme
        current_theme = self.main_window.settings_manager.get_setting("theme")
        new_theme = new_settings.get("theme")
        if new_theme is not None and new_theme != current_theme:
            self.main_window.settings_manager.set_setting("theme", new_theme)
            self.theme_manager.apply_theme(new_theme)
            settings_changed = True

        if language_settings_changed:
            translation_manager.set_language(translation_manager._determine_effective_locale())
            QMessageBox.information(self.main_window, 
                                    translation_manager.translate("ApplicationLogicHandler", "Language Change"),
                                    translation_manager.translate("ApplicationLogicHandler", "Language settings have been updated. Please restart the application for changes to take full effect."))
            
        if settings_changed and not language_settings_changed:
            self.main_window.folder_browser.refresh_all_views()

    def apply_shortcuts_settings(self, new_shortcuts):
        self.main_window.shortcuts_manager.save_shortcuts(new_shortcuts)

    def set_focus_on_path_edit(self):
        active_panel_widget = self.main_window.folder_browser.active_panel_widget
        if active_panel_widget:
            active_panel_widget.path_edit.setFocus()
