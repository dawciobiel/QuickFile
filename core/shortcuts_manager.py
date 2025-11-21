import json
import os
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction

class ShortcutsManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.shortcuts_file = os.path.join(os.path.expanduser("~"), ".quickfile_shortcuts.json")
        self.actions = {}
        self.default_shortcuts = {
            "Wyjdź": "Ctrl+Q",
            "Idź w górę": "",
            "Odśwież": "Ctrl+R",
            "Nowy Plik": "",
            "Nowy Folder": "F7",
            "Szukaj": "",
            "Kopiuj": "F5",
            "Wklej": "Ctrl+V",
            "Przenieś": "F6",
            "Zmień nazwę": "F2",
            "Usuń": "F8",
            "Porównaj": "F9",
            "Synchronizuj": "",
            "Utwórz archiwum": "",
            "Wypakuj archiwum": "",
            "Otwórz zakładki": "Ctrl+B",
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
