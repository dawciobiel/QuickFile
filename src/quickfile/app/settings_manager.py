# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import json
import os
import shutil
import platform

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMainWindow
from quickfile.app.task_queue_manager import TaskType


class SettingsManager:
    def __init__(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile")
        os.makedirs(config_dir, exist_ok=True)
        self.settings_file = os.path.join(config_dir, "settings.json")
        
        old_settings_file = os.path.join(os.path.expanduser("~"), ".quickfile_settings.json")
        if os.path.exists(old_settings_file) and not os.path.exists(self.settings_file):
            shutil.move(old_settings_file, self.settings_file)

        self.default_settings = {
            "leftPanelPath": os.path.expanduser("~"),
            "rightPanelPath": os.path.expanduser("~"),
            "activePanel": "left",
            "showDotFiles": True,
            "active_selection_color": "#336699",
            "inactive_selection_color": "#606060",
            "file_permissions_display_mode": "symbolic",
            "show_uid_column": True,
            "show_gid_column": True,
            "language_mode": "auto",
            "manual_language": "en_US",
            "insert_selection_text_color": "#FFFFFF",
            "insert_selection_font_bold": False,
            "insert_selection_font_italic": False,
            "viewer_command": "xdg-open %f",
            "editor_command": "xdg-open %f",
            "use_default_terminal": True,
            "custom_terminal_command": self.get_default_terminal_command(),
            "use_default_admin_terminal": True,
            "custom_admin_terminal_command": self.get_default_admin_terminal_command(),
            "bringToFrontOnStartup": True,
            "theme": "dark",
            "sound_notifications_enabled": True,
        }
        
        # Add default notification settings for all task types
        for task_type in TaskType:
            self.default_settings[f"notify_on_{task_type.name.lower()}"] = True

        self.settings = self.load_settings_from_file()

    def get_default_terminal_command(self):
        system = platform.system()
        if system == "Windows":
            return 'cmd.exe /c "cd /d %d && start cmd.exe"'
        elif system == "Darwin": # macOS
            return 'open -a Terminal %d'
        else: # Linux and other Unix-like
            # Try to find a suitable terminal
            terminals = {"gnome-terminal": "--working-directory=%d", "konsole": "--workdir %d", "xfce4-terminal": "--working-directory=%d"}
            for term, arg in terminals.items():
                if shutil.which(term):
                    return f"{term} {arg}"
            return 'x-terminal-emulator' # Fallback

    def get_default_admin_terminal_command(self):
        system = platform.system()
        if system == "Windows":
            return 'powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k cd /d %d\'"'
        elif system == "Darwin": # macOS
            return "osascript -e 'do shell script \"cd \\\"%d\\\"; open -a Terminal .\" with administrator privileges'"
        else: # Linux
            # Find a suitable terminal and construct the sudo command
            terminals = {"konsole": "--workdir %d -e sudo -s", "gnome-terminal": "--working-directory=%d -- bash -c \"sudo -s; exec bash\"", "xfce4-terminal": "--working-directory=%d -e 'sudo -s'"}
            for term, cmd_format in terminals.items():
                if shutil.which(term):
                    return f"{term} {cmd_format}"
            return 'x-terminal-emulator -e "sudo -s"' # Fallback

    def load_settings_from_file(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
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
