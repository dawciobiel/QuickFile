# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import sys

from PyQt6.QtWidgets import QWidget, QMessageBox, QDialog

# Add current directory to sys.path to allow importing sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from quickfile.plugins.base import SymlinkPlugin
from create_link_dialog import CreateLinkDialog
from modify_link_dialog import ModifyLinkDialog
from quickfile.app.action_logger import action_logger
from quickfile.file_operations.file_manager import FileManager, FileManagerError


class SymlinkManagerPlugin(SymlinkPlugin):

    def __init__(self):
        # This plugin will manage its own file operations for links
        self.file_manager = FileManager()

    def get_name(self) -> str:
        return "Symlink Manager"

    def get_description(self) -> str:
        return "Provides functionality to create and modify symbolic and hard links."

    def is_supported(self) -> bool:
        # Link creation is supported on POSIX systems.
        # Windows support is more complex and would require a separate plugin or logic.
        return os.name == 'posix'

    def create_link(self, source_path: str, default_link_dir: str, parent: QWidget):
        dialog = CreateLinkDialog(parent, source_path, default_link_dir)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            details = dialog.get_link_details()
            if details:
                source, link, is_hardlink = details
                try:
                    action_logger.log_action("create_link", source=source, link=link, is_hardlink=is_hardlink)
                    message = self.file_manager.create_link(source, link, is_hardlink)
                    QMessageBox.information(parent, "Success", message)
                except (FileManagerError, ValueError, FileExistsError) as e:
                    QMessageBox.critical(parent, "Error", str(e))

    def modify_link(self, link_path: str, parent: QWidget):
        if not os.path.islink(link_path):
            QMessageBox.warning(parent, "Warning", "Please select a symbolic link to modify.")
            return

        try:
            target_path = os.readlink(link_path)
        except OSError as e:
            QMessageBox.critical(parent, "Error", f"Could not read link target: {e}")
            return

        dialog = ModifyLinkDialog(parent, link_path, target_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_target = dialog.get_new_target()
            if new_target and new_target != target_path:
                try:
                    action_logger.log_action("modify_link", link=link_path, new_target=new_target)
                    message = self.file_manager.modify_symbolic_link(link_path, new_target)
                    QMessageBox.information(parent, "Success", message)
                except (FileManagerError, ValueError, FileNotFoundError) as e:
                    QMessageBox.critical(parent, "Error", str(e))
