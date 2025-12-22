from PyQt6 import uic
from PyQt6.QtWidgets import QDialog

from app.translation_manager import translation_manager


class SyncDialog(QDialog):
    def __init__(self, parent, source_dir, dest_dir):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/sync_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("SyncDialog", "Directory Synchronization"))

        self.source_dir_label.setText(source_dir)
        self.dest_dir_label.setText(dest_dir)

        self._translate_ui()

    def _translate_ui(self):
        self.source_label_title.setText(translation_manager.translate("SyncDialog", "Source:"))
        self.dest_label_title.setText(translation_manager.translate("SyncDialog", "Destination:"))
        self.options_group.setTitle(translation_manager.translate("SyncDialog", "Synchronization Options"))
        self.two_way_sync_checkbox.setText(
            translation_manager.translate("SyncDialog", "Two-way synchronization (copy newer files both ways)"))
        self.delete_files_checkbox.setText(
            translation_manager.translate("SyncDialog", "Delete files in destination folder if they don't exist in source"))
        self.include_subdirs_checkbox.setText(translation_manager.translate("SyncDialog", "Include subdirectories"))

    def get_options(self):
        return {
            "two_way": self.two_way_sync_checkbox.isChecked(),
            "delete": self.delete_files_checkbox.isChecked(),
            "include_subdirs": self.include_subdirs_checkbox.isChecked(),
        }
