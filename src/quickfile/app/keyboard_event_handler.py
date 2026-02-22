# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication

from quickfile.app.application_logic_handler import ApplicationLogicHandler
from quickfile.app.translation_manager import translation_manager
from quickfile.browser.folder_browser import FolderBrowser


class KeyboardEventManager(QObject):
    def __init__(self, main_window, application_logic_handler: ApplicationLogicHandler = None, folder_browser: FolderBrowser = None):
        super().__init__(main_window)
        self.main_window = main_window
        self._application_logic_handler = application_logic_handler
        self._folder_browser = folder_browser
        self.shortcuts_manager = main_window.shortcuts_manager

        self._action_handlers = {}
        self._system_shortcuts = {}
        self._keypad_mapping = {
            "+": Qt.Key.Key_Plus,
            "Keypad Plus": Qt.Key.Key_Plus,
            "-": Qt.Key.Key_Minus,
            "Keypad Minus": Qt.Key.Key_Minus,
            "*": Qt.Key.Key_Asterisk,
            "Keypad Asterisk": Qt.Key.Key_Asterisk,
            "/": Qt.Key.Key_Slash,
            "Keypad Slash": Qt.Key.Key_Slash,
        }
        
        # Initialize handlers if dependencies are already available
        if self._application_logic_handler and self._folder_browser:
            self._initialize_handlers()

    @property
    def application_logic_handler(self):
        return self._application_logic_handler

    @application_logic_handler.setter
    def application_logic_handler(self, handler: ApplicationLogicHandler):
        self._application_logic_handler = handler
        self._initialize_handlers() # Re-initialize handlers when dependency is set

    @property
    def folder_browser(self):
        return self._folder_browser

    @folder_browser.setter
    def folder_browser(self, browser: FolderBrowser):
        self._folder_browser = browser
        self._initialize_handlers() # Re-initialize handlers when dependency is set

    def _initialize_handlers(self):
        """
        Initializes or re-initializes action handlers and system shortcuts
        once all dependencies are available.
        """
        if not self._application_logic_handler or not self._folder_browser:
            return # Not all dependencies are set yet

        logging.debug("KeyboardEventManager: Initializing action handlers.")
        self._action_handlers = {
            "file.exit": self.main_window.close,
            "toolbar.go_up": self._folder_browser.go_up_directory,
            "view.refresh": self._application_logic_handler.refresh_all_views,
            "operations.new_file": self._application_logic_handler.create_new_file,
            "operations.new_folder": self._application_logic_handler.create_new_directory,
            "view.search": self._application_logic_handler.start_file_search,
            "operations.copy": self._application_logic_handler.copy_selected_item,
            "operations.move": self._application_logic_handler.move_selected_item,
            "operations.rename": self._application_logic_handler.rename_selected_item,
            "operations.delete": self._application_logic_handler.delete_selected_item,
            "file.compare": self._application_logic_handler.compare_selected_items,
            "view.synchronize": self._application_logic_handler.synchronize_directories,
            "file.create_archive": self._application_logic_handler.create_archive,
            "file.extract_archive": self._application_logic_handler.extract_archive,
            "view.new_tab": self._application_logic_handler.new_tab,
            "view.close_tab": self._application_logic_handler.close_tab,
            "favorites.add": self._application_logic_handler.add_favorite,
            "favorites.manage": self._application_logic_handler.open_favorites_dialog,
            "action.calculate_size": self._application_logic_handler.calculate_directory_size,
            "operations.view": self._application_logic_handler._handle_f3_key,
            "operations.edit": self._application_logic_handler._handle_f4_key,
            "view.focus_path": self._application_logic_handler.set_focus_on_path_edit,
            "selection.select_by_pattern": self._application_logic_handler.show_select_dialog,
            "help.about": self._application_logic_handler.show_about_dialog,
        }

        self._system_shortcuts = {
            (Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier): self._folder_browser.switch_active_panel,
            (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier): lambda: self.main_window.statusBar().showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)")),
            (Qt.Key.Key_F10, Qt.KeyboardModifier.NoModifier): self.main_window.close,
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
        if not self._application_logic_handler or not self._folder_browser:
            logging.warning("KeyboardEventManager: Handlers not initialized yet.")
            return False

        key = event.key()
        modifiers = event.modifiers()

        # 1. Check system/hardcoded shortcuts first
        system_action = self._system_shortcuts.get((key, modifiers))
        if system_action:
            system_action()
            return True

        # 2. Check configurable shortcuts
        modifiers_int = modifiers.value

        for action_name, shortcut_str in self.shortcuts_manager.shortcuts.items():
            if not shortcut_str:
                continue

            # Generic handling for Keypad keys
            if modifiers & Qt.KeyboardModifier.KeypadModifier:
                expected_key = self._keypad_mapping.get(shortcut_str)
                if expected_key == key:
                    handler = self._action_handlers.get(action_name)
                    if handler:
                        handler()
                        return True

            # Standard QKeySequence matching
            seq = QKeySequence(shortcut_str)
            if not seq.isEmpty():
                if seq == QKeySequence(key | modifiers_int):
                    handler = self._action_handlers.get(action_name)
                    if handler:
                        handler()
                        return True

        # 3. Fallback to panel-specific key handling (e.g., Enter to go into folder)
        if self._folder_browser.active_panel_widget:
            active_view = self._folder_browser.active_panel_widget.file_view
            if hasattr(active_view, 'handle_key_event'):
                return active_view.handle_key_event(event)
            
        return False
