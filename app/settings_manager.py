import json
import os
import shutil
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMainWindow

class SettingsManager:
    def __init__(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile")
        os.makedirs(config_dir, exist_ok=True)
        self.settings_file = os.path.join(config_dir, "settings.json")
        
        # Migrate old settings file if it exists
        old_settings_file = os.path.join(os.path.expanduser("~"), ".quickfile_settings.json")
        if os.path.exists(old_settings_file) and not os.path.exists(self.settings_file):
            shutil.move(old_settings_file, self.settings_file)

        self.default_settings = {
            "view_mode": "flat",
            "leftPanelPath": os.path.expanduser("~"),
            "rightPanelPath": os.path.expanduser("~"),
            "activePanel": "left",
            "showDotFiles": True,
            "active_selection_color": "#336699",  # Darker blue for active selection
            "inactive_selection_color": "#606060" # Darker gray for inactive selection
        }
        self.settings = self.load_settings_from_file()

    def load_settings_from_file(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                # Start with defaults and update with loaded settings
                settings = self.default_settings.copy()
                settings.update(loaded_settings)
                return settings
            except (json.JSONDecodeError, IOError):
                return self.default_settings.copy()
        return self.default_settings.copy()

    def save_settings_to_file(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError:
            print(f"Warning: Could not save settings to {self.settings_file}")

    def get_setting(self, key, default=None):
        # Ensure that if a new default is added, it's correctly returned if not in settings.json
        return self.settings.get(key, self.default_settings.get(key, default))

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings_to_file()

    def load_window_settings(self, window: QMainWindow):
        q_settings = QSettings("QuickFile", "QuickFile")
        geometry = q_settings.value("geometry", window.saveGeometry())
        window.restoreGeometry(geometry)
        window_state = q_settings.value("windowState", window.saveState())
        window.restoreState(window_state)

    def save_window_settings(self, window: QMainWindow):
        q_settings = QSettings("QuickFile", "QuickFile")
        q_settings.setValue("geometry", window.saveGeometry())
        q_settings.setValue("windowState", window.saveState())
