import logging
import os
from PyQt6.QtWidgets import QInputDialog, QStyle, QDialog, QMessageBox
from PyQt6.QtCore import QCoreApplication
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
        self._create_help_menu() # Add help menu

    def show_about_dialog(self):
        """Opens the about dialog."""
        from utils.about_dialog import AboutDialog # Import locally to avoid circular dependencies if AboutDialog imports MenuPanel
        dialog = AboutDialog(self.main_window)
        dialog.exec()

    def _create_help_menu(self):
        help_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Help"))
        about_action = QAction(QCoreApplication.translate("MenuPanel", "About"), self.main_window)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def _create_view_menu(self):
        view_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "View"))
        flat_view_action = QAction(QCoreApplication.translate("MenuPanel", "Flat View"), self.main_window)
        flat_view_action.triggered.connect(lambda: self.main_window.folder_browser.set_view_mode("flat"))
        view_menu.addAction(flat_view_action)
        tree_view_action = QAction(QCoreApplication.translate("MenuPanel", "Tree View"), self.main_window)
        tree_view_action.triggered.connect(lambda: self.main_window.folder_browser.set_view_mode("tree"))
        view_menu.addAction(tree_view_action)

    def _create_settings_menu(self):
        settings_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Settings"))
        configure_shortcuts_action = QAction(QCoreApplication.translate("MenuPanel", "Configure Shortcuts"), self.main_window)
        configure_shortcuts_action.triggered.connect(self.open_shortcuts_dialog)
        settings_menu.addAction(configure_shortcuts_action)
        general_settings_action = QAction(QCoreApplication.translate("MenuPanel", "General Settings"), self.main_window)
        general_settings_action.triggered.connect(self.open_general_settings_dialog)
        settings_menu.addAction(general_settings_action)

    def open_general_settings_dialog(self):
        current_view_mode = self.main_window.settings_manager.get_setting("view_mode")
        current_show_dot_files = self.main_window.settings_manager.get_setting("showDotFiles")
        dialog = SettingsDialog(self.main_window, current_view_mode, current_show_dot_files)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_view_mode = dialog.get_selected_view_mode()
            new_show_dot_files = dialog.get_selected_show_dot_files()
            logging.debug(f"Current show_dot_files: {current_show_dot_files}, New show_dot_files: {new_show_dot_files}")

            # Apply view mode setting
            if new_view_mode != current_view_mode:
                self.main_window.settings_manager.set_setting("view_mode", new_view_mode)
                self.main_window.folder_browser.set_view_mode(new_view_mode)
                self.main_window.status_bar.showMessage(QCoreApplication.translate("MenuPanel", f"View mode changed to: {new_view_mode}."))

            # Apply show dot files setting
            if new_show_dot_files != current_show_dot_files:
                self.main_window.settings_manager.set_setting("showDotFiles", new_show_dot_files)
                self.main_window.folder_browser.set_show_dot_files(new_show_dot_files) # <--- ADDED THIS CALL
                self.main_window.status_bar.showMessage(QCoreApplication.translate("MenuPanel", f"Show dot files changed to: {new_show_dot_files}."))

    def open_shortcuts_dialog(self):
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            self.main_window.shortcuts_manager.save_shortcuts(new_shortcuts)

    def _create_file_menu(self):
        self.file_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "File"))

        compare_action = QAction(QCoreApplication.translate("MenuPanel", "Compare"), self.main_window)
        compare_action.triggered.connect(self.main_window._compare_selected_items)
        self.file_menu.addAction(compare_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Compare"), compare_action)

        properties_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), QCoreApplication.translate("MenuPanel", "Properties"), self.main_window)
        properties_action.triggered.connect(self.show_properties_dialog)
        self.file_menu.addAction(properties_action)
        self.toolbar.addAction(properties_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Properties"), properties_action)

        self.file_menu.addSeparator()

        exit_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), QCoreApplication.translate("MenuPanel", "Exit"), self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        self.file_menu.addAction(exit_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Exit"), exit_action)

    def _create_archive_menu(self):
        archive_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Archive"))
        create_archive_action = QAction(QCoreApplication.translate("MenuPanel", "Create Archive"), self.main_window)
        create_archive_action.triggered.connect(self.create_archive)
        archive_menu.addAction(create_archive_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Create Archive"), create_archive_action)
        extract_archive_action = QAction(QCoreApplication.translate("MenuPanel", "Extract Archive"), self.main_window)
        extract_archive_action.triggered.connect(self.extract_archive)
        archive_menu.addAction(extract_archive_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Extract Archive"), extract_archive_action)

    def create_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            logging.warning(QCoreApplication.translate("MenuPanel", "Attempted to create archive without selecting a file/folder."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Archiving Error"), QCoreApplication.translate("MenuPanel", "No file/folder selected for archiving."))
            return

        archive_name, ok = QInputDialog.getText(self.main_window, QCoreApplication.translate("MenuPanel", "Create Archive"), QCoreApplication.translate("MenuPanel", "Archive name (without extension):"))
        if ok and archive_name:
            archive_path = os.path.join(os.path.dirname(selected_path), archive_name + ".zip")
            self.main_window.archive_manager.create_zip_archive(selected_path, archive_path)
            self.main_window.folder_browser.refresh_all_views()

    def extract_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path or not selected_path.endswith(('.zip', '.tar', '.gz', '.bz2', '.xz', '.rar')):
            logging.warning(QCoreApplication.translate("MenuPanel", f"Attempted to extract invalid archive type or no archive selected: {selected_path}"))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Extraction Error"), QCoreApplication.translate("MenuPanel", "No archive file selected for extraction or unsupported format."))
            return

        extract_path, ok = QInputDialog.getText(self.main_window, QCoreApplication.translate("MenuPanel", "Extract Archive"), QCoreApplication.translate("MenuPanel", "Destination path:"), text=os.path.dirname(selected_path))
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
                logging.warning(QCoreApplication.translate("MenuPanel", f"Unrar not installed error: {e}"))
                QMessageBox.warning(self.main_window, QCoreApplication.translate("MenuPanel", "Error"), str(e))
            except Exception as e:
                logging.exception(QCoreApplication.translate("MenuPanel", f"Error during archive extraction for {selected_path}: {e}"))
                show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Extraction Error"), QCoreApplication.translate("MenuPanel", str(e)))

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Operations"))
        self.toolbar.addSeparator()
        go_up_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), QCoreApplication.translate("MenuPanel", "Go Up"), self.main_window)
        go_up_action.triggered.connect(self.main_window.folder_browser.go_up_directory)
        operations_menu.addAction(go_up_action)
        self.toolbar.addAction(go_up_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Go Up"), go_up_action)
        refresh_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), QCoreApplication.translate("MenuPanel", "Refresh"), self.main_window)
        refresh_action.triggered.connect(self.main_window.folder_browser.refresh_all_views)
        operations_menu.addAction(refresh_action)
        self.toolbar.addAction(refresh_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Refresh"), refresh_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()
        create_file_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), QCoreApplication.translate("MenuPanel", "New File"), self.main_window)
        create_file_action.triggered.connect(self.create_new_file)
        operations_menu.addAction(create_file_action)
        self.toolbar.addAction(create_file_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "New File"), create_file_action)
        create_directory_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon), QCoreApplication.translate("MenuPanel", "New Folder"), self.main_window)
        create_directory_action.triggered.connect(self.create_new_directory)
        operations_menu.addAction(create_directory_action)
        self.toolbar.addAction(create_directory_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "New Folder"), create_directory_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()
        search_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), QCoreApplication.translate("MenuPanel", "Search"), self.main_window)
        search_action.triggered.connect(self.main_window.search_input.setFocus)
        operations_menu.addAction(search_action)
        self.toolbar.addAction(search_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Search"), search_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()
        copy_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), QCoreApplication.translate("MenuPanel", "Copy"), self.main_window)
        copy_action.triggered.connect(self.copy_selected_item)
        operations_menu.addAction(copy_action)
        self.toolbar.addAction(copy_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Copy"), copy_action)
        paste_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), QCoreApplication.translate("MenuPanel", "Paste"), self.main_window)
        operations_menu.addAction(paste_action)
        self.toolbar.addAction(paste_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Paste"), paste_action)
        move_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), QCoreApplication.translate("MenuPanel", "Move"), self.main_window)
        move_action.triggered.connect(self.move_selected_item)
        operations_menu.addAction(move_action)
        self.toolbar.addAction(move_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Move"), move_action)
        rename_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton), QCoreApplication.translate("MenuPanel", "Rename"), self.main_window)
        rename_action.triggered.connect(self.rename_selected_item)
        operations_menu.addAction(rename_action)
        self.toolbar.addAction(rename_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Rename"), rename_action)
        delete_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), QCoreApplication.translate("MenuPanel", "Delete"), self.main_window)
        delete_action.triggered.connect(self.delete_selected_item)
        operations_menu.addAction(delete_action)
        self.toolbar.addAction(delete_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Delete"), delete_action)
        compare_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent), QCoreApplication.translate("MenuPanel", "Compare"), self.main_window)
        compare_action.triggered.connect(self.main_window._compare_selected_items)
        self.toolbar.addAction(compare_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Compare"), compare_action)
        synchronize_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), QCoreApplication.translate("MenuPanel", "Synchronize"), self.main_window)
        synchronize_action.triggered.connect(self.synchronize_directories)
        operations_menu.addAction(synchronize_action)
        self.toolbar.addAction(synchronize_action)
        self.main_window.shortcuts_manager.register_action(QCoreApplication.translate("MenuPanel", "Synchronize"), synchronize_action)

    def show_properties_dialog(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Error"), QCoreApplication.translate("MenuPanel", "No file or folder selected."))
            return

        properties = get_file_properties(selected_path)
        if properties:
            dialog = PropertiesDialog(properties, self.main_window)
            dialog.exec()
        else:
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Error"), QCoreApplication.translate("MenuPanel", f"Could not retrieve properties for: {selected_path}"))

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
                file_name, ok = QInputDialog.getText(self.main_window, QCoreApplication.translate("MenuPanel", "New File"), QCoreApplication.translate("MenuPanel", "File name:"))
                if ok and file_name:
                    self.file_manager.create_file(current_dir, file_name)
                    self.main_window.folder_browser.refresh_all_views()
            else:
                logging.warning(QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel when creating new file."))
                show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "File Creation Error"), QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel."))
        else:
            logging.warning(QCoreApplication.translate("MenuPanel", "No active panel when attempting to create new file."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "File Creation Error"), QCoreApplication.translate("MenuPanel", "No active panel."))

    def create_new_directory(self):
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                directory_name, ok = QInputDialog.getText(self.main_window, QCoreApplication.translate("MenuPanel", "New Folder"), QCoreApplication.translate("MenuPanel", "Folder name:"))
                if ok and directory_name:
                    self.file_manager.create_directory(current_dir, directory_name)
                    self.main_window.folder_browser.refresh_all_views()
            else:
                logging.warning(QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel when creating new directory."))
                show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Folder Creation Error"), QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel."))
        else:
            logging.warning(QCoreApplication.translate("MenuPanel", "No active panel when attempting to create new directory."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Folder Creation Error"), QCoreApplication.translate("MenuPanel", "No active panel."))

    def copy_selected_item(self):
        """Opens the copy dialog for the selected item or copies multiple items directly."""
        source_paths = self.main_window.folder_browser.get_selected_paths()
        if not source_paths:
            logging.warning(QCoreApplication.translate("MenuPanel", "Attempted to copy item without selecting a file/folder."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Copy Error"), QCoreApplication.translate("MenuPanel", "No file/folder selected for copying."))
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
        logging.info(QCoreApplication.translate("MenuPanel", "--- Starting move_selected_item ---"))
        source_path = self.main_window.folder_browser.current_selected_path
        logging.info(f"Source path: {source_path}")
        if not source_path:
            logging.warning(QCoreApplication.translate("MenuPanel", "Attempted to move item without selecting a file/folder."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Move Error"), QCoreApplication.translate("MenuPanel", "No file/folder selected for moving."))
            return

        active_panel = self.main_window.folder_browser.active_panel
        inactive_panel = self.main_window.folder_browser.right_panel if active_panel == self.main_window.folder_browser.left_panel else self.main_window.folder_browser.left_panel
        destination_path = self.main_window.folder_browser.current_paths[inactive_panel]
        logging.info(f"Destination path: {destination_path}")

        dialog = MoveDialog(self.main_window, source_path, destination_path)
        logging.info(QCoreApplication.translate("MenuPanel", "MoveDialog created."))
        dialog_result = dialog.exec()
        logging.info(QCoreApplication.translate("MenuPanel", f"dialog.exec() returned: {dialog_result}"))

        if dialog_result == QDialog.DialogCode.Accepted:
            logging.info(QCoreApplication.translate("MenuPanel", "Move dialog accepted."))
            options = dialog.get_options()
            logging.info(QCoreApplication.translate("MenuPanel", f"Move options: {options}"))
            logging.info(QCoreApplication.translate("MenuPanel", f"Calling file_manager.move_item_with_options with source: {source_path}, destination: {destination_path}, options: {options}"))
            self.file_manager.move_item_with_options(source_path, destination_path, options)
            logging.info(QCoreApplication.translate("MenuPanel", "move_item_with_options call completed."))
        else:
            logging.info(QCoreApplication.translate("MenuPanel", "Move dialog not accepted (cancelled or failed)."))

    def cut_selected_item(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.cut_item(selected_path)
        else:
            logging.warning(QCoreApplication.translate("MenuPanel", "No file/folder selected for cut operation."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Cut Error"), QCoreApplication.translate("MenuPanel", "No file/folder selected for cutting."))

    def paste_item_to_current_dir(self):
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                self.file_manager.paste_item(current_dir)
            else:
                logging.warning(QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel when pasting item."))
                show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Paste Error"), QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel."))
        else:
            logging.warning(QCoreApplication.translate("MenuPanel", "No active panel when attempting to paste item."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Paste Error"), QCoreApplication.translate("MenuPanel", "No active panel."))

    def delete_selected_item(self):
        logging.debug(QCoreApplication.translate("MenuPanel", "MenuPanel: delete_selected_item called"))
        selected_paths = self.main_window.folder_browser.get_selected_paths()

        if not selected_paths:
            logging.warning(QCoreApplication.translate("MenuPanel", "No file/folder selected for delete operation."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Deletion Error"), QCoreApplication.translate("MenuPanel", "No file/folder selected for deletion."))
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
            new_name, ok = QInputDialog.getText(self.main_window, QCoreApplication.translate("MenuPanel", "Rename"), QCoreApplication.translate("MenuPanel", "New name:"), text=old_name)
            if ok and new_name:
                self.file_manager.rename_item(selected_path, new_name)
            elif not new_name:
                logging.warning(QCoreApplication.translate("MenuPanel", "Attempted to rename item with an empty new name."))
                show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Rename Error"), QCoreApplication.translate("MenuPanel", "New name cannot be empty."))
        else:
            logging.warning(QCoreApplication.translate("MenuPanel", "No file/folder selected for rename operation."))
            show_error_message(self.main_window, QCoreApplication.translate("MenuPanel", "Rename Error"), QCoreApplication.translate("MenuPanel", "No file/folder selected for renaming."))
