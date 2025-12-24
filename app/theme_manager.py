import os
import json
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.themes_dir = os.path.join(os.path.dirname(__file__), "..", "themes")
        self.themes = self._discover_themes()
        self.current_theme_path = None

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

    def get_theme_path(self):
        return self.current_theme_path

    def apply_theme(self, theme_name):
        theme_path = os.path.join(self.themes_dir, theme_name)
        if not os.path.isdir(theme_path):
            logging.warning(f"Theme '{theme_name}' not found.")
            return

        self.current_theme_path = theme_path
        
        # Load palette
        palette_path = os.path.join(theme_path, "palette.json")
        if not os.path.exists(palette_path):
            logging.warning(f"palette.json not found for theme '{theme_name}'.")
            return
            
        with open(palette_path, 'r') as f:
            palette = json.load(f)

        # Load stylesheet
        stylesheet_path = os.path.join(theme_path, "style.qss")
        if not os.path.exists(stylesheet_path):
            logging.warning(f"style.qss not found for theme '{theme_name}'.")
            return
            
        with open(stylesheet_path, 'r') as f:
            stylesheet = f.read()

        # Replace placeholders
        for key, value in palette.items():
            stylesheet = stylesheet.replace(f"@@{key}@@", value)
            
        # Replace dynamic colors from settings
        active_color = self.settings_manager.get_setting("active_selection_color")
        inactive_color = self.settings_manager.get_setting("inactive_selection_color")
        
        stylesheet = stylesheet.replace("@@selection_background@@", active_color)
        stylesheet = stylesheet.replace("@@inactive_selection_background@@", inactive_color)

        QApplication.instance().setStyleSheet(stylesheet)
        logging.info(f"Applied theme: {theme_name}")
        self.theme_changed.emit(theme_path)
