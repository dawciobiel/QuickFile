# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QApplication
from app.translation_manager import translation_manager

class ChecksumResultDialog(QDialog):
    def __init__(self, parent, title, results):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)

        self.layout = QVBoxLayout(self)

        self.results_text_edit = QTextEdit()
        self.results_text_edit.setReadOnly(True)
        self.results_text_edit.setText(results)
        self.layout.addWidget(self.results_text_edit)

        self.button_layout = QHBoxLayout()
        self.copy_button = QPushButton(translation_manager.translate("ChecksumResultDialog", "Copy to Clipboard"))
        self.close_button = QPushButton(translation_manager.translate("Buttons", "Close"))

        self.button_layout.addWidget(self.copy_button)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_button)
        
        self.layout.addLayout(self.button_layout)

        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.close_button.clicked.connect(self.accept)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.results_text_edit.toPlainText())
        self.copy_button.setText(translation_manager.translate("ChecksumResultDialog", "Copied!"))
        self.copy_button.setEnabled(False)
