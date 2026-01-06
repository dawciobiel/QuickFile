import json
import os

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QKeySequence


class ShortcutsManager:
    def __init__(self, main_window):
        self.main_window = main_window
        
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation)
        quickfile_config_dir = os.path.join(config_dir, "QuickFile")
        
        if not os.path.exists(quickfile_config_dir):
            os.makedirs(quickfile_config_dir)

        self.shortcuts_file = os.path.join(quickfile_config_dir, "quickfile_shortcuts.json")
        self.actions = {}
        self.default_shortcuts = {
            "file.exit": "Ctrl+Q",
            "toolbar.go_up": "",
            "view.refresh": "Ctrl+R",
            "operations.new_file": "Shift+F4",
            "operations.new_folder": "F7",
            "view.search": "",
            "operations.copy": "F5",
            "operations.paste": "Ctrl+V",
            "operations.move": "F6",
            "operations.rename": "F2",
            "operations.delete": "F8",
            "file.compare": "F9",
            "view.synchronize": "",
            "file.create_archive": "",
            "file.extract_archive": "",
            "view.new_tab": "Ctrl+T",
            "view.close_tab": "Ctrl+W",
            "favorites.add": "Ctrl+D",
            "favorites.manage": "Ctrl+Shift+B",
            "action.calculate_size": "Ctrl+Space"
        }
        self.shortcuts = self.load_shortcuts()

    def load_shortcuts(self):
        if os.path.exists(self.shortcuts_file):
            with open(self.shortcuts_file, 'r') as f:
                loaded_settings = json.load(f)
                # Migrate old keys if necessary (simple check)
                if "action.exit" in loaded_settings:
                    return self.default_shortcuts.copy()  # Force defaults if old keys detected

                defaults = self.default_shortcuts.copy()
                defaults.update(loaded_settings)
                return defaults
        return self.default_shortcuts.copy()

    def save_shortcuts(self, shortcuts):
        with open(self.shortcuts_file, 'w') as f:
            json.dump(shortcuts, f, indent=4)
        self.shortcuts = shortcuts
        self.apply_shortcuts()

    def apply_shortcuts_settings(self, shortcuts):
        self.save_shortcuts(shortcuts)

    def register_action(self, name, action):
        self.actions[name] = action
        self.apply_shortcut(name)

    def apply_shortcut(self, name):
        if name in self.actions and name in self.shortcuts:
            self.actions[name].setShortcut(QKeySequence(self.shortcuts[name]))

    def apply_shortcuts(self):
        for name in self.actions:
            self.apply_shortcut(name)

    def get_shortcut_string(self, name):
        return self.shortcuts.get(name, "")
