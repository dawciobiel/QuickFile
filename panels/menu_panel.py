from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QStyle, QToolBar

from app.application_logic_handler import ApplicationLogicHandler  # Import ApplicationLogicHandler
from app.shortcuts_manager import ShortcutsManager  # Import ShortcutsManager
from app.translation_manager import translation_manager


class MenuPanel(QObject):
    go_up_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    view_mode_changed = pyqtSignal(str)

    # --- Stable, Non-Translated Action Keys for Shortcuts and Logic ---
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
        self._create_archive_menu()
        self._create_view_menu()
        self._create_settings_menu()
        self._create_help_menu()

    def _create_action(self, visible_text, tooltip_text, icon=None, slot=None, shortcut_key=None, add_to_toolbar=False):
        """
        Helper to create a QAction. It accepts ALREADY TRANSLATED text.
        The shortcut_key is the stable, non-translated key.
        """
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
            slot=self.application_logic_handler.open_shortcuts_dialog, # Delegated
            shortcut_key=self.KEY_CONFIGURE_SHORTCUTS
        )
        settings_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "General Settings"),
            tooltip_text=translation_manager.translate("MenuPanel", "General Settings"),
            slot=self.application_logic_handler.open_general_settings_dialog, # Delegated
            shortcut_key=self.KEY_GENERAL_SETTINGS
        )
        settings_menu.addAction(shortcuts_action)
        settings_menu.addAction(settings_action)

    # Removed open_general_settings_dialog and open_shortcuts_dialog from here

    def _create_file_menu(self):
        file_menu = self.menu_bar.addMenu(translation_manager.translate("MainWindow", "File"))
        
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

        file_menu.addAction(compare_action)
        file_menu.addAction(properties_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # self.toolbar.addAction(properties_action) # Handled by add_to_toolbar

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

        # --- Go Up ---
        go_up_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Go Up"),
            tooltip_text=translation_manager.translate("MenuPanel", "Go to parent directory"),
            icon=QStyle.StandardPixmap.SP_ArrowUp,
            slot=self.go_up_requested,
            shortcut_key=self.KEY_GO_UP,
            add_to_toolbar=True
        )
        # self.toolbar.addAction(go_up_action) # Handled by add_to_toolbar
        operations_menu.addAction(go_up_action)

        # --- Refresh ---
        refresh_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Refresh"),
            tooltip_text=translation_manager.translate("MenuPanel", "Refresh the current view"),
            icon=QStyle.StandardPixmap.SP_BrowserReload,
            slot=self.refresh_requested,
            shortcut_key=self.KEY_REFRESH,
            add_to_toolbar=True
        )
        # self.toolbar.addAction(refresh_action) # Handled by add_to_toolbar
        operations_menu.addAction(refresh_action)
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        # --- Other Operations ---
        
        # New File
        new_file_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "New File"),
            tooltip_text=translation_manager.translate("MenuPanel", "Create a new empty file"),
            icon=QStyle.StandardPixmap.SP_FileIcon,
            slot=lambda: self.application_logic_handler.create_new_file(self.application_logic_handler._get_active_panel_path()),
            shortcut_key=self.KEY_NEW_FILE,
            add_to_toolbar=True
        )
        operations_menu.addAction(new_file_action)

        # New Folder
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

        # Search
        search_action = self._create_action(
            visible_text=translation_manager.translate("MenuPanel", "Search"),
            tooltip_text=translation_manager.translate("MenuPanel", "Search for files and directories"),
            icon=QStyle.StandardPixmap.SP_FileDialogDetailedView,
            slot=self.application_logic_handler.start_file_search,  # Corrected slot
            shortcut_key=self.KEY_SEARCH,
            add_to_toolbar=True
        )
        operations_menu.addAction(search_action)
        # self.toolbar.addAction(search_action) # Handled by add_to_toolbar
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        # Copy
        copy_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Copy"), tooltip_text=translation_manager.translate("MenuPanel", "Copy selected items"), icon=QStyle.StandardPixmap.SP_FileLinkIcon, slot=self.application_logic_handler.copy_selected_item, shortcut_key=self.KEY_COPY, add_to_toolbar=True)
        operations_menu.addAction(copy_action)
        # self.toolbar.addAction(copy_action) # Handled by add_to_toolbar

        # Paste
        paste_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Paste"), tooltip_text=translation_manager.translate("MenuPanel", "Paste items from clipboard"), icon=QStyle.StandardPixmap.SP_FileIcon, slot=self.application_logic_handler.paste_item_to_current_dir, shortcut_key=self.KEY_PASTE, add_to_toolbar=True)
        operations_menu.addAction(paste_action)
        # self.toolbar.addAction(paste_action) # Handled by add_to_toolbar

        # Move
        move_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Move"), tooltip_text=translation_manager.translate("MenuPanel", "Move selected items"), icon=QStyle.StandardPixmap.SP_DirLinkIcon, slot=self.application_logic_handler.move_selected_item, shortcut_key=self.KEY_MOVE, add_to_toolbar=True)
        operations_menu.addAction(move_action)
        # self.toolbar.addAction(move_action) # Handled by add_to_toolbar

        # Rename
        rename_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Rename"), tooltip_text=translation_manager.translate("MenuPanel", "Rename selected item"), icon=QStyle.StandardPixmap.SP_LineEditClearButton, slot=self.application_logic_handler.rename_selected_item, shortcut_key=self.KEY_RENAME, add_to_toolbar=True)
        operations_menu.addAction(rename_action)
        # self.toolbar.addAction(rename_action) # Handled by add_to_toolbar

        # Delete
        delete_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Delete"), tooltip_text=translation_manager.translate("MenuPanel", "Delete selected items"), icon=QStyle.StandardPixmap.SP_TrashIcon, slot=self.application_logic_handler.delete_selected_item, shortcut_key=self.KEY_DELETE, add_to_toolbar=True)
        operations_menu.addAction(delete_action)
        # self.toolbar.addAction(delete_action) # Handled by add_to_toolbar
        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        # Compare
        compare_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Compare"), tooltip_text=translation_manager.translate("MenuPanel", "Compare selected items"), icon=QStyle.StandardPixmap.SP_FileDialogToParent, slot=self.application_logic_handler.compare_selected_items, shortcut_key=self.KEY_COMPARE, add_to_toolbar=True)
        operations_menu.addAction(compare_action)
        # self.toolbar.addAction(compare_action) # Handled by add_to_toolbar

        # Synchronize
        sync_action = self._create_action(visible_text=translation_manager.translate("MenuPanel", "Synchronize"), tooltip_text=translation_manager.translate("MenuPanel", "Synchronize directories"), icon=QStyle.StandardPixmap.SP_DirLinkIcon, slot=self.application_logic_handler.synchronize_directories, shortcut_key=self.KEY_SYNCHRONIZE, add_to_toolbar=True)
        operations_menu.addAction(sync_action)
        # self.toolbar.addAction(sync_action) # Handled by add_to_toolbar
