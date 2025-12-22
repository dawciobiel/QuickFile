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

        # Updated default shortcuts to match keys used in MenuPanel
        self.default_shortcuts = {
            "action.exit": "Ctrl+Q",
            "action.go_up": "Backspace",
            "action.refresh": "Ctrl+R",
            "action.new_file": "Shift+F4",
            "action.new_folder": "F7",
            "action.search": "Ctrl+F",
            "action.copy": "F5",
            "action.paste": "Ctrl+V",
            "action.move": "F6",
            "action.rename": "F2",
            "action.delete": "F8",
            "action.compare": "",
            "action.synchronize": "",
            "action.create_archive": "",
            "action.extract_archive": "",
            "action.properties": "",
            "action.about": "",
            "action.flat_view": "",
            "action.tree_view": "",
            "action.configure_shortcuts": "",
            "action.general_settings": "",
            "action.new_tab": "Ctrl+T",
            "action.close_tab": "Ctrl+W",
        }
        self.shortcuts = self.load_shortcuts()

    def load_shortcuts(self):
        shortcuts = self.default_shortcuts.copy()
        if os.path.exists(self.shortcuts_file):
            try:
                with open(self.shortcuts_file, 'r') as f:
                    loaded_shortcuts = json.load(f)
                    # Update defaults with loaded values (merging)
                    shortcuts.update(loaded_shortcuts)
            except json.JSONDecodeError:
                pass  # Fallback to defaults if file is corrupted
        return shortcuts

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
            shortcut_seq = self.shortcuts[name]
            if shortcut_seq:
                self.actions[name].setShortcut(QKeySequence(shortcut_seq))
            else:
                self.actions[name].setShortcut(QKeySequence())

    def apply_shortcuts(self):
        for name in self.actions:
            self.apply_shortcut(name)

    def get_shortcut_string(self, name):
        return self.shortcuts.get(name, "")
