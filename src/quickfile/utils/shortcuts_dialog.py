# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QDialogButtonBox
from quickfile.app.translation_manager import translation_manager
from quickfile.utils.resource_path import get_resource_path

class ShortcutsDialog(QDialog):
    def __init__(self, parent, shortcuts):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/shortcuts_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("ShortcutsDialog", "Keyboard Shortcuts"))
        self.shortcuts = shortcuts
        self._init_ui()

    def _init_ui(self):
        # Configure table
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels([translation_manager.translate("ShortcutsDialog", "Action"), translation_manager.translate("ShortcutsDialog", "Shortcut")])
        self.tableWidget.setRowCount(len(self.shortcuts))

        for i, (action, shortcut) in enumerate(self.shortcuts.items()):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(action))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(shortcut))

        self.tableWidget.resizeColumnsToContents()

        # Configure buttons
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText(translation_manager.translate("ShortcutsDialog", "Save"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("ShortcutsDialog", "Cancel"))
        
        # Signals are already connected in .ui file (accepted -> accept, rejected -> reject)

    def get_shortcuts(self):
        new_shortcuts = {}
        for i in range(self.tableWidget.rowCount()):
            action = self.tableWidget.item(i, 0).text()
            shortcut = self.tableWidget.item(i, 1).text()
            new_shortcuts[action] = shortcut
        return new_shortcuts
