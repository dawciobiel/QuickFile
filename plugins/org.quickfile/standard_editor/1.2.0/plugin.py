# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import sys
from PyQt6.QtWidgets import QWidget
from plugins.base import EditorPlugin


class StandardEditorPlugin(EditorPlugin):
    def __init__(self):
        super().__init__()
        #: Absolute file path -> open EditorWindow. One window per file.
        self.open_editors = {}

    def get_name(self) -> str:
        return "Standard Editor"

    def get_description(self) -> str:
        return "A built-in code editor with syntax highlighting."

    def can_handle(self, file_path: str) -> bool:
        return True

    def open_editor(self, file_path: str, theme_manager, parent: QWidget = None):
        file_path = os.path.abspath(file_path)

        existing = self.open_editors.get(file_path)
        if existing is not None:
            existing.raise_()
            existing.activateWindow()
            return existing

        plugin_dir = os.path.dirname(__file__)
        added_to_path = plugin_dir not in sys.path
        if added_to_path:
            sys.path.insert(0, plugin_dir)

        try:
            from widgets.editor_window import EditorWindow

            window = EditorWindow(file_path, theme_manager, parent)
        finally:
            if added_to_path and plugin_dir in sys.path:
                sys.path.remove(plugin_dir)

        self.open_editors[file_path] = window
        window.closed.connect(lambda path=file_path: self._forget_editor(path))
        window.show()
        return window

    def _forget_editor(self, file_path: str):
        window = self.open_editors.pop(file_path, None)
        if window is not None:
            window.deleteLater()
