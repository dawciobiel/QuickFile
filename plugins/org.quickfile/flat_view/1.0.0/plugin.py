import os
import sys
from PyQt6.QtWidgets import QWidget

# Add current directory to sys.path to allow importing sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from plugins.base import ViewModePlugin
from flat_view import FlatFileView

class FlatViewPlugin(ViewModePlugin):
    
    @property
    def name(self) -> str:
        return "Flat View"

    @property
    def description(self) -> str:
        return "A classic flat, two-column file system view."

    @property
    def view_mode_name(self) -> str:
        return "flat"

    def create_view_widget(self, parent: QWidget) -> QWidget:
        # Note: The FlatFileView expects settings_manager and theme_manager.
        # The parent (FolderBrowser) will need to provide these.
        # This is a simplification for now.
        # A better approach would be to pass a context object.
        if hasattr(parent, 'settings_manager') and hasattr(parent, 'theme_manager'):
            return FlatFileView(parent.settings_manager, parent.theme_manager, parent)
        else:
            # Fallback or error
            raise ValueError("Parent widget for FlatFileView must have settings_manager and theme_manager attributes.")
