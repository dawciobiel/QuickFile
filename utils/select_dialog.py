import os

from PyQt6.QtWidgets import QDialog, QComboBox, QCheckBox, QLabel, QDialogButtonBox
from PyQt6.uic import loadUi


class SelectDialog(QDialog):
    # Type hints for dynamically loaded UI elements
    patternComboBox: QComboBox
    caseSensitiveCheckBox: QCheckBox
    onlyFilesCheckBox: QCheckBox
    buttonBox: QDialogButtonBox
    patternLabel: QLabel

    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'ui', 'select_dialog.ui')
        loadUi(ui_path, self)

    def get_selection_options(self):
        return {
            "pattern": self.patternComboBox.currentText(),
            "case_sensitive": self.caseSensitiveCheckBox.isChecked(),
            "only_files": self.onlyFilesCheckBox.isChecked()
        }
