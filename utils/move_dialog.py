from PyQt6 import uic
from PyQt6.QtWidgets import QDialog

from app.translation_manager import translation_manager


class MoveDialog(QDialog):
    def __init__(self, parent, source_path, destination_path):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/file_operation_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("MoveDialog", "Move"))

        # Set labels
        self.source_label_title.setText(translation_manager.translate("MoveDialog", "Source:"))
        self.source_path_label.setText(source_path)
        self.destination_label_title.setText(translation_manager.translate("MoveDialog", "Destination:"))
        self.destination_path_label.setText(destination_path)

        # Set options
        self.options_group.setTitle(translation_manager.translate("MoveDialog", "Options"))
        self.overwrite_checkbox.setText(translation_manager.translate("MoveDialog", "Overwrite existing files"))

        # Hide the preserve timestamp option for move operations
        self.preserve_timestamp_checkbox.setVisible(False)

    def get_options(self):
        """Returns a dictionary with selected options."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
        }
