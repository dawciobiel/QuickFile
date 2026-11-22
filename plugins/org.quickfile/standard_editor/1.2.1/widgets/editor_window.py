# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from .editor_widget import EditorWidget
from app.translation_manager import translation_manager


class EditorWindow(QMainWindow):
    """Non-modal editor window with the usual window controls.

    A ``QDialog`` shown with ``exec()`` blocked the host application and had no
    minimise/maximise buttons. This window behaves like the bundled file viewer:
    the plugin calls ``show()`` and keeps it in ``open_editors``.
    """

    closed = pyqtSignal()

    def __init__(self, file_path, theme_manager, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(
            translation_manager.translate("StandardEditor", "Editor - {name}").format(
                name=os.path.basename(file_path)
            )
        )
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(800, 600)

        self.editor_widget = EditorWidget(file_path, theme_manager, self)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.save_and_close)
        self.button_box.rejected.connect(self.close)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.editor_widget)
        layout.addWidget(self.button_box)
        self.setCentralWidget(central)

    def save_and_close(self):
        if not self.editor_widget.save_file():
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Save Failed"),
                translation_manager.translate(
                    "StandardEditor", "Could not save {name}."
                ).format(name=os.path.basename(self.file_path)),
            )
            return
        self.close()

    def closeEvent(self, event):
        if not self.editor_widget.has_unsaved_changes():
            self.closed.emit()
            super().closeEvent(event)
            return

        choice = QMessageBox.question(
            self,
            translation_manager.translate("StandardEditor", "Unsaved Changes"),
            translation_manager.translate(
                "StandardEditor", "Save changes to {name}?"
            ).format(name=os.path.basename(self.file_path)),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if choice == QMessageBox.StandardButton.Save:
            if not self.editor_widget.save_file():
                event.ignore()
                return
        elif choice != QMessageBox.StandardButton.Discard:
            event.ignore()
            return

        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.editor_widget.find_text()
            event.accept()
        elif event.key() == Qt.Key.Key_F3:
            self.editor_widget.find_next()
            event.accept()
        else:
            super().keyPressEvent(event)
