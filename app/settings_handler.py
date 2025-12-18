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

    def apply_general_settings(self, new_settings: dict):
        """Applies the general settings received from the settings dialog."""
        # This logic will be moved from ApplicationLogicHandler
        pass

    def apply_shortcuts_settings(self, new_shortcuts: dict):
        """Applies the new shortcuts from the shortcuts dialog."""
        # This logic will be moved from ApplicationLogicHandler
        pass
