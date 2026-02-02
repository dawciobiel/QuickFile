# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import json
import os
from functools import partial
import importlib
import logging

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QMessageBox

from quickfile.app.plugin_sandbox import SandboxedPluginWrapper
from quickfile.app.task_queue_manager import Task, TaskType
from quickfile.app.translation_manager import translation_manager
from quickfile.utils.icon_manager import get_colorized_icon
from quickfile.utils.resource_path import get_resource_path


class MenuPanel:
    def __init__(self, main_window, toolbar, app_logic_handler, shortcuts_manager, theme_manager):
        self.main_window = main_window
        self.toolbar = toolbar
        self.app_logic_handler = app_logic_handler
        self.shortcuts_manager = shortcuts_manager
        self.theme_manager = theme_manager
        self.actions = {}
        self.icon_map = self._create_icon_map()
        theme_data = self.theme_manager.get_current_theme_data()
        self.icon_color = theme_data.get("icon_color", theme_data.get("foreground", "#000000"))


    def _create_icon_map(self):
        base_path = "resources/icons/fonts.google.com"
        
        return {
            "view.refresh": get_resource_path(os.path.join(base_path, "refresh.svg")),
            "toolbar.go_up": get_resource_path(os.path.join(base_path, "go_up.svg")),
            "operations.view": get_resource_path(os.path.join(base_path, "view.svg")),
            "operations.edit": get_resource_path(os.path.join(base_path, "edit.svg")),
            "operations.copy": get_resource_path(os.path.join(base_path, "copy.svg")),
            "operations.move": get_resource_path(os.path.join(base_path, "move.svg")),
            "operations.new_folder": get_resource_path(os.path.join(base_path, "new_folder.svg")),
            "operations.delete": get_resource_path(os.path.join(base_path, "delete.svg")),
            "view.search": get_resource_path(os.path.join(base_path, "search.svg")),
            "view.synchronize": get_resource_path(os.path.join(base_path, "synchronize.svg")),
            "options.general_settings": get_resource_path(os.path.join(base_path, "settings.svg")),
            "operations.rename": get_resource_path(os.path.join(base_path, "rename.svg")),
            "operations.new_file": get_resource_path(os.path.join(base_path, "new_file.svg")),
            "operations.change_owner": get_resource_path(os.path.join(base_path, "change_owner.svg")),
            "operations.open_terminal": get_resource_path(os.path.join(base_path, "subdirectory_arrow_right.svg")),
            "operations.open_admin_terminal": get_resource_path(os.path.join(base_path, "subdirectory_arrow_right.svg")), # Re-using icon
            "view.new_tab": get_resource_path(os.path.join(base_path, "new_tab.svg")),
            "view.close_tab": get_resource_path(os.path.join(base_path, "close_tab.svg")),
            "favorites.manage": get_resource_path(os.path.join(base_path, "manage_favorites.svg")),
            "favorites.add": get_resource_path(os.path.join(base_path, "add_favorite.svg")),
            "file.properties": get_resource_path(os.path.join(base_path, "file_properties.svg")),
        }

    def initialize_ui(self):
        self._create_all_actions()
        self._build_toolbar_from_config()
        self._build_menus()
        self._add_plugin_actions()

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
            "operations.open_terminal": (translation_manager.translate("MenuPanel", "Open Terminal Here"), self.app_logic_handler.open_terminal_here),
            "operations.open_admin_terminal": (translation_manager.translate("MenuPanel", "Open Admin Terminal Here"), self.app_logic_handler.open_admin_terminal_here),
            # Selection Menu
            "selection.select_by_pattern": (translation_manager.translate("MenuPanel", "Select by Pattern"),
                                            self.app_logic_handler.show_select_dialog),
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
                icon_path = self.icon_map[shortcut_id]
                action.setIcon(get_colorized_icon(icon_path, self.icon_color))

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
        self.file_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&File"))
        self._add_action_to_menu(self.file_menu, "file.properties")
        self._add_action_to_menu(self.file_menu, "file.compare")
        self.file_menu.addSeparator()
        self._add_action_to_menu(self.file_menu, "file.create_archive")
        self._add_action_to_menu(self.file_menu, "file.extract_archive")
        self.file_menu.addSeparator()
        self._add_action_to_menu(self.file_menu, "file.create_link")
        self._add_action_to_menu(self.file_menu, "file.modify_link")
        # "Exit" and plugin actions will be added later

    def _create_operations_menu(self):
        self.operations_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Operations"))
        self._add_action_to_menu(self.operations_menu, "operations.view")
        self._add_action_to_menu(self.operations_menu, "operations.edit")
        self.operations_menu.addSeparator()
        self._add_action_to_menu(self.operations_menu, "operations.copy")
        self._add_action_to_menu(self.operations_menu, "operations.move")
        self._add_action_to_menu(self.operations_menu, "operations.delete")
        self._add_action_to_menu(self.operations_menu, "operations.rename")
        self.operations_menu.addSeparator()
        self._add_action_to_menu(self.operations_menu, "operations.new_file")
        self._add_action_to_menu(self.operations_menu, "operations.new_folder")
        
        if "operations.change_owner" in self.actions:
            self.operations_menu.addSeparator()
            self._add_action_to_menu(self.operations_menu, "operations.change_owner")

        self.operations_menu.addSeparator()
        self._add_action_to_menu(self.operations_menu, "operations.open_terminal")
        self._add_action_to_menu(self.operations_menu, "operations.open_admin_terminal")

    def _create_favorites_menu(self):
        self.favorites_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "F&avorites"))
        self._add_action_to_menu(self.favorites_menu, "favorites.add")
        self._add_action_to_menu(self.favorites_menu, "favorites.manage")

    def _create_view_menu(self):
        self.view_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&View"))
        self._add_action_to_menu(self.view_menu, "view.refresh")
        self.view_menu.addSeparator()
        self._add_action_to_menu(self.view_menu, "view.show_toolbar")
        self.view_menu.addSeparator()
        self._add_action_to_menu(self.view_menu, "view.new_tab")
        self._add_action_to_menu(self.view_menu, "view.close_tab")
        self.view_menu.addSeparator()
        self._add_action_to_menu(self.view_menu, "view.search")
        self._add_action_to_menu(self.view_menu, "view.synchronize")
        self.view_menu.addSeparator()
        self._add_action_to_menu(self.view_menu, "view.focus_path")

    def _create_options_menu(self):
        self.options_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Options"))
        self._add_action_to_menu(self.options_menu, "options.general_settings")
        self._add_action_to_menu(self.options_menu, "options.shortcuts")

    def _create_help_menu(self):
        self.help_menu = self.main_window.menuBar().addMenu(translation_manager.translate("MenuPanel", "&Help"))
        self._add_action_to_menu(self.help_menu, "help.about")

    def _add_plugin_actions(self):
        menu_plugins = self.app_logic_handler.task_queue_manager.plugin_manager.get_menu_action_plugins()
        
        menus = {
            "file": self.file_menu,
            "operations": self.operations_menu,
            "view": self.view_menu,
            "options": self.options_menu,
            "help": self.help_menu
        }
        
        plugin_actions_by_menu = {name: [] for name in menus.keys()}
        if menu_plugins:
            for plugin in menu_plugins:
                for action_info in plugin.get_menu_actions():
                    target_menu_name = action_info.get("menu", "").lower()
                    if target_menu_name in plugin_actions_by_menu:
                        action = QAction(action_info["text"], self.main_window)

                        if isinstance(plugin, SandboxedPluginWrapper):
                            action_id = action_info.get("action_id")
                            if action_id:
                                action.triggered.connect(partial(self._handle_sandboxed_action, plugin, action_info))
                        else:
                            action.triggered.connect(action_info["callback"])
                            
                        if "icon_path" in action_info:
                            action.setIcon(get_colorized_icon(action_info["icon_path"], self.icon_color))
                        plugin_actions_by_menu[target_menu_name].append(action)

        # --- Finalize File Menu ---
        file_tools_actions = [self.actions.get("file.calculate_checksum")] + plugin_actions_by_menu["file"]
        file_tools_actions = [action for action in file_tools_actions if action]

        if file_tools_actions:
            self.file_menu.addSeparator()
            for action in file_tools_actions:
                self.file_menu.addAction(action)
        
        self.file_menu.addSeparator()
        self._add_action_to_menu(self.file_menu, "file.exit")

        # --- Finalize Other Menus ---
        for menu_name, menu_widget in menus.items():
            if menu_name == "file":
                continue
            
            if plugin_actions_by_menu[menu_name]:
                menu_widget.addSeparator()
                for action in plugin_actions_by_menu[menu_name]:
                    menu_widget.addAction(action)

    def _handle_sandboxed_action(self, plugin_wrapper, action_info):
        plugin_id = plugin_wrapper.metadata.get("id")
        
        dialog_module_name = action_info.get("dialog_module")
        dialog_class_name = action_info.get("dialog_class")
        
        if not (dialog_module_name and dialog_class_name):
            logging.error(f"Plugin {plugin_id} action is missing dialog information.")
            return

        try:
            selected_path = self.app_logic_handler.ui_state_provider.get_current_selected_path()
            if not selected_path:
                 QMessageBox.warning(self.main_window, "Action", "Please select an item first.")
                 return

            dialog_module = importlib.import_module(dialog_module_name)
            DialogClass = getattr(dialog_module, dialog_class_name)
            
            dialog = DialogClass(self.main_window, selected_path)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                task_type_str = action_info.get("task_type")
                
                if not task_type_str:
                    logging.error(f"Plugin {plugin_id} action is missing task_type.")
                    return
                
                task_type = TaskType[task_type_str]
                
                options = {**data, "plugin_id": plugin_id}
                
                task = Task(task_type, source_paths=[selected_path], destination_path=data.get("destination_path"), options=options)
                self.app_logic_handler.task_queue_manager.add_task(task)
                self.main_window.statusBar().showMessage(f"Added {task_type.name.replace('_', ' ').lower()} task to queue.")

        except (ImportError, AttributeError) as e:
            logging.error(f"Could not load or create dialog for plugin {plugin_id}: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Failed to open dialog for plugin: {plugin_id}")
        except Exception as e:
            logging.error(f"An error occurred while handling sandboxed action for {plugin_id}: {e}", exc_info=True)
            QMessageBox.critical(self.main_window, "Error", f"An unexpected error occurred: {e}")
