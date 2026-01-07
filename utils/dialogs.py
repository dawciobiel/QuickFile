# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QMessageBox, QSpacerItem, QSizePolicy, QGridLayout, QWidget
from PyQt6.QtCore import QSize
from app.translation_manager import translation_manager # Import our new manager


def show_error_message(parent: QWidget | None, title: str, message: str):
    """Displays an error message dialog."""
    error_dialog = QMessageBox(parent)
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setText(title)
    error_dialog.setInformativeText(message)
    error_dialog.setWindowTitle(translation_manager.translate("QMessageBox", "Error")) # Zastosowano tłumaczenie dla tytułu okna
    
    # Add a spacer item to force the width
    spacer = QSpacerItem(400, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
    layout = error_dialog.layout()

    # The spacer needs to be added to the layout.
    # We can add it to a new row.
    if isinstance(layout, QGridLayout):
        # The layout of QMessageBox is:
        # row 0: icon and label
        # row 1: informative text
        # row 2: checkbox
        # row 3: buttonbox
        # We add the spacer to the grid. It should span all columns.
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())

    error_dialog.exec()