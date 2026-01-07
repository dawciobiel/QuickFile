# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication

from app.application_logic_handler import ApplicationLogicHandler
from app.translation_manager import translation_manager
from browser.folder_browser import FolderBrowser


class KeyboardEventManager(QObject):
    def __init__(self, main_window, application_logic_handler: ApplicationLogicHandler, folder_browser: FolderBrowser):
        super().__init__(main_window)
        self.main_window = main_window
        self.application_logic_handler = application_logic_handler
        self.folder_browser = folder_browser
        self.shortcuts_manager = main_window.shortcuts_manager

        # Map action names to handler functions
        self.action_handlers = {
            "file.exit": self.main_window.close,
            "toolbar.go_up": self.folder_browser.go_up_directory,
            "view.refresh": self.application_logic_handler.refresh_all_views,
            "operations.new_file": self.application_logic_handler.create_new_file,
            "operations.new_folder": self.application_logic_handler.create_new_directory,
            "view.search": self.application_logic_handler.start_file_search,
            "operations.copy": self.application_logic_handler.copy_selected_item,
            "operations.paste": self.application_logic_handler.paste_item_to_current_dir,
            "operations.move": self.application_logic_handler.move_selected_item,
            "operations.rename": self.application_logic_handler.rename_selected_item,
            "operations.delete": self.application_logic_handler.delete_selected_item,
            "file.compare": self.application_logic_handler.compare_selected_items,
            "view.synchronize": self.application_logic_handler.synchronize_directories,
            "file.create_archive": self.application_logic_handler.create_archive,
            "file.extract_archive": self.application_logic_handler.extract_archive,
            "view.new_tab": self.application_logic_handler.new_tab,
            "view.close_tab": self.application_logic_handler.close_tab,
            "favorites.add": self.application_logic_handler.add_favorite,
            "favorites.manage": self.application_logic_handler.open_favorites_dialog,
            "action.calculate_size": self.application_logic_handler.calculate_directory_size,
            "operations.view": self.application_logic_handler._handle_f3_key,
            "operations.edit": self.application_logic_handler._handle_f4_key,
            "view.focus_path": self.application_logic_handler.set_focus_on_path_edit,
            "selection.select_by_pattern": self.application_logic_handler.show_select_dialog,
            "help.about": self.application_logic_handler.show_about_dialog,
        }

        # Hardcoded shortcuts for essential navigation that might not be in shortcuts manager yet
        # or are considered "system" shortcuts for this app
        self.system_shortcuts = {
            (Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier): self.folder_browser.switch_active_panel,
            (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier): lambda: self.main_window.status_bar.showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)")),
            # F10 is often system menu, but we use it for exit in MC style
            (Qt.Key.Key_F10, Qt.KeyboardModifier.NoModifier): self.main_window.close,
        }

        # Mapping for special Keypad keys to handle them generically
        self.keypad_mapping = {
            "+": Qt.Key.Key_Plus,
            "Keypad Plus": Qt.Key.Key_Plus,
            "-": Qt.Key.Key_Minus,
            "Keypad Minus": Qt.Key.Key_Minus,
            "*": Qt.Key.Key_Asterisk,
            "Keypad Asterisk": Qt.Key.Key_Asterisk,
            "/": Qt.Key.Key_Slash,
            "Keypad Slash": Qt.Key.Key_Slash,
        }

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            if event.modifiers() and event.text():
                event.accept()
                return True

        if QApplication.activeModalWidget() is not None:
            return False

        if event.type() == QEvent.Type.KeyPress:
            was_handled = self.handle_key_event(event)
            if was_handled:
                event.accept()
                return True

        return super().eventFilter(source, event)

    def handle_key_event(self, event):
        # 1. Check system/hardcoded shortcuts first
        key = event.key()
        modifiers = event.modifiers()

        system_action = self.system_shortcuts.get((key, modifiers))
        if system_action:
            system_action()
            return True

        # 2. Check configurable shortcuts
        # Iterate over all configured shortcuts to find a match

        # Convert modifiers to int for bitwise operations
        modifiers_int = modifiers.value

        for action_name, shortcut_str in self.shortcuts_manager.shortcuts.items():
            if not shortcut_str:
                continue

            # Generic handling for Keypad keys
            if modifiers & Qt.KeyboardModifier.KeypadModifier:
                expected_key = self.keypad_mapping.get(shortcut_str)
                if expected_key == key:
                    handler = self.action_handlers.get(action_name)
                    if handler:
                        handler()
                        return True

            # Standard QKeySequence matching
            seq = QKeySequence(shortcut_str)
            if not seq.isEmpty():
                # Compare the QKeySequence created from the event with the one from config
                if seq == QKeySequence(key | modifiers_int):
                    handler = self.action_handlers.get(action_name)
                    if handler:
                        handler()
                        return True

        # 3. Fallback to panel-specific key handling
        if self.folder_browser.active_panel_widget:
            active_view = self.folder_browser.active_panel_widget.file_view
            if hasattr(active_view, 'handle_key_event'):
                return active_view.handle_key_event(event)
            
        return False
