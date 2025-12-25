from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from app.translation_manager import translation_manager


class SyncDialog(QDialog):
    def __init__(self, parent, left_path, right_path):
        super().__init__(parent)
        uic.loadUi("ui/sync_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("SyncDialog", "Synchronize Directories"))

        self.source_dir_label.setText(left_path)
        self.dest_dir_label.setText(right_path)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def get_options(self):
        return {
            "two_way": self.two_way_sync_checkbox.isChecked(),
            "left_to_right": not self.two_way_sync_checkbox.isChecked(), # Assuming one-way if not two-way
            "right_to_left": False, # This logic needs to be improved if we want 3-way choice
            "include_subdirs": self.include_subdirs_checkbox.isChecked(),
            "delete": self.delete_files_checkbox.isChecked(),
            "by_content": False # This option is not in the UI, default to False
        }
