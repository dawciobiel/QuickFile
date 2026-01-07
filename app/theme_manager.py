# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

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
        
        # Load palette
        palette_data = {}
        palette_path = os.path.join(theme_path, "palette.json")
        if not os.path.exists(palette_path):
            logging.warning(f"palette.json not found for theme '{theme_name}'.")
        else:
            with open(palette_path, 'r') as f:
                palette_data = json.load(f)
        
        self.current_theme_data = palette_data.copy()

        # Load file styles, ensuring keys always exist
        file_styles_path = os.path.join(theme_path, "file_styles.json")
        if os.path.exists(file_styles_path):
            with open(file_styles_path, 'r') as f:
                file_styles = json.load(f)
                self.current_theme_data['file_styles'] = file_styles.get('file_styles', {})
                self.current_theme_data['special_types'] = file_styles.get('special_types', {})
        else:
            # Ensure keys exist even if file is missing
            self.current_theme_data['file_styles'] = {}
            self.current_theme_data['special_types'] = {}

        # Apply stylesheet
        stylesheet_path = os.path.join(theme_path, "style.qss")
        if not os.path.exists(stylesheet_path):
            logging.warning(f"style.qss not found for theme '{theme_name}'.")
        else:
            with open(stylesheet_path, 'r') as f:
                stylesheet = f.read()

            # Replace placeholders ONLY from the original palette data
            for key, value in palette_data.items():
                if isinstance(value, str):
                    stylesheet = stylesheet.replace(f"@@{key}@@", value)
            
            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)

        logging.info(f"Applied theme: {theme_name}")
        self.theme_changed.emit(theme_name)
