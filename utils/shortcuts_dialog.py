from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

class ShortcutsDialog(QDialog):
    def __init__(self, parent, shortcuts):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.shortcuts = shortcuts
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.table.setRowCount(len(self.shortcuts))

        for i, (action, shortcut) in enumerate(self.shortcuts.items()):
            self.table.setItem(i, 0, QTableWidgetItem(action))
            self.table.setItem(i, 1, QTableWidgetItem(shortcut))

        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_shortcuts(self):
        new_shortcuts = {}
        for i in range(self.table.rowCount()):
            action = self.table.item(i, 0).text()
            shortcut = self.table.item(i, 1).text()
            new_shortcuts[action] = shortcut
        return new_shortcuts
