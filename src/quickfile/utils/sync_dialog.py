# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from quickfile.app.translation_manager import translation_manager
from quickfile.utils.resource_path import get_resource_path


class SyncDialog(QDialog):
    def __init__(self, parent, left_path, right_path):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/sync_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("SyncDialog", "Synchronize Directories"))
        self.retranslate_ui()

        self.source_dir_label.setText(left_path)
        self.dest_dir_label.setText(right_path)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def retranslate_ui(self):
        self.source_label_title.setText(translation_manager.translate("SyncDialog", "Source:"))
        self.dest_label_title.setText(translation_manager.translate("SyncDialog", "Destination:"))
        self.options_group.setTitle(translation_manager.translate("SyncDialog", "Synchronization options"))
        self.two_way_sync_checkbox.setText(translation_manager.translate("SyncDialog", "Two-way synchronization (copy newer files both ways)"))
        self.delete_files_checkbox.setText(translation_manager.translate("SyncDialog", "Delete files in destination folder if they don't exist in source"))
        self.include_subdirs_checkbox.setText(translation_manager.translate("SyncDialog", "Include subdirectories"))
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))

    def get_options(self):
        return {
            "two_way": self.two_way_sync_checkbox.isChecked(),
            "left_to_right": not self.two_way_sync_checkbox.isChecked(), # Assuming one-way if not two-way
            "right_to_left": False, # This logic needs to be improved if we want 3-way choice
            "include_subdirs": self.include_subdirs_checkbox.isChecked(),
            "delete": self.delete_files_checkbox.isChecked(),
            "by_content": False # This option is not in the UI, default to False
        }
