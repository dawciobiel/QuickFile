import json
import logging
import os

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from utils.resource_path import get_resource_path


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.themes_dir = get_resource_path("themes")
        self.themes = self._discover_themes()
        self.current_theme_name = None
        self.current_theme_data = {}

    def _discover_themes(self):
        themes = []
        if os.path.isdir(self.themes_dir):
            for item in os.listdir(self.themes_dir):
                if os.path.isdir(os.path.join(self.themes_dir, item)):
                    themes.append(item)
        logging.info(f"Discovered themes: {themes}")
        return themes

    def get_themes(self):
        return self.themes

    def get_current_theme_data(self):
        return self.current_theme_data

    def get_theme_path(self):
        if self.current_theme_name:
            return os.path.join(self.themes_dir, self.current_theme_name)
        return None

    def apply_theme(self, theme_name):
        theme_path = os.path.join(self.themes_dir, theme_name)
        if not os.path.isdir(theme_path):
            logging.warning(f"Theme '{theme_name}' not found.")
            return

        self.current_theme_name = theme_name
        
        palette_path = os.path.join(theme_path, "palette.json")
        if not os.path.exists(palette_path):
            logging.warning(f"palette.json not found for theme '{theme_name}'.")
            self.current_theme_data = {}
        else:
            with open(palette_path, 'r') as f:
                self.current_theme_data = json.load(f)

        stylesheet_path = os.path.join(theme_path, "style.qss")
        if not os.path.exists(stylesheet_path):
            logging.warning(f"style.qss not found for theme '{theme_name}'.")
            # We don't return here, as the palette might still be useful
        else:
            with open(stylesheet_path, 'r') as f:
                stylesheet = f.read()

            # Replace placeholders
            for key, value in self.current_theme_data.items():
                if isinstance(value, str):
                    stylesheet = stylesheet.replace(f"@@{key}@@", value)
            
            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)

        logging.info(f"Applied theme: {theme_name}")
        # Emit the signal AFTER all data is loaded and stylesheet is applied
        self.theme_changed.emit(theme_name)
