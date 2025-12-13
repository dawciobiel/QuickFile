import os
import json
import logging
from PyQt6.QtWidgets import QApplication

class ThemeManager:
    def __init__(self, themes_dir="themes"):
        self.themes_dir = themes_dir
        self.available_themes = self._discover_themes()
        self.current_theme_name = None

    def _discover_themes(self):
        """
        Discovers available themes by scanning subdirectories in the themes_dir.
        Returns a list of theme names (directory names).
        """
        themes = []
        if os.path.exists(self.themes_dir) and os.path.isdir(self.themes_dir):
            for entry in os.listdir(self.themes_dir):
                theme_path = os.path.join(self.themes_dir, entry)
                if os.path.isdir(theme_path) and \
                   os.path.exists(os.path.join(theme_path, "palette.json")) and \
                   os.path.exists(os.path.join(theme_path, "style.qss")):
                    themes.append(entry)
        logging.info(f"Discovered themes: {themes}")
        return sorted(themes)

    def _load_palette(self, theme_name):
        """
        Loads the palette.json for a given theme.
        Returns a dictionary of color variables.
        """
        palette_path = os.path.join(self.themes_dir, theme_name, "palette.json")
        if os.path.exists(palette_path):
            with open(palette_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_qss(self, theme_name):
        """
        Loads the style.qss for a given theme.
        Returns the raw QSS string.
        """
        qss_path = os.path.join(self.themes_dir, theme_name, "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                return f.read()
        return ""

    def apply_theme(self, theme_name):
        """
        Loads, processes, and applies the specified theme to the QApplication.
        """
        if theme_name not in self.available_themes:
            logging.warning(f"Theme '{theme_name}' not found.")
            return False

        palette = self._load_palette(theme_name)
        raw_qss = self._load_qss(theme_name)

        processed_qss = raw_qss
        for var, value in palette.items():
            # Replace placeholders like @@variable_name@@ with actual color values
            processed_qss = processed_qss.replace(f"@@{var}@@", value)
        
        QApplication.instance().setStyleSheet(processed_qss)
        self.current_theme_name = theme_name
        logging.info(f"Applied theme: {theme_name}")
        return True

    def get_available_themes(self):
        return self.available_themes

    def get_current_theme_name(self):
        return self.current_theme_name
