import json
import os
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import QStandardPaths

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
            "action.exit": "Ctrl+Q",
            "action.go_up": "",
            "action.refresh": "Ctrl+R",
            "action.new_file": "",
            "action.new_folder": "F7",
            "action.search": "",
            "action.copy": "F5",
            "action.paste": "Ctrl+V",
            "action.move": "F6",
            "action.rename": "F2",
            "action.delete": "F8",
            "action.compare": "F9",
            "action.synchronize": "",
            "action.create_archive": "",
            "action.extract_archive": "",
            "action.new_tab": "Ctrl+T",
            "action.close_tab": "Ctrl+W",
            "action.add_favorite": "Ctrl+D",
            "action.show_favorites": "Ctrl+Shift+B",
        }
        self.shortcuts = self.load_shortcuts()

    def load_shortcuts(self):
        if os.path.exists(self.shortcuts_file):
            with open(self.shortcuts_file, 'r') as f:
                loaded_settings = json.load(f)
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
