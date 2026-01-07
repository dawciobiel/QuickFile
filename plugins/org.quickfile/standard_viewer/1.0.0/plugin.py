import os
import sys

from PyQt6.QtWidgets import QWidget

# Add current directory to sys.path to allow importing sibling modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from plugins.base import ViewerPlugin
import file_viewer_dialog


class StandardViewerPlugin(ViewerPlugin):

    def __init__(self):
        # Keep track of open viewers to avoid creating duplicates for the same file
        self.open_viewers = {}

    @property
    def name(self) -> str:
        return "Standard File Viewer"

    @property
    def description(self) -> str:
        return "A built-in viewer for text files and simple images."

    def can_view(self, file_path: str) -> bool:
        # For now, let's say it can view any file.
        # The dialog itself will handle binary/unsupported files.
        return os.path.isfile(file_path)

    def view_file(self, file_path: str, theme_manager=None, parent: QWidget = None, *args, **kwargs):
        # If a viewer for this file is already open, just bring it to the front
        if file_path in self.open_viewers and not self.open_viewers[file_path].isHidden():
            viewer = self.open_viewers[file_path]
            viewer.raise_()
            viewer.activateWindow()
            return

        # Ensure theme_manager and parent are correctly passed, even with *args, **kwargs
        viewer = file_viewer_dialog.FileViewerWindow(file_path, theme_manager, parent)

        # When the window is closed, remove it from our tracking dictionary
        viewer.closed.connect(lambda: self.open_viewers.pop(file_path, None))

        self.open_viewers[file_path] = viewer
        viewer.show()
        viewer.raise_()
        viewer.activateWindow()
