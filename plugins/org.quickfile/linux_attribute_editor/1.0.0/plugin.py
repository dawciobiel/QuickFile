import os
import sys

from PyQt6.QtWidgets import QWidget

# Add current directory to sys.path to allow importing sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from plugins.base import AttributeEditorPlugin
from change_owner_dialog import ChangeOwnerDialog


class LinuxAttributeEditorPlugin(AttributeEditorPlugin):

    @property
    def name(self) -> str:
        return "Linux Attribute Editor"

    @property
    def description(self) -> str:
        return "A plugin to edit file/directory owner and permissions on Linux."

    def is_supported(self) -> bool:
        # This plugin is only for POSIX-compliant systems (Linux, macOS)
        return os.name == 'posix'

    def open_editor(self, path: str, parent: QWidget):
        dialog = ChangeOwnerDialog(path, parent)
        dialog.exec()
