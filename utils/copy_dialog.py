import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class CopyDialog(QDialog):
    def __init__(self, parent, source_paths, destination_path):
        super().__init__(parent)
        uic.loadUi("ui/file_operation_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("CopyDialog", "Copy"))
        
        if isinstance(source_paths, str):
            self.source_paths = [source_paths]
        else:
            self.source_paths = source_paths
            
        self.destination_path = destination_path
        
        self._init_options_ui()

    def _init_options_ui(self):
        # Ensure we are on the options page and hide the progress page
        self.stackedWidget.setCurrentWidget(self.options_page)
        
        if len(self.source_paths) == 1:
            self.source_path_label.setText(self.source_paths[0])
        else:
            self.source_path_label.setText(translation_manager.translate("CopyDialog", f"{len(self.source_paths)} items selected"))
            
        self.destination_path_label.setText(self.destination_path)

        self.overwrite_checkbox.setText(translation_manager.translate("CopyDialog", "Overwrite existing files"))
        self.preserve_timestamp_checkbox.setText(translation_manager.translate("CopyDialog", "Preserve original modification date"))
        self.preserve_timestamp_checkbox.setChecked(True)
        self.preserve_timestamp_checkbox.setVisible(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))
        
        # The dialog now just accepts or rejects, no task starting here
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def get_options(self):
        """Returns the selected options from the dialog."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "preserve_timestamp": self.preserve_timestamp_checkbox.isChecked(),
        }
