import json
import os
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import QStandardPaths # Dodaj ten import

class ShortcutsManager:
    def __init__(self, main_window):
        self.main_window = main_window
        
        # Zmieniona ścieżka do pliku skrótów
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation)
        quickfile_config_dir = os.path.join(config_dir, "QuickFile")
        
        if not os.path.exists(quickfile_config_dir):
            os.makedirs(quickfile_config_dir) # Tworzymy katalog, jeśli nie istnieje

        self.shortcuts_file = os.path.join(quickfile_config_dir, "quickfile_shortcuts.json")
        self.actions = {}
        self.default_shortcuts = {
            "Exit": "Ctrl+Q",
            "Go Up": "",
            "Refresh": "Ctrl+R",
            "New File": "",
            "New Folder": "F7",
            "Search": "",
            "Copy": "F5",
            "Paste": "Ctrl+V",
            "Move": "F6",
            "Rename": "F2",
            "Delete": "F8",
            "Compare": "F9",
            "Synchronize": "",
            "Create Archive": "",
            "Extract Archive": "",
            "Open Bookmarks": "Ctrl+B",
        }
        self.shortcuts = self.load_shortcuts()

    def load_shortcuts(self):
        if os.path.exists(self.shortcuts_file):
            with open(self.shortcuts_file, 'r') as f:
                return json.load(f)
        return self.default_shortcuts

    def save_shortcuts(self, shortcuts):
        with open(self.shortcuts_file, 'w') as f:
            json.dump(shortcuts, f, indent=4)
        self.shortcuts = shortcuts
        self.apply_shortcuts()

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
