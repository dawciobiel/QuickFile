import json
import os

class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.join(os.path.expanduser("~"), ".quickfile_settings.json")
        self.default_settings = {
            "view_mode": "flat" # Domyślny tryb widoku
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Połącz domyślne ustawienia z wczytanymi, aby zapewnić, że wszystkie klucze istnieją
                    self.default_settings.update(loaded_settings)
                    return self.default_settings
            except json.JSONDecodeError:
                # Jeśli plik jest uszkodzony, użyj domyślnych ustawień
                return self.default_settings
        return self.default_settings

    def save_settings(self, new_settings):
        self.settings.update(new_settings) # Zaktualizuj bieżące ustawienia
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get_setting(self, key):
        return self.settings.get(key, self.default_settings.get(key))

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings(self.settings) # Zapisz po każdej zmianie
