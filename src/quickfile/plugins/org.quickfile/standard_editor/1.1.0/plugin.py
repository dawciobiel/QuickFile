# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import sys
from PyQt6.QtWidgets import QWidget
from quickfile.plugins.base import EditorPlugin

class StandardEditorPlugin(EditorPlugin):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "Standard Editor"

    def get_description(self) -> str:
        return "A built-in code editor with syntax highlighting."

    def can_handle(self, file_path: str) -> bool:
        return True

    def open_editor(self, file_path: str, theme_manager, parent: QWidget):
        plugin_dir = os.path.dirname(__file__)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
            
        # Import our custom dialog
        from widgets.editor_dialog import EditorDialog
        
        dialog = EditorDialog(file_path, theme_manager, parent)
        dialog.exec()

        if plugin_dir in sys.path:
            sys.path.remove(plugin_dir)
