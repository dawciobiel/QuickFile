# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import grp
import logging
import os
import pwd
import stat

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QCompleter, QGridLayout, QLineEdit, QLabel, QComboBox

from app.translation_manager import translation_manager


class ChangeOwnerDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)

        # --- Declare UI attributes for linter ---
        self.gridLayout: QGridLayout = None
        self.value_name_top: QLineEdit = None
        self.value_owner: QLabel = None
        self.value_group: QLabel = None
        self.value_size: QLabel = None
        self.value_permissions: QLabel = None
        self.owner_combo: QComboBox = None
        self.group_combo: QComboBox = None
        self.buttonBox: QDialogButtonBox = None
        # -----------------------------------------
        
        ui_path = os.path.join(os.path.dirname(__file__), "change_owner_dialog.ui")
        uic.loadUi(ui_path, self)

        # Set column stretch programmatically
        self.gridLayout.setColumnStretch(0, 2)
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.setColumnStretch(2, 1)
        
        self.path = path
        self.setWindowTitle(translation_manager.translate("ChangeOwnerDialog", "Change Owner & Group"))

        self._populate_info()
        self._populate_combos()

        self.buttonBox.accepted.connect(self.apply_changes)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "Change"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))

    def _populate_info(self):
        try:
            st = os.stat(self.path)

            self.value_name_top.setText(os.path.basename(self.path))
            self.value_name_top.setReadOnly(True)  # Ensure it's read-only
            
            owner_name = pwd.getpwuid(st.st_uid).pw_name
            self.value_owner.setText(owner_name)

            group_name = grp.getgrgid(st.st_gid).gr_name
            self.value_group.setText(group_name)

            size_str = f"{st.st_size} B"
            if st.st_size > 1024 * 1024:
                size_str = f"{st.st_size / (1024 * 1024):.2f} MB"
            elif st.st_size > 1024:
                size_str = f"{st.st_size / 1024:.2f} KB"
            self.value_size.setText(size_str)

            mode = st.st_mode
            permissions_str = f"{stat.filemode(mode)}\n{oct(mode)[-3:]}"
            self.value_permissions.setText(permissions_str)

        except (OSError, KeyError) as e:
            logging.error(f"Could not retrieve file info for {self.path}: {e}")
            self.value_name_top.setText(f"Error: {e}")

    def _populate_combos(self):
        # Populate users
        for p in pwd.getpwall():
            self.owner_combo.addItem(p.pw_name, p.pw_uid)

        # Populate groups
        for g in grp.getgrall():
            self.group_combo.addItem(g.gr_name, g.gr_gid)

        # Set current owner/group
        st = os.stat(self.path)
        current_owner_name = pwd.getpwuid(st.st_uid).pw_name
        current_group_name = grp.getgrgid(st.st_gid).gr_name
        self.owner_combo.setCurrentText(current_owner_name)
        self.group_combo.setCurrentText(current_group_name)

        # Make comboboxes filterable
        for combo in [self.owner_combo, self.group_combo]:
            combo.setEditable(True)
            combo.setInsertPolicy(combo.InsertPolicy.NoInsert)
            combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)

    def apply_changes(self):
        try:
            new_uid = self.owner_combo.currentData()
            new_gid = self.group_combo.currentData()

            # -1 means no change
            os.chown(self.path, new_uid, new_gid)

            logging.info(f"Changed owner of {self.path} to {new_uid}:{new_gid}")
            self.accept()
        except OSError as e:
            logging.error(f"Failed to change owner/group for {self.path}: {e}")
            # You might want to show a QMessageBox here
            self.reject()
