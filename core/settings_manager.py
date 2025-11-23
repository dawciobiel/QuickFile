import json
import os
import shutil

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
            "activePanel": "left"
        }
        self.settings = self.load_settings()

    def load_settings(self):
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

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError:
            print(f"Warning: Could not save settings to {self.settings_file}")

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()
