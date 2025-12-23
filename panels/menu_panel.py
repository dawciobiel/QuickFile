import logging
import os
from PyQt6.QtWidgets import QInputDialog, QStyle, QDialog, QMessageBox, QToolBar
from PyQt6.QtCore import QObject, pyqtSignal
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
from app.translation_manager import translation_manager
from app.shortcuts_manager import ShortcutsManager
from app.application_logic_handler import ApplicationLogicHandler


class MenuPanel(QObject):
    go_up_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    view_mode_changed = pyqtSignal(str)

    KEY_COMPARE = "action.compare"
    KEY_PROPERTIES = "action.properties"
    KEY_EXIT = "action.exit"
    KEY_CREATE_ARCHIVE = "action.create_archive"
    KEY_EXTRACT_ARCHIVE = "action.extract_archive"
    KEY_GO_UP = "action.go_up"
    KEY_REFRESH = "action.refresh"
    KEY_NEW_FILE = "action.new_file"
    KEY_NEW_FOLDER = "action.new_folder"
    KEY_SEARCH = "action.search"
    KEY_COPY = "action.copy"
    KEY_PASTE = "action.paste"
    KEY_MOVE = "action.move"
    KEY_RENAME = "action.rename"
    KEY_DELETE = "action.delete"
    KEY_SYNCHRONIZE = "action.synchronize"
    KEY_ABOUT = "action.about"
    KEY_FLAT_VIEW = "action.flat_view"
    KEY_TREE_VIEW = "action.tree_view"
    KEY_CONFIGURE_SHORTCUTS = "action.configure_shortcuts"
    KEY_GENERAL_SETTINGS = "action.general_settings"
    KEY_NEW_TAB = "action.new_tab"
    KEY_CLOSE_TAB = "action.close_tab"
    KEY_ADD_FAVORITE = "action.add_favorite"
    KEY_SHOW_FAVORITES = "action.show_favorites"

    def __init__(self, main_window, toolbar: QToolBar, application_logic_handler: ApplicationLogicHandler, shortcuts_manager: ShortcutsManager):
        super().__init__(main_window)
        self.main_window = main_window
        self.menu_bar = main_window.menuBar()
        self.toolbar = toolbar
        self.application_logic_handler = application_logic_handler
        self.shortcuts_manager = shortcuts_manager

    def initialize_menus(self):
        self._create_menus()

    def _create_menus(self):
        self._create_file_menu()
        self._create_operations_menu()
        self._create_favorites_menu()
        self._create_archive_menu()
        self._create_view_menu()
        self._create_settings_menu()
        self._create_help_menu()

    def _create_action(self, visible_text, tooltip_text, icon=None, slot=None, shortcut_key=None, add_to_toolbar=False):
        action = QAction(visible_text, self.main_window)
        if icon:
            action.setIcon(self.main_window.style().standardIcon(icon))
        if slot:
            action.triggered.connect(slot)
        if shortcut_key:
            self.shortcuts_manager.register_action(shortcut_key, action)
        
        action.setToolTip(tooltip_text)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        return action

    def show_about_dialog(self):
        from utils.about_dialog import AboutDialog
        dialog = AboutDialog(self.main_window)
        dialog.exec()

    def _create_help_menu(self):
        help_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "Help"))
        about_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "About"),
            tooltip_text=translation_manager.translate("MenuPanel", "About"),
            slot=self.show_about_dialog,
            shortcut_key=self.KEY_ABOUT
        )
        help_menu.addAction(about_action)

    def _create_view_menu(self):
        view_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "View"))
        flat_view_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Flat View"),
            tooltip_text=translation_manager.translate("MenuPanel", "Flat View"),
            slot=lambda: self.view_mode_changed.emit("flat"),
            shortcut_key=self.KEY_FLAT_VIEW
        )
        tree_view_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Tree View"),
            tooltip_text=translation_manager.translate("MenuPanel", "Tree View"),
            slot=lambda: self.view_mode_changed.emit("tree"),
            shortcut_key=self.KEY_TREE_VIEW
        )
        view_menu.addAction(flat_view_action)
        view_menu.addAction(tree_view_action)

    def _create_settings_menu(self):
        settings_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "Settings"))
        shortcuts_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Configure Shortcuts"),
            tooltip_text=translation_manager.translate("MenuPanel", "Configure Shortcuts"),
            slot=self.application_logic_handler.open_shortcuts_dialog,
            shortcut_key=self.KEY_CONFIGURE_SHORTCUTS
        )
        settings_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "General Settings"),
            tooltip_text=translation_manager.translate("MenuPanel", "General Settings"),
            slot=self.application_logic_handler.open_general_settings_dialog,
            shortcut_key=self.KEY_GENERAL_SETTINGS
        )
        settings_menu.addAction(shortcuts_action)
        settings_menu.addAction(settings_action)

    def _create_file_menu(self):
        file_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "File"))
        
        new_tab_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "New Tab"),
            tooltip_text=translation_manager.translate("MenuPanel", "Open a new tab"),
            slot=self.application_logic_handler.new_tab,
            shortcut_key=self.KEY_NEW_TAB
        )
        close_tab_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Close Tab"),
            tooltip_text=translation_manager.translate("MenuPanel", "Close the current tab"),
            slot=self.application_logic_handler.close_tab,
            shortcut_key=self.KEY_CLOSE_TAB
        )
        compare_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Compare"),
            tooltip_text=translation_manager.translate("MenuPanel", "Compare selected items"),
            slot=self.application_logic_handler.compare_selected_items,
            shortcut_key=self.KEY_COMPARE
        )
        properties_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Properties"),
            tooltip_text=translation_manager.translate("MenuPanel", "Show properties of selected item"),
            icon=QStyle.StandardPixmap.SP_FileDialogInfoView,
            slot=self.application_logic_handler.show_properties_dialog,
            shortcut_key=self.KEY_PROPERTIES,
            add_to_toolbar=True
        )
        exit_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Exit"),
            tooltip_text=translation_manager.translate("MenuPanel", "Exit the application"),
            icon=QStyle.StandardPixmap.SP_DialogCancelButton,
            slot=self.main_window.close,
            shortcut_key=self.KEY_EXIT
        )

        file_menu.addAction(new_tab_action)
        file_menu.addAction(close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(compare_action)
        file_menu.addAction(properties_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def _create_favorites_menu(self):
        favorites_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "Favorites"))
        add_favorite_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Add to favorites"),
            tooltip_text=translation_manager.translate("MenuPanel", "Add current directory to favorites"),
            slot=self.application_logic_handler.add_favorite,
            shortcut_key=self.KEY_ADD_FAVORITE
        )
        show_favorites_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Show favorites"),
            tooltip_text=translation_manager.translate("MenuPanel", "Show favorites list"),
            slot=self.application_logic_handler.open_favorites_dialog,
            shortcut_key=self.KEY_SHOW_FAVORITES
        )
        favorites_menu.addAction(add_favorite_action)
        favorites_menu.addAction(show_favorites_action)

    def _create_archive_menu(self):
        archive_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "Archive"))
        create_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Create Archive"),
            tooltip_text=translation_manager.translate("MenuPanel", "Create an archive from selected item"),
            slot=self.application_logic_handler.create_archive,
            shortcut_key=self.KEY_CREATE_ARCHIVE
        )
        extract_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Extract Archive"),
            tooltip_text=translation_manager.translate("MenuPanel", "Extract selected archive"),
            slot=self.application_logic_handler.extract_archive,
            shortcut_key=self.KEY_EXTRACT_ARCHIVE
        )
        archive_menu.addAction(create_action)
        archive_menu.addAction(extract_action)

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "Operations"))
        self.toolbar.addSeparator()

        go_up_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Go Up"),
            tooltip_text=translation_manager.translate("MenuPanel", "Go to parent directory"),
            icon=QStyle.StandardPixmap.SP_ArrowUp,
            slot=self.go_up_requested,
            shortcut_key=self.KEY_GO_UP,
            add_to_toolbar=True
        )
        operations_menu.addAction(go_up_action)

        refresh_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Refresh"),
            tooltip_text=translation_manager.translate("MenuPanel", "Refresh the current view"),
            icon=QStyle.StandardPixmap.SP_BrowserReload,
            slot=self.refresh_requested,
            shortcut_key=self.KEY_REFRESH,
            add_to_toolbar=True
        )
        operations_menu.addAction(refresh_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        new_file_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "New File"),
            tooltip_text=translation_manager.translate("MenuPanel", "Create a new empty file"),
            icon=QStyle.StandardPixmap.SP_FileIcon,
            slot=lambda: self.application_logic_handler.create_new_file(self.application_logic_handler._get_active_panel_path()),
            shortcut_key=self.KEY_NEW_FILE,
            add_to_toolbar=True
        )
        operations_menu.addAction(new_file_action)

        new_folder_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "New Folder"),
            tooltip_text=translation_manager.translate("MenuPanel", "Create a new directory"),
            icon=QStyle.StandardPixmap.SP_DirIcon,
            slot=lambda: self.application_logic_handler.create_new_directory(self.application_logic_handler._get_active_panel_path()),
            shortcut_key=self.KEY_NEW_FOLDER,
            add_to_toolbar=True
        )
        operations_menu.addAction(new_folder_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        search_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Search"), tooltip_text=translation_manager.translate("MenuPanel", "Search for files and directories"), icon=QStyle.StandardPixmap.SP_FileDialogDetailedView, slot=self.main_window.search_input.setFocus, shortcut_key=self.KEY_SEARCH, add_to_toolbar=True)
        operations_menu.addAction(search_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        copy_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Copy"), tooltip_text=translation_manager.translate("MenuPanel", "Copy selected items"), icon=QStyle.StandardPixmap.SP_FileLinkIcon, slot=self.application_logic_handler.copy_selected_item, shortcut_key=self.KEY_COPY, add_to_toolbar=True)
        operations_menu.addAction(copy_action)

        paste_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Paste"), tooltip_text=translation_manager.translate("MenuPanel", "Paste items from clipboard"), icon=QStyle.StandardPixmap.SP_FileIcon, slot=self.application_logic_handler.paste_item_to_current_dir, shortcut_key=self.KEY_PASTE, add_to_toolbar=True)
        operations_menu.addAction(paste_action)

        move_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Move"), tooltip_text=translation_manager.translate("MenuPanel", "Move selected items"), icon=QStyle.StandardPixmap.SP_DirLinkIcon, slot=self.application_logic_handler.move_selected_item, shortcut_key=self.KEY_MOVE, add_to_toolbar=True)
        operations_menu.addAction(move_action)

        rename_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Rename"), tooltip_text=translation_manager.translate("MenuPanel", "Rename selected item"), icon=QStyle.StandardPixmap.SP_LineEditClearButton, slot=self.application_logic_handler.rename_selected_item, shortcut_key=self.KEY_RENAME, add_to_toolbar=True)
        operations_menu.addAction(rename_action)

        delete_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Delete"), tooltip_text=translation_manager.translate("MenuPanel", "Delete selected items"), icon=QStyle.StandardPixmap.SP_TrashIcon, slot=self.application_logic_handler.delete_selected_item, shortcut_key=self.KEY_DELETE, add_to_toolbar=True)
        operations_menu.addAction(delete_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        compare_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Compare"), tooltip_text=translation_manager.translate("MenuPanel", "Compare selected items"), icon=QStyle.StandardPixmap.SP_FileDialogToParent, slot=self.application_logic_handler.compare_selected_items, shortcut_key=self.KEY_COMPARE, add_to_toolbar=True)
        operations_menu.addAction(compare_action)

        sync_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Synchronize"), tooltip_text=translation_manager.translate("MenuPanel", "Synchronize directories"), icon=QStyle.StandardPixmap.SP_DirLinkIcon, slot=self.application_logic_handler.synchronize_directories, shortcut_key=self.KEY_SYNCHRONIZE, add_to_toolbar=True)
        operations_menu.addAction(sync_action)
