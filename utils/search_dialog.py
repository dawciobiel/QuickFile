# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QFileDialog
from app.translation_manager import translation_manager
from utils.resource_path import get_resource_path

class SearchDialog(QDialog):
    def __init__(self, parent, start_path):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/search_dialog.ui"), self)
        
        self.startPathEdit.setText(start_path)
        
        self._connect_signals()
        self._translate_ui()
        
        # Set focus to file name input
        self.fileNameEdit.setFocus()

    def _connect_signals(self):
        self.searchButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        self.browsePathButton.clicked.connect(self._browse_path)
        
        # Enable/disable controls based on checkboxes
        self.dateFromCheckbox.toggled.connect(self.dateFromEdit.setEnabled)
        self.dateToCheckbox.toggled.connect(self.dateToEdit.setEnabled)
        self.sizeFromCheckbox.toggled.connect(self.sizeFromSpinBox.setEnabled)
        self.sizeFromCheckbox.toggled.connect(self.sizeFromUnitCombo.setEnabled)
        self.sizeToCheckbox.toggled.connect(self.sizeToSpinBox.setEnabled)
        self.sizeToCheckbox.toggled.connect(self.sizeToUnitCombo.setEnabled)
        
        # Permissions
        self.permissionsCheckbox.toggled.connect(self._toggle_permissions)

    def _toggle_permissions(self, checked):
        self.permOwnerEdit.setEnabled(checked)
        self.permGroupEdit.setEnabled(checked)
        self.permOthersEdit.setEnabled(checked)
        self.suidCheckbox.setEnabled(checked)
        self.sgidCheckbox.setEnabled(checked)
        self.stickyCheckbox.setEnabled(checked)

    def _translate_ui(self):
        self.setWindowTitle(translation_manager.translate("SearchDialog", "Advanced Search"))
        self.searchButton.setText(translation_manager.translate("Buttons", "Search"))
        self.cancelButton.setText(translation_manager.translate("Buttons", "Cancel"))
        # Add more translations as needed

    def _browse_path(self):
        directory = QFileDialog.getExistingDirectory(self, translation_manager.translate("SearchDialog", "Select Directory"), self.startPathEdit.text())
        if directory:
            self.startPathEdit.setText(directory)

    def get_query(self):
        # For now, we construct a simple query string based on file name
        # In the future, we will return a complex dictionary with all criteria
        return self.fileNameEdit.text()

    def get_options(self):
        # Return all search options
        return {
            "file_name": self.fileNameEdit.text(),
            "file_name_case_sensitive": self.fileNameCaseSensitiveCheckbox.isChecked(),
            "extension": self.extensionEdit.text(),
            "extension_case_sensitive": self.extensionCaseSensitiveCheckbox.isChecked(),
            "start_path": self.startPathEdit.text(),
            "exclude_paths": self.excludePathsEdit.toPlainText().splitlines(),
            "permissions_enabled": self.permissionsCheckbox.isChecked(),
            "perm_owner": self.permOwnerEdit.text(),
            "perm_group": self.permGroupEdit.text(),
            "perm_others": self.permOthersEdit.text(),
            "suid": self.suidCheckbox.isChecked(),
            "sgid": self.sgidCheckbox.isChecked(),
            "sticky": self.stickyCheckbox.isChecked(),
            "plugin_id": "org.quickfile.search_standard" # Dodano plugin_id
            # Add other attributes here later
        }
