# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os

from PyQt6.QtWidgets import QDialog, QComboBox, QCheckBox, QLabel, QDialogButtonBox
from PyQt6.uic import loadUi

from quickfile.app.settings_manager import SettingsManager


class SelectDialog(QDialog):
    # Type hints for dynamically loaded UI elements
    patternComboBox: QComboBox
    caseSensitiveCheckBox: QCheckBox
    onlyFilesCheckBox: QCheckBox
    buttonBox: QDialogButtonBox
    patternLabel: QLabel

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'ui', 'select_dialog.ui')
        loadUi(ui_path, self)

        self._load_history()

    def _load_history(self):
        """Loads pattern history into the combo box."""
        history = self.settings_manager.get_setting("selection_history", [])
        if history:
            self.patternComboBox.addItems(history)

    def get_selection_options(self):
        """Returns the selected options and updates the history."""
        pattern = self.patternComboBox.currentText()

        # Update history
        history = self.settings_manager.get_setting("selection_history", [])
        if pattern in history:
            history.remove(pattern)
        history.insert(0, pattern)
        # Keep the list at a reasonable size
        max_history_size = 15
        self.settings_manager.set_setting("selection_history", history[:max_history_size])

        return {
            "pattern": pattern,
            "case_sensitive": self.caseSensitiveCheckBox.isChecked(),
            "only_files": self.onlyFilesCheckBox.isChecked()
        }
