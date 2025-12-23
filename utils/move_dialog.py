from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class MoveDialog(QDialog):
    def __init__(self, parent, source_path, destination_path):
        super().__init__(parent)
        uic.loadUi("ui/file_operation_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("MoveDialog", "Move"))

        self._init_ui(source_path, destination_path)

    def _init_ui(self, source_path, destination_path):
        # Set labels
        self.source_path_label.setText(source_path)
        self.destination_path_label.setText(destination_path)

        # Configure options
        self.overwrite_checkbox.setText(translation_manager.translate("MoveDialog", "Overwrite existing files"))
        self.preserve_timestamp_checkbox.setVisible(False) # Not applicable for move

        # Configure buttons
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))

    def get_options(self):
        """Returns a dictionary with selected options."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
        }
