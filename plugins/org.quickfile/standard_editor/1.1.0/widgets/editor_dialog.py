import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
from PyQt6.QtCore import Qt
from .editor_widget import EditorWidget

class EditorDialog(QDialog):
    def __init__(self, file_path, theme_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editor - {os.path.basename(file_path)}")
        self.resize(800, 600)

        self.editor_widget = EditorWidget(file_path, theme_manager, self)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        
        self.button_box.accepted.connect(self.save_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.editor_widget)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def save_and_accept(self):
        if self.editor_widget.save_file():
            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.editor_widget.find_text()
            event.accept()
        elif event.key() == Qt.Key.Key_F3:
            self.editor_widget.find_next()
            event.accept()
        else:
            super().keyPressEvent(event)
