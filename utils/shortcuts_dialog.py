from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QTableWidgetItem

from app.translation_manager import translation_manager


class ShortcutsDialog(QDialog):
    def __init__(self, parent, shortcuts):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/shortcuts_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("ShortcutsDialog", "Keyboard Shortcuts"))
        self.shortcuts = shortcuts
        self._init_table()

    def _init_table(self):
        self.tableWidget.setRowCount(len(self.shortcuts))
        self.tableWidget.setHorizontalHeaderLabels([
            translation_manager.translate("ShortcutsDialog", "Action"),
            translation_manager.translate("ShortcutsDialog", "Shortcut")
        ])

        for i, (action, shortcut) in enumerate(self.shortcuts.items()):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(action))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(shortcut))

        self.tableWidget.resizeColumnsToContents()

    def get_shortcuts(self):
        new_shortcuts = {}
        for i in range(self.tableWidget.rowCount()):
            action = self.tableWidget.item(i, 0).text()
            shortcut = self.tableWidget.item(i, 1).text()
            new_shortcuts[action] = shortcut
        return new_shortcuts
