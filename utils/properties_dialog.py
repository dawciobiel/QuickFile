from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QTextEdit

from app.translation_manager import translation_manager


class PropertiesDialog(QDialog):
    def __init__(self, properties, parent=None):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/properties_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("PropertiesDialog", "Properties"))

        if properties:
            for key, value in properties.items():
                translated_key = translation_manager.translate("PropertiesDialog", key)
                if key == 'Full path':
                    path_text_edit = QTextEdit()
                    path_text_edit.setReadOnly(True)
                    path_text_edit.setText(str(value))
                    path_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                    path_text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                    path_text_edit.setFixedHeight(60)
                    self.formLayout.addRow(QLabel(f"{translated_key}:"), path_text_edit)
                else:
                    label_value = QLabel(str(value))
                    label_value.setWordWrap(True)
                    self.formLayout.addRow(QLabel(f"{translated_key}:"), label_value)
