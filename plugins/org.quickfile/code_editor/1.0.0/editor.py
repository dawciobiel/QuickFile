import os
import sys
from PyQt6.QtWidgets import QWidget
from plugins.base import EditorPlugin

class CodeEditorPlugin(EditorPlugin):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "Code Editor"

    @property
    def description(self) -> str:
        return "A built-in code editor with syntax highlighting."

    def can_handle(self, file_path: str) -> bool:
        # For now, let's say it can handle all files.
        # We can refine this later.
        return True

    def create_editor_widget(self, file_path: str, parent: QWidget = None) -> QWidget:
        # This is a workaround to solve relative import issues when the plugin
        # is loaded dynamically. By adding the plugin's own directory to the path,
        # we can import modules from its subdirectories (like 'widgets').
        plugin_dir = os.path.dirname(__file__)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
            
        from widgets.editor_widget import EditorWidget
        
        # It's good practice to remove the path after the import if it's no longer needed,
        # to avoid potential conflicts with other modules.
        if plugin_dir in sys.path:
            sys.path.remove(plugin_dir)

        return EditorWidget(file_path, parent)
