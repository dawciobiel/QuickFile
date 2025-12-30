from PyQt6.QtGui import QAction

from app.translation_manager import translation_manager


class MenuPanel:
    def __init__(self, main_window, toolbar, app_logic_handler, shortcuts_manager):
        self.main_window = main_window
        self.toolbar = toolbar
        self.app_logic_handler = app_logic_handler
        self.shortcuts_manager = shortcuts_manager

    def initialize_menus(self):
        self._create_toolbar_actions()
        self._create_file_menu()
        self._create_operations_menu()
        self._create_favorites_menu()
        self._create_view_menu()
        self._create_options_menu()
        self._create_help_menu()

    def _create_toolbar_actions(self):
        go_up_action = QAction("Go Up", self.main_window)
        go_up_action.triggered.connect(self.app_logic_handler.go_up_directory)
        self.toolbar.addAction(go_up_action)

        refresh_action = QAction("Refresh", self.main_window)
        refresh_action.triggered.connect(self.app_logic_handler.refresh_all_views)
        self.toolbar.addAction(refresh_action)

    def _create_menu_action(self, menu, text_id, shortcut_id, slot, checkable=False):
        translated_text = translation_manager.translate("MenuPanel", text_id)
        action = QAction(translated_text, self.main_window)
        action.setCheckable(checkable)

        shortcut = self.shortcuts_manager.get_shortcut_string(shortcut_id)
        if shortcut:
            action.setShortcut(shortcut)

        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _create_file_menu(self):
        file_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&File"))
        self._create_menu_action(file_menu, "Properties", "file.properties", self.app_logic_handler.show_properties_dialog)
        self._create_menu_action(file_menu, "Compare", "file.compare", self.app_logic_handler.compare_selected_items)
        file_menu.addSeparator()
        self._create_menu_action(file_menu, "Create Archive", "file.create_archive", self.app_logic_handler.create_archive)
        self._create_menu_action(file_menu, "Extract Archive", "file.extract_archive", self.app_logic_handler.extract_archive)
        file_menu.addSeparator()
        self._create_menu_action(file_menu, "Calculate Checksum", "file.calculate_checksum", self.app_logic_handler.calculate_checksum)
        file_menu.addSeparator()
        self._create_menu_action(file_menu, "Create Link", "file.create_link", self.app_logic_handler.create_link)
        self._create_menu_action(file_menu, "Modify Symbolic Link", "file.modify_link", self.app_logic_handler.modify_symbolic_link)
        file_menu.addSeparator()
        self._create_menu_action(file_menu, "Exit", "file.exit", self.main_window.close)

    def _create_operations_menu(self):
        operations_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Operations"))
        self._create_menu_action(operations_menu, "View", "operations.view", self.app_logic_handler._handle_f3_key)
        self._create_menu_action(operations_menu, "Edit", "operations.edit", self.app_logic_handler._handle_f4_key)
        operations_menu.addSeparator()
        self._create_menu_action(operations_menu, "Copy", "operations.copy", self.app_logic_handler.copy_selected_item)
        self._create_menu_action(operations_menu, "Move", "operations.move", self.app_logic_handler.move_selected_item)
        self._create_menu_action(operations_menu, "Delete", "operations.delete", self.app_logic_handler.delete_selected_item)
        self._create_menu_action(operations_menu, "Rename", "operations.rename", self.app_logic_handler.rename_selected_item)
        operations_menu.addSeparator()
        self._create_menu_action(operations_menu, "New File", "operations.new_file", self.app_logic_handler.create_new_file)
        self._create_menu_action(operations_menu, "New Folder", "operations.new_folder", self.app_logic_handler.create_new_directory)
        operations_menu.addSeparator()
        self._create_menu_action(operations_menu, "Change Owner", "operations.change_owner", self.app_logic_handler.change_owner)

    def _create_favorites_menu(self):
        favorites_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "F&avorites"))
        self._create_menu_action(favorites_menu, "Add to Favorites", "favorites.add", self.app_logic_handler.add_favorite)
        self._create_menu_action(favorites_menu, "Manage Favorites", "favorites.manage", self.app_logic_handler.open_favorites_dialog)

    def _create_view_menu(self):
        view_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&View"))
        self._create_menu_action(view_menu, "Refresh", "view.refresh", self.app_logic_handler.refresh_all_views)
        view_menu.addSeparator()
        self._create_menu_action(view_menu, "New Tab", "view.new_tab", self.app_logic_handler.new_tab)
        self._create_menu_action(view_menu, "Close Tab", "view.close_tab", self.app_logic_handler.close_tab)
        view_menu.addSeparator()
        self._create_menu_action(view_menu, "Search", "view.search", self.app_logic_handler.start_file_search)
        self._create_menu_action(view_menu, "Synchronize Directories", "view.synchronize", self.app_logic_handler.synchronize_directories)

    def _create_options_menu(self):
        options_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Options"))
        self._create_menu_action(options_menu, "General Settings", "options.general_settings",
                                 self.app_logic_handler.open_general_settings_dialog)
        self._create_menu_action(options_menu, "Shortcuts", "options.shortcuts", self.app_logic_handler.open_shortcuts_dialog)

    def _create_help_menu(self):
        help_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Help"))
        self._create_menu_action(help_menu, "About", "help.about", self.app_logic_handler.show_about_dialog)
