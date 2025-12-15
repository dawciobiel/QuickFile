import os
import json
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, themes_dir="themes"):
        super().__init__()
        self.themes_dir = themes_dir
        self.available_themes = self._discover_themes()
        self.current_theme_name = None

    def _discover_themes(self):
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
        palette_path = os.path.join(self.themes_dir, theme_name, "palette.json")
        if os.path.exists(palette_path):
            with open(palette_path, 'r') as f:
                return json.load(f)
        return {}

    def _load_qss(self, theme_name):
        qss_path = os.path.join(self.themes_dir, theme_name, "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as f:
                return f.read()
        return ""

    def apply_theme(self, theme_name):
        if theme_name not in self.available_themes:
            logging.warning(f"Theme '{theme_name}' not found.")
            return False

        palette = self._load_palette(theme_name)
        raw_qss = self._load_qss(theme_name)

        processed_qss = raw_qss
        for var, value in palette.items():
            processed_qss = processed_qss.replace(f"@@{var}@@", value)
        
        QApplication.instance().setStyleSheet(processed_qss)
        self.current_theme_name = theme_name
        self.theme_changed.emit(self.get_theme_path(theme_name)) # Emit full path
        logging.info(f"Applied theme: {theme_name}")
        return True

    def get_available_themes(self):
        return self.available_themes

    def get_current_theme_name(self):
        return self.current_theme_name

    def get_theme_path(self, theme_name=None):
        """
        Returns the absolute path to the directory of the specified theme.
        If theme_name is None, returns the path of the current theme.
        """
        if theme_name is None:
            theme_name = self.current_theme_name
        if theme_name:
            return os.path.join(self.themes_dir, theme_name)
        return None
