import logging
import os
from PyQt6.QtWidgets import QInputDialog, QStyle, QDialog, QMessageBox
from file_operations.archive_manager import UnrarNotInstalledError
from PyQt6.QtGui import QIcon, QKeySequence, QAction
from utils.copy_dialog import CopyDialog
from utils.move_dialog import MoveDialog
from utils.delete_dialog import DeleteDialog
from utils.sync_dialog import SyncDialog
from utils.shortcuts_dialog import ShortcutsDialog
from utils.settings_dialog import SettingsDialog
from utils.dialogs import show_error_message
from utils.properties_dialog import PropertiesDialog
from file_operations.properties_manager import get_file_properties


class MenuPanel:
    def __init__(self, main_window):
        self.main_window = main_window
        self.menu_bar = main_window.menuBar()
        self.toolbar = main_window.toolbar
        self.file_manager = main_window.file_manager

        self._create_file_menu()
        self._create_operations_menu()
        self._create_archive_menu()
        self._create_view_menu()
        self._create_settings_menu()

    def _create_view_menu(self):
        view_menu = self.menu_bar.addMenu("View")
        flat_view_action = QAction("Flat View", self.main_window)
        flat_view_action.triggered.connect(lambda: self.main_window.folder_browser.set_view_mode("flat"))
        view_menu.addAction(flat_view_action)
        tree_view_action = QAction("Tree View", self.main_window)
        tree_view_action.triggered.connect(lambda: self.main_window.folder_browser.set_view_mode("tree"))
        view_menu.addAction(tree_view_action)

    def _create_settings_menu(self):
        settings_menu = self.menu_bar.addMenu("Settings")
        configure_shortcuts_action = QAction("Configure Shortcuts", self.main_window)
        configure_shortcuts_action.triggered.connect(self.open_shortcuts_dialog)
        settings_menu.addAction(configure_shortcuts_action)
        general_settings_action = QAction("General Settings", self.main_window)
        general_settings_action.triggered.connect(self.open_general_settings_dialog)
        settings_menu.addAction(general_settings_action)

    def open_general_settings_dialog(self):
        current_view_mode = self.main_window.settings_manager.get_setting("view_mode")
        dialog = SettingsDialog(self.main_window, current_view_mode)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_view_mode = dialog.get_selected_view_mode()
            if new_view_mode != current_view_mode:
                self.main_window.settings_manager.set_setting("view_mode", new_view_mode)
                self.main_window.folder_browser.set_view_mode(new_view_mode)
                self.main_window.status_bar.showMessage(f"View mode changed to: {new_view_mode}.")

    def open_shortcuts_dialog(self):
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            self.main_window.shortcuts_manager.save_shortcuts(new_shortcuts)

    def _create_file_menu(self):
        self.file_menu = self.menu_bar.addMenu("File")

        compare_action = QAction("Compare", self.main_window)
        compare_action.triggered.connect(self.main_window._compare_selected_items)
        self.file_menu.addAction(compare_action)
        self.main_window.shortcuts_manager.register_action("Compare", compare_action)

        properties_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), "Properties", self.main_window)
        properties_action.triggered.connect(self.show_properties_dialog)
        self.file_menu.addAction(properties_action)
        self.toolbar.addAction(properties_action)
        self.main_window.shortcuts_manager.register_action("Properties", properties_action)

        self.file_menu.addSeparator()

        exit_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "Exit", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        self.file_menu.addAction(exit_action)
        self.main_window.shortcuts_manager.register_action("Exit", exit_action)

    def _create_archive_menu(self):
        archive_menu = self.menu_bar.addMenu("Archive")
        create_archive_action = QAction("Create Archive", self.main_window)
        create_archive_action.triggered.connect(self.create_archive)
        archive_menu.addAction(create_archive_action)
        self.main_window.shortcuts_manager.register_action("Create Archive", create_archive_action)
        extract_archive_action = QAction("Extract Archive", self.main_window)
        extract_archive_action.triggered.connect(self.extract_archive)
        archive_menu.addAction(extract_archive_action)
        self.main_window.shortcuts_manager.register_action("Extract Archive", extract_archive_action)

    def create_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            logging.warning("Attempted to create archive without selecting a file/folder.")
            show_error_message(self.main_window, "Archiving Error", "No file/folder selected for archiving.")
            return

        archive_name, ok = QInputDialog.getText(self.main_window, "Create Archive", "Archive name (without extension):")
        if ok and archive_name:
            archive_path = os.path.join(os.path.dirname(selected_path), archive_name + ".zip")
            self.main_window.archive_manager.create_zip_archive(selected_path, archive_path)
            self.main_window.folder_browser.refresh_all_views()

    def extract_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path or not selected_path.endswith(('.zip', '.tar', '.gz', '.bz2', '.xz', '.rar')):
            logging.warning(f"Attempted to extract invalid archive type or no archive selected: {selected_path}")
            show_error_message(self.main_window, "Extraction Error", "No archive file selected for extraction or unsupported format.")
            return

        extract_path, ok = QInputDialog.getText(self.main_window, "Extract Archive", "Destination path:", text=os.path.dirname(selected_path))
        if ok and extract_path:
            if not os.path.exists(extract_path):
                os.makedirs(extract_path)
            try:
                if selected_path.endswith('.zip'):
                    self.main_window.archive_manager.extract_zip_archive(selected_path, extract_path)
                elif selected_path.endswith('.rar'):
                    self.main_window.archive_manager.extract_rar_archive(selected_path, extract_path)
                else:
                    self.main_window.archive_manager.extract_tar_archive(selected_path, extract_path)
                self.main_window.folder_browser.refresh_all_views()
            except UnrarNotInstalledError as e:
                logging.warning(f"Unrar not installed error: {e}")
                QMessageBox.warning(self.main_window, "Error", str(e))
            except Exception as e:
                logging.exception(f"Error during archive extraction for {selected_path}: {e}")
                show_error_message(self.main_window, "Extraction Error", str(e))

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu("Operations")
        self.toolbar.addSeparator()
        go_up_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Go Up", self.main_window)
        go_up_action.triggered.connect(self.main_window.folder_browser.go_up_directory)
        operations_menu.addAction(go_up_action)
        self.toolbar.addAction(go_up_action)
        self.main_window.shortcuts_manager.register_action("Go Up", go_up_action)
        refresh_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Refresh", self.main_window)
        refresh_action.triggered.connect(self.main_window.folder_browser.refresh_all_views)
        operations_menu.addAction(refresh_action)
        self.toolbar.addAction(refresh_action)
        self.main_window.shortcuts_manager.register_action("Refresh", refresh_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()
        create_file_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "New File", self.main_window)
        create_file_action.triggered.connect(self.create_new_file)
        operations_menu.addAction(create_file_action)
        self.toolbar.addAction(create_file_action)
        self.main_window.shortcuts_manager.register_action("New File", create_file_action)
        create_directory_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon), "New Folder", self.main_window)
        create_directory_action.triggered.connect(self.create_new_directory)
        operations_menu.addAction(create_directory_action)
        self.toolbar.addAction(create_directory_action)
        self.main_window.shortcuts_manager.register_action("New Folder", create_directory_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()
        search_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Search", self.main_window)
        search_action.triggered.connect(self.main_window.search_input.setFocus)
        operations_menu.addAction(search_action)
        self.toolbar.addAction(search_action)
        self.main_window.shortcuts_manager.register_action("Search", search_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()
        copy_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), "Copy", self.main_window)
        copy_action.triggered.connect(self.copy_selected_item)
        operations_menu.addAction(copy_action)
        self.toolbar.addAction(copy_action)
        self.main_window.shortcuts_manager.register_action("Copy", copy_action)
        paste_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Paste", self.main_window)
        operations_menu.addAction(paste_action)
        self.toolbar.addAction(paste_action)
        self.main_window.shortcuts_manager.register_action("Paste", paste_action)
        move_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), "Move", self.main_window)
        move_action.triggered.connect(self.move_selected_item)
        operations_menu.addAction(move_action)
        self.toolbar.addAction(move_action)
        self.main_window.shortcuts_manager.register_action("Move", move_action)
        rename_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton), "Rename", self.main_window)
        rename_action.triggered.connect(self.rename_selected_item)
        operations_menu.addAction(rename_action)
        self.toolbar.addAction(rename_action)
        self.main_window.shortcuts_manager.register_action("Rename", rename_action)
        delete_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Delete", self.main_window)
        delete_action.triggered.connect(self.delete_selected_item)
        operations_menu.addAction(delete_action)
        self.toolbar.addAction(delete_action)
        self.main_window.shortcuts_manager.register_action("Delete", delete_action)
        compare_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent), "Compare", self.main_window)
        compare_action.triggered.connect(self.main_window._compare_selected_items)
        self.toolbar.addAction(compare_action)
        self.main_window.shortcuts_manager.register_action("Compare", compare_action)
        synchronize_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), "Synchronize", self.main_window)
        synchronize_action.triggered.connect(self.synchronize_directories)
        operations_menu.addAction(synchronize_action)
        self.toolbar.addAction(synchronize_action)
        self.main_window.shortcuts_manager.register_action("Synchronize", synchronize_action)

    def show_properties_dialog(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            show_error_message(self.main_window, "Error", "No file or folder selected.")
            return

        properties = get_file_properties(selected_path)
        if properties:
            dialog = PropertiesDialog(properties, self.main_window)
            dialog.exec()
        else:
            show_error_message(self.main_window, "Error", f"Could not retrieve properties for: {selected_path}")

    def synchronize_directories(self):
        left_path = self.main_window.folder_browser.current_paths[self.main_window.folder_browser.left_panel]
        right_path = self.main_window.folder_browser.current_paths[self.main_window.folder_browser.right_panel]
        dialog = SyncDialog(self.main_window, left_path, right_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.main_window.directory_synchronizer.synchronize(left_path, right_path, options)

    def create_new_file(self):
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                file_name, ok = QInputDialog.getText(self.main_window, "New File", "File name:")
                if ok and file_name:
                    self.file_manager.create_file(current_dir, file_name)
                    self.main_window.folder_browser.refresh_all_views()
            else:
                logging.warning("Could not determine current directory for active panel when creating new file.")
                show_error_message(self.main_window, "File Creation Error", "Could not determine current directory for active panel.")
        else:
            logging.warning("No active panel when attempting to create new file.")
            show_error_message(self.main_window, "File Creation Error", "No active panel.")

    def create_new_directory(self):
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                directory_name, ok = QInputDialog.getText(self.main_window, "New Folder", "Folder name:")
                if ok and directory_name:
                    self.file_manager.create_directory(current_dir, directory_name)
                    self.main_window.folder_browser.refresh_all_views()
            else:
                logging.warning("Could not determine current directory for active panel when creating new directory.")
                show_error_message(self.main_window, "Folder Creation Error", "Could not determine current directory for active panel.")
        else:
            logging.warning("No active panel when attempting to create new directory.")
            show_error_message(self.main_window, "Folder Creation Error", "No active panel.")

    def copy_selected_item(self):
        """Opens the copy dialog for the selected item or copies multiple items directly."""
        source_paths = self.main_window.folder_browser.get_selected_paths()
        if not source_paths:
            logging.warning("Attempted to copy item without selecting a file/folder.")
            show_error_message(self.main_window, "Copy Error", "No file/folder selected for copying.")
            return

        active_panel = self.main_window.folder_browser.active_panel
        inactive_panel = self.main_window.folder_browser.right_panel if active_panel == self.main_window.folder_browser.left_panel else self.main_window.folder_browser.left_panel
        destination_path = self.main_window.folder_browser.current_paths[inactive_panel]

        if len(source_paths) == 1:
            # Single item: show dialog
            dialog = CopyDialog(self.main_window, source_paths[0], destination_path)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                options = dialog.get_options()
                self.file_manager.copy_item_with_options(source_paths[0], destination_path, options)
        else:
            # Multiple items: copy directly with default options
            # Default options could be defined somewhere or hardcoded here
            default_options = {"overwrite": False, "preserve_timestamp": True}
            for source_path in source_paths:
                self.file_manager.copy_item_with_options(source_path, destination_path, default_options)
            self.main_window.folder_browser.refresh_all_views() # Refresh after all copies are done

    def move_selected_item(self):
        """Opens the move dialog for the selected item."""
        logging.info("--- Starting move_selected_item ---")
        source_path = self.main_window.folder_browser.current_selected_path
        logging.info(f"Source path: {source_path}")
        if not source_path:
            logging.warning("Attempted to move item without selecting a file/folder.")
            show_error_message(self.main_window, "Move Error", "No file/folder selected for moving.")
            return

        active_panel = self.main_window.folder_browser.active_panel
        inactive_panel = self.main_window.folder_browser.right_panel if active_panel == self.main_window.folder_browser.left_panel else self.main_window.folder_browser.left_panel
        destination_path = self.main_window.folder_browser.current_paths[inactive_panel]
        logging.info(f"Destination path: {destination_path}")

        dialog = MoveDialog(self.main_window, source_path, destination_path)
        logging.info("MoveDialog created.")
        dialog_result = dialog.exec()
        logging.info(f"dialog.exec() returned: {dialog_result}")

        if dialog_result == QDialog.DialogCode.Accepted:
            logging.info("Move dialog accepted.")
            options = dialog.get_options()
            logging.info(f"Move options: {options}")
            logging.info(f"Calling file_manager.move_item_with_options with source: {source_path}, destination: {destination_path}, options: {options}")
            self.file_manager.move_item_with_options(source_path, destination_path, options)
            logging.info("move_item_with_options call completed.")
        else:
            logging.info("Move dialog not accepted (cancelled or failed).")

    def cut_selected_item(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.cut_item(selected_path)
        else:
            logging.warning("No file/folder selected for cut operation.")
            show_error_message(self.main_window, "Cut Error", "No file/folder selected for cutting.")

    def paste_item_to_current_dir(self):
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                self.file_manager.paste_item(current_dir)
            else:
                logging.warning("Could not determine current directory for active panel when pasting item.")
                show_error_message(self.main_window, "Paste Error", "Could not determine current directory for active panel.")
        else:
            logging.warning("No active panel when attempting to paste item.")
            show_error_message(self.main_window, "Paste Error", "No active panel.")

    def delete_selected_item(self):
        logging.debug("MenuPanel: delete_selected_item called")
        selected_paths = self.main_window.folder_browser.get_selected_paths()

        if not selected_paths:
            logging.warning("No file/folder selected for delete operation.")
            show_error_message(self.main_window, "Deletion Error", "No file/folder selected for deletion.")
            return

        dialog = DeleteDialog(self.main_window, selected_paths)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for path in selected_paths:
                self.file_manager.delete_item_with_confirmation(path, show_confirmation=False)
            self.main_window.folder_browser.refresh_all_views()

    def rename_selected_item(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            old_name = os.path.basename(selected_path)
            new_name, ok = QInputDialog.getText(self.main_window, "Rename", "New name:", text=old_name)
            if ok and new_name:
                self.file_manager.rename_item(selected_path, new_name)
            elif not new_name:
                logging.warning("Attempted to rename item with an empty new name.")
                show_error_message(self.main_window, "Rename Error", "New name cannot be empty.")
        else:
            logging.warning("No file/folder selected for rename operation.")
            show_error_message(self.main_window, "Rename Error", "No file/folder selected for renaming.")
