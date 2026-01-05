import json
import os

from PyQt6.QtGui import QAction, QIcon

from app.translation_manager import translation_manager
from utils.resource_path import get_resource_path


class MenuPanel:
    def __init__(self, main_window, toolbar, app_logic_handler, shortcuts_manager):
        self.main_window = main_window
        self.toolbar = toolbar
        self.app_logic_handler = app_logic_handler
        self.shortcuts_manager = shortcuts_manager
        self.actions = {}
        self.icon_map = self._create_icon_map()

    def _create_icon_map(self):
        base_path = "resources/icons/fonts.google.com"
        return {
            "view.refresh": get_resource_path(os.path.join(base_path, "refresh_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "toolbar.go_up": get_resource_path(os.path.join(base_path, "arrow_upward_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.view": get_resource_path(os.path.join(base_path, "description_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.edit": get_resource_path(os.path.join(base_path, "handyman_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.copy": get_resource_path(os.path.join(base_path, "file_copy_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.move": get_resource_path(os.path.join(base_path, "move_item_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.new_folder": get_resource_path(os.path.join(base_path, "create_new_folder_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.delete": get_resource_path(os.path.join(base_path, "scan_delete_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "view.search": get_resource_path(os.path.join(base_path, "search_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "view.synchronize": get_resource_path(os.path.join(base_path, "sync_alt_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "options.general_settings": get_resource_path(os.path.join(base_path, "settings_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.rename": get_resource_path(os.path.join(base_path, "rename_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.new_file": get_resource_path(os.path.join(base_path, "note_add_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "operations.change_owner": get_resource_path(os.path.join(base_path, "person_edit_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "view.new_tab": get_resource_path(os.path.join(base_path, "new_tab_right_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "view.close_tab": get_resource_path(os.path.join(base_path, "close_tab_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "favorites.manage": get_resource_path(os.path.join(base_path, "menage_favorites_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
            "favorites.add": get_resource_path(os.path.join(base_path, "bookmark_add_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg")),
        }

    def initialize_ui(self):
        self._create_all_actions()
        self._build_toolbar_from_config()
        self._build_menus()

    def _create_all_actions(self):
        """Create all possible actions that can be used in menus or toolbars."""
        action_definitions = {
            # File Menu
            "file.properties": (translation_manager.translate("MenuPanel", "Properties"), self.app_logic_handler.show_properties_dialog),
            "file.compare": (translation_manager.translate("MenuPanel", "Compare"), self.app_logic_handler.compare_selected_items),
            "file.create_archive": (translation_manager.translate("MenuPanel", "Create Archive"), self.app_logic_handler.create_archive),
            "file.extract_archive": (translation_manager.translate("MenuPanel", "Extract Archive"), self.app_logic_handler.extract_archive),
            "file.calculate_checksum": (translation_manager.translate("MenuPanel", "Calculate Checksum"),
                                        self.app_logic_handler.calculate_checksum),
            "file.create_link": (translation_manager.translate("MenuPanel", "Create Link"), self.app_logic_handler.create_link),
            "file.modify_link": (translation_manager.translate("MenuPanel", "Modify Symbolic Link"),
                                 self.app_logic_handler.modify_symbolic_link),
            "file.exit": (translation_manager.translate("MenuPanel", "Exit"), self.main_window.close),
            # Operations Menu
            "operations.view": (translation_manager.translate("MenuPanel", "View"), self.app_logic_handler._handle_f3_key),
            "operations.edit": (translation_manager.translate("MenuPanel", "Edit"), self.app_logic_handler._handle_f4_key),
            "operations.copy": (translation_manager.translate("MenuPanel", "Copy"), self.app_logic_handler.copy_selected_item),
            "operations.move": (translation_manager.translate("MenuPanel", "Move"), self.app_logic_handler.move_selected_item),
            "operations.delete": (translation_manager.translate("MenuPanel", "Delete"), self.app_logic_handler.delete_selected_item),
            "operations.rename": (translation_manager.translate("MenuPanel", "Rename"), self.app_logic_handler.rename_selected_item),
            "operations.new_file": (translation_manager.translate("MenuPanel", "New File"), self.app_logic_handler.create_new_file),
            "operations.new_folder": (translation_manager.translate("MenuPanel", "New Folder"),
                                      self.app_logic_handler.create_new_directory),
            "operations.change_owner": (translation_manager.translate("MenuPanel", "Change Owner"), self.app_logic_handler.change_owner),
            # Favorites Menu
            "favorites.add": (translation_manager.translate("MenuPanel", "Add to Favorites"), self.app_logic_handler.add_favorite),
            "favorites.manage": (translation_manager.translate("MenuPanel", "Manage Favorites"),
                                 self.app_logic_handler.open_favorites_dialog),
            # View Menu
            "view.refresh": (translation_manager.translate("MenuPanel", "Refresh"), self.app_logic_handler.refresh_all_views),
            "view.show_toolbar": (translation_manager.translate("MenuPanel", "Show Toolbar"),
                                  self.app_logic_handler.toggle_toolbar_visibility, True),
            "view.new_tab": (translation_manager.translate("MenuPanel", "New Tab"), self.app_logic_handler.new_tab),
            "view.close_tab": (translation_manager.translate("MenuPanel", "Close Tab"), self.app_logic_handler.close_tab),
            "view.search": (translation_manager.translate("MenuPanel", "Search"), self.app_logic_handler.start_file_search),
            "view.synchronize": (translation_manager.translate("MenuPanel", "Synchronize Directories"),
                                 self.app_logic_handler.synchronize_directories),
            "view.focus_path": (translation_manager.translate("MenuPanel", "Focus Path Edit"), self.app_logic_handler.set_focus_on_path_edit),
            # Options Menu
            "options.general_settings": (translation_manager.translate("MenuPanel", "General Settings"),
                                         self.app_logic_handler.open_general_settings_dialog),
            "options.shortcuts": (translation_manager.translate("MenuPanel", "Shortcuts"), self.app_logic_handler.open_shortcuts_dialog),
            # Help Menu
            "help.about": (translation_manager.translate("MenuPanel", "About"), self.app_logic_handler.show_about_dialog),
            # Toolbar-specific actions
            "toolbar.go_up": (translation_manager.translate("MenuPanel", "Go Up"), self.app_logic_handler.go_up_directory),
        }

        for shortcut_id, definition in action_definitions.items():
            text, slot, *rest = definition
            checkable = rest[0] if rest else False

            action = QAction(text, self.main_window)
            action.setCheckable(checkable)

            if shortcut_id in self.icon_map:
                action.setIcon(QIcon(self.icon_map[shortcut_id]))

            shortcut = self.shortcuts_manager.get_shortcut_string(shortcut_id)
            if shortcut:
                action.setShortcut(shortcut)

            if checkable:
                action.toggled.connect(slot)
            else:
                action.triggered.connect(slot)

            self.main_window.addAction(action)

            self.actions[shortcut_id] = action

    def _build_toolbar_from_config(self):
        self.toolbar.clear()
        config_path = get_resource_path("config/toolbar_layout.json")
        try:
            with open(config_path, 'r') as f:
                layout_config = json.load(f)

            for item in layout_config:
                if not item.get("visible", False):
                    continue

                item_id = item.get("id")
                if item_id == "separator":
                    self.toolbar.addSeparator()
                elif item_id in self.actions:
                    self.toolbar.addAction(self.actions[item_id])
                else:
                    print(f"Warning: Action '{item_id}' from toolbar_layout.json not found.")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading toolbar config: {e}. Building default toolbar.")
            self.toolbar.addAction(self.actions["toolbar.go_up"])
            self.toolbar.addAction(self.actions["view.refresh"])

    def _build_menus(self):
        self._create_file_menu()
        self._create_operations_menu()
        self._create_favorites_menu()
        self._create_view_menu()
        self._create_options_menu()
        self._create_help_menu()

    def _add_action_to_menu(self, menu, shortcut_id):
        if shortcut_id in self.actions:
            menu.addAction(self.actions[shortcut_id])

    def _create_file_menu(self):
        file_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&File"))
        self._add_action_to_menu(file_menu, "file.properties")
        self._add_action_to_menu(file_menu, "file.compare")
        file_menu.addSeparator()
        self._add_action_to_menu(file_menu, "file.create_archive")
        self._add_action_to_menu(file_menu, "file.extract_archive")
        file_menu.addSeparator()
        self._add_action_to_menu(file_menu, "file.calculate_checksum")
        file_menu.addSeparator()
        self._add_action_to_menu(file_menu, "file.create_link")
        self._add_action_to_menu(file_menu, "file.modify_link")
        file_menu.addSeparator()
        self._add_action_to_menu(file_menu, "file.exit")

    def _create_operations_menu(self):
        operations_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Operations"))
        self._add_action_to_menu(operations_menu, "operations.view")
        self._add_action_to_menu(operations_menu, "operations.edit")
        operations_menu.addSeparator()
        self._add_action_to_menu(operations_menu, "operations.copy")
        self._add_action_to_menu(operations_menu, "operations.move")
        self._add_action_to_menu(operations_menu, "operations.delete")
        self._add_action_to_menu(operations_menu, "operations.rename")
        operations_menu.addSeparator()
        self._add_action_to_menu(operations_menu, "operations.new_file")
        self._add_action_to_menu(operations_menu, "operations.new_folder")
        operations_menu.addSeparator()
        self._add_action_to_menu(operations_menu, "operations.change_owner")

    def _create_favorites_menu(self):
        favorites_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "F&avorites"))
        self._add_action_to_menu(favorites_menu, "favorites.add")
        self._add_action_to_menu(favorites_menu, "favorites.manage")

    def _create_view_menu(self):
        view_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&View"))
        self._add_action_to_menu(view_menu, "view.refresh")
        view_menu.addSeparator()
        self._add_action_to_menu(view_menu, "view.show_toolbar")
        view_menu.addSeparator()
        self._add_action_to_menu(view_menu, "view.new_tab")
        self._add_action_to_menu(view_menu, "view.close_tab")
        view_menu.addSeparator()
        self._add_action_to_menu(view_menu, "view.search")
        self._add_action_to_menu(view_menu, "view.synchronize")
        view_menu.addSeparator()
        self._add_action_to_menu(view_menu, "view.focus_path")

    def _create_options_menu(self):
        options_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Options"))
        self._add_action_to_menu(options_menu, "options.general_settings")
        self._add_action_to_menu(options_menu, "options.shortcuts")

    def _create_help_menu(self):
        help_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Help"))
        self._add_action_to_menu(help_menu, "help.about")
