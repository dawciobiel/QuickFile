# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QLabel, QTextEdit, QDialogButtonBox
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager
from utils.resource_path import get_resource_path

class PropertiesDialog(QDialog):
    def __init__(self, properties, parent=None):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/properties_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("PropertiesDialog", "Properties"))

        self._init_ui(properties)
        self.retranslate_ui()

    def _init_ui(self, properties):
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

    def retranslate_ui(self):
        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText(translation_manager.translate("Buttons", "OK"))
