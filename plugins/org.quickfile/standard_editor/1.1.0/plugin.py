import os
import sys
from PyQt6.QtWidgets import QWidget
from plugins.base import EditorPlugin

class StandardEditorPlugin(EditorPlugin):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "Standard Editor"

    @property
    def description(self) -> str:
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
