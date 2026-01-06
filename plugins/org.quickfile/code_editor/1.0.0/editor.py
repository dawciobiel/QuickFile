import os
import sys
from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QDialogButtonBox
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
        return True

    def open_editor(self, file_path: str, theme_manager, parent: QWidget):
        # This is a workaround to solve relative import issues when the plugin
        # is loaded dynamically.
        plugin_dir = os.path.dirname(__file__)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
            
        from widgets.editor_widget import EditorWidget
        
        dialog = QDialog(parent)
        dialog.setWindowTitle(f"Editor - {os.path.basename(file_path)}")
        dialog.resize(800, 600)

        editor_widget = EditorWidget(file_path, theme_manager, dialog)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        
        def save_and_accept():
            if editor_widget.save_file():
                dialog.accept()

        button_box.accepted.connect(save_and_accept)
        button_box.rejected.connect(dialog.reject)

        layout = QVBoxLayout(dialog)
        layout.addWidget(editor_widget)
        layout.addWidget(button_box)
        dialog.setLayout(layout)
        
        dialog.exec()

        if plugin_dir in sys.path:
            sys.path.remove(plugin_dir)
