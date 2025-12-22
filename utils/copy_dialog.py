from PyQt6 import uic
from PyQt6.QtWidgets import QDialog

from app.translation_manager import translation_manager


class CopyDialog(QDialog):
    def __init__(self, parent, source_path, destination_path):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/file_operation_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("CopyDialog", "Copy"))

        # Set labels
        self.source_label_title.setText(translation_manager.translate("CopyDialog", "Source:"))
        self.source_path_label.setText(source_path)
        self.destination_label_title.setText(translation_manager.translate("CopyDialog", "Destination:"))
        self.destination_path_label.setText(destination_path)

        # Set options
        self.options_group.setTitle(translation_manager.translate("CopyDialog", "Options"))
        self.overwrite_checkbox.setText(translation_manager.translate("CopyDialog", "Overwrite existing files"))
        self.preserve_timestamp_checkbox.setText(translation_manager.translate("CopyDialog", "Preserve original modification date"))
        self.preserve_timestamp_checkbox.setChecked(True)

    def get_options(self):
        """Returns a dictionary with selected options."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "preserve_timestamp": self.preserve_timestamp_checkbox.isChecked(),
        }
