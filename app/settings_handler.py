# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging

from PyQt6.QtWidgets import QMessageBox

from app.translation_manager import translation_manager


class SettingsHandler:
    """Handles the logic of applying application settings."""

    def __init__(self, main_window, settings_manager, shortcuts_manager, theme_manager):
        self.main_window = main_window
        self.settings_manager = settings_manager
        self.shortcuts_manager = shortcuts_manager
        self.theme_manager = theme_manager

    def apply_all_settings(self):
        """Applies all settings at startup."""
        # Apply theme
        theme_name = self.settings_manager.get_setting("theme", "dark")
        self.theme_manager.apply_theme(theme_name)

        # Apply window geometry
        self.settings_manager.load_window_settings(self.main_window)

        # Apply toolbar visibility
        toolbar_visible = self.settings_manager.get_setting("toolbar_visible", True)
        self.main_window.mainToolbar.setVisible(toolbar_visible)
        if self.main_window.menu_panel:
            show_toolbar_action = self.main_window.menu_panel.actions.get("view.show_toolbar")
            if show_toolbar_action:
                show_toolbar_action.setChecked(toolbar_visible)

        # Apply other settings that affect the UI
        self.main_window.folder_browser.refresh_all_views()

    def save_window_state(self):
        """Saves window geometry and state."""
        self.settings_manager.save_window_settings(self.main_window)

    def apply_general_settings(self, new_settings: dict):
        """Applies the general settings received from the settings dialog."""
        # Update settings in SettingsManager
        for key, value in new_settings.items():
            self.settings_manager.set_setting(key, value)

        # Apply specific settings that require immediate UI updates
        if "showDotFiles" in new_settings:
            # The FolderBrowser's create_file_view method uses settings_manager.get_setting("showDotFiles")
            # So, refreshing the views should pick up the new setting.
            self.main_window.folder_browser.refresh_all_views()

        if "file_permissions_display_mode" in new_settings or \
                "show_uid_column" in new_settings or \
                "show_gid_column" in new_settings:
            # These settings affect how file details are displayed.
            # Calling update_view_settings on file_view will refresh the model and delegate.
            left_panel = self.main_window.folder_browser.get_left_panel_widget()
            right_panel = self.main_window.folder_browser.get_right_panel_widget()
            
            if left_panel and hasattr(left_panel.file_view, 'update_view_settings'):
                left_panel.file_view.update_view_settings()
            if right_panel and hasattr(right_panel.file_view, 'update_view_settings'):
                right_panel.file_view.update_view_settings()

        if "language_mode" in new_settings or "manual_language" in new_settings:
            # For language changes, we typically need to restart the application.
            # Inform the user about this.
            QMessageBox.information(
                self.main_window,
                translation_manager.translate("SettingsHandler", "Language Change"),
                translation_manager.translate("SettingsHandler", "Language settings will take effect after restarting the application.")
            )
            # Optionally, you could trigger a restart here, but usually, it's left to the user.

        if "theme" in new_settings:
            self.theme_manager.apply_theme(new_settings["theme"])

        logging.info("General settings applied successfully.")

    def apply_shortcuts_settings(self, new_shortcuts: dict):
        """Applies the new shortcuts from the shortcuts dialog."""
        self.shortcuts_manager.save_shortcuts(new_shortcuts)
        self.shortcuts_manager.apply_shortcuts()
