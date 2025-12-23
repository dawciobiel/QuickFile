from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class SyncDialog(QDialog):
    def __init__(self, parent, source_dir, dest_dir):
        super().__init__(parent)
        uic.loadUi("ui/sync_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("SyncDialog", "Directory Synchronization"))

        self.source_dir = source_dir
        self.dest_dir = dest_dir

        self._init_ui()

    def _init_ui(self):
        # Set path labels
        self.source_dir_label.setText(self.source_dir)
        self.dest_dir_label.setText(self.dest_dir)

        # Configure buttons
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("SyncDialog", "Synchronize"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("SyncDialog", "Cancel"))

    def get_options(self):
        return {
            "two_way": self.two_way_sync_checkbox.isChecked(),
            "delete": self.delete_files_checkbox.isChecked(),
            "include_subdirs": self.include_subdirs_checkbox.isChecked(),
        }
