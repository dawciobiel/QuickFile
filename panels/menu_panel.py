import logging
import os
from PyQt6.QtWidgets import QInputDialog, QStyle, QDialog, QMessageBox
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal
from file_operations.archive_manager import UnrarNotInstalledError
from PyQt6.QtGui import QAction
from utils.copy_dialog import CopyDialog
from utils.move_dialog import MoveDialog
from utils.delete_dialog import DeleteDialog
from utils.sync_dialog import SyncDialog
from utils.shortcuts_dialog import ShortcutsDialog
from utils.settings_dialog import SettingsDialog
from utils.dialogs import show_error_message
from utils.properties_dialog import PropertiesDialog
from file_operations.properties_manager import get_file_properties


class MenuPanel(QObject):
    go_up_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    view_mode_changed = pyqtSignal(str)

    # Constants for repeated strings
    ACTION_COMPARE = QCoreApplication.translate("MenuPanel", "Compare")
    ACTION_PROPERTIES = QCoreApplication.translate("MenuPanel", "Properties")
    ACTION_EXIT = QCoreApplication.translate("MenuPanel", "Exit")
    ACTION_CREATE_ARCHIVE = QCoreApplication.translate("MenuPanel", "Create Archive")
    ACTION_EXTRACT_ARCHIVE = QCoreApplication.translate("MenuPanel", "Extract Archive")
    ACTION_GO_UP = QCoreApplication.translate("MenuPanel", "Go Up")
    ACTION_REFRESH = QCoreApplication.translate("MenuPanel", "Refresh")
    ACTION_NEW_FILE = QCoreApplication.translate("MenuPanel", "New File")
    ACTION_NEW_FOLDER = QCoreApplication.translate("MenuPanel", "New Folder")
    ACTION_SEARCH = QCoreApplication.translate("MenuPanel", "Search")
    ACTION_COPY = QCoreApplication.translate("MenuPanel", "Copy")
    ACTION_PASTE = QCoreApplication.translate("MenuPanel", "Paste")
    ACTION_MOVE = QCoreApplication.translate("MenuPanel", "Move")
    ACTION_RENAME = QCoreApplication.translate("MenuPanel", "Rename")
    ACTION_DELETE = QCoreApplication.translate("MenuPanel", "Delete")
    ACTION_SYNCHRONIZE = QCoreApplication.translate("MenuPanel", "Synchronize")

    ERROR_NO_ACTIVE_PANEL = QCoreApplication.translate("MenuPanel", "No active panel.")
    ERROR_NO_CURRENT_DIR = QCoreApplication.translate("MenuPanel", "Could not determine current directory for active panel.")
    ERROR_FILE_CREATION = QCoreApplication.translate("MenuPanel", "File Creation Error")
    ERROR_FOLDER_CREATION = QCoreApplication.translate("MenuPanel", "Folder Creation Error")

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.menu_bar = main_window.menuBar()
        self.toolbar = main_window.toolbar

        self._create_menus()

    def _create_menus(self):
        self._create_file_menu()
        self._create_operations_menu()
        self._create_archive_menu()
        self._create_view_menu()
        self._create_settings_menu()
        self._create_help_menu()

    def _create_action(self, text, icon=None, slot=None, shortcut_key=None):
        """Helper to create and register a QAction."""
        action = QAction(text, self.main_window)
        if icon:
            action.setIcon(self.main_window.style().standardIcon(icon))
        if slot:
            action.triggered.connect(slot)
        if shortcut_key:
            self.main_window.shortcuts_manager.register_action(shortcut_key, action)
        return action

    def show_about_dialog(self):
        from utils.about_dialog import AboutDialog
        dialog = AboutDialog(self.main_window)
        dialog.exec()

    def _create_help_menu(self):
        help_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Help"))
        about_action = self._create_action(QCoreApplication.translate("MenuPanel", "About"), slot=self.show_about_dialog)
        help_menu.addAction(about_action)

    def _create_view_menu(self):
        view_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "View"))
        flat_view_action = self._create_action(QCoreApplication.translate("MenuPanel", "Flat View"), slot=lambda: self.view_mode_changed.emit("flat"))
        tree_view_action = self._create_action(QCoreApplication.translate("MenuPanel", "Tree View"), slot=lambda: self.view_mode_changed.emit("tree"))
        view_menu.addAction(flat_view_action)
        view_menu.addAction(tree_view_action)

    def _create_settings_menu(self):
        settings_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Settings"))
        shortcuts_action = self._create_action(QCoreApplication.translate("MenuPanel", "Configure Shortcuts"), slot=self.open_shortcuts_dialog)
        settings_action = self._create_action(QCoreApplication.translate("MenuPanel", "General Settings"), slot=self.open_general_settings_dialog)
        settings_menu.addAction(shortcuts_action)
        settings_menu.addAction(settings_action)

    def open_general_settings_dialog(self):
        current_show_dot_files = self.main_window.settings_manager.get_setting("showDotFiles")
        dialog = SettingsDialog(self.main_window, current_show_dot_files)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_show_dot_files = dialog.get_selected_show_dot_files()
            self.main_window.application_logic_handler.apply_general_settings(None, new_show_dot_files) # Pass None for view_mode

    def open_shortcuts_dialog(self):
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            self.main_window.application_logic_handler.apply_shortcuts_settings(new_shortcuts)

    def _create_file_menu(self):
        file_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "File"))
        
        compare_action = self._create_action(self.ACTION_COMPARE, slot=self.main_window.application_logic_handler.compare_selected_items, shortcut_key=self.ACTION_COMPARE)
        properties_action = self._create_action(self.ACTION_PROPERTIES, QStyle.StandardPixmap.SP_FileDialogInfoView, self.main_window.application_logic_handler.show_properties_dialog, self.ACTION_PROPERTIES)
        exit_action = self._create_action(self.ACTION_EXIT, QStyle.StandardPixmap.SP_DialogCancelButton, self.main_window.close, self.ACTION_EXIT)

        file_menu.addAction(compare_action)
        file_menu.addAction(properties_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        self.toolbar.addAction(properties_action)

    def _create_archive_menu(self):
        archive_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Archive"))
        create_action = self._create_action(self.ACTION_CREATE_ARCHIVE, slot=self.main_window.application_logic_handler.create_archive, shortcut_key=self.ACTION_CREATE_ARCHIVE)
        extract_action = self._create_action(self.ACTION_EXTRACT_ARCHIVE, slot=self.main_window.application_logic_handler.extract_archive, shortcut_key=self.ACTION_EXTRACT_ARCHIVE)
        archive_menu.addAction(create_action)
        archive_menu.addAction(extract_action)

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu(QCoreApplication.translate("MenuPanel", "Operations"))
        self.toolbar.addSeparator()

        go_up_action = self._create_action(self.ACTION_GO_UP, QStyle.StandardPixmap.SP_ArrowUp, None, self.ACTION_GO_UP)
        go_up_action.triggered.connect(self.go_up_requested)
        operations_menu.addAction(go_up_action)
        self.toolbar.addAction(go_up_action)

        refresh_action = self._create_action(self.ACTION_REFRESH, QStyle.StandardPixmap.SP_BrowserReload, None, self.ACTION_REFRESH)
        refresh_action.triggered.connect(self.refresh_requested)
        operations_menu.addAction(refresh_action)
        self.toolbar.addAction(refresh_action)

        actions = [
            (self.ACTION_NEW_FILE, QStyle.StandardPixmap.SP_FileIcon, self.main_window.application_logic_handler.create_new_file),
            (self.ACTION_NEW_FOLDER, QStyle.StandardPixmap.SP_DirIcon, self.main_window.application_logic_handler.create_new_directory),
            (self.ACTION_SEARCH, QStyle.StandardPixmap.SP_FileDialogDetailedView, self.main_window.search_input.setFocus),
            (self.ACTION_COPY, QStyle.StandardPixmap.SP_FileLinkIcon, self.main_window.application_logic_handler.copy_selected_item),
            (self.ACTION_PASTE, QStyle.StandardPixmap.SP_FileIcon, self.main_window.application_logic_handler.paste_item_to_current_dir),
            (self.ACTION_MOVE, QStyle.StandardPixmap.SP_DirLinkIcon, self.main_window.application_logic_handler.move_selected_item),
            (self.ACTION_RENAME, QStyle.StandardPixmap.SP_LineEditClearButton, self.main_window.application_logic_handler.rename_selected_item),
            (self.ACTION_DELETE, QStyle.StandardPixmap.SP_TrashIcon, self.main_window.application_logic_handler.delete_selected_item),
            (self.ACTION_COMPARE, QStyle.StandardPixmap.SP_FileDialogToParent, self.main_window.application_logic_handler.compare_selected_items),
            (self.ACTION_SYNCHRONIZE, QStyle.StandardPixmap.SP_DirLinkIcon, self.main_window.application_logic_handler.synchronize_directories),
        ]

        for text, icon, slot in actions:
            action = self._create_action(text, icon, slot, text)
            operations_menu.addAction(action)
            self.toolbar.addAction(action)
            if text in [self.ACTION_REFRESH, self.ACTION_NEW_FOLDER, self.ACTION_SEARCH, self.ACTION_DELETE]:
                operations_menu.addSeparator()
                self.toolbar.addSeparator()
