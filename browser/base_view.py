from PyQt6.QtWidgets import QWidget

class AbstractFileView(QWidget):
    """
    Abstract base class for file views (e.g., flat, tree).
    Defines a common interface for the FolderBrowser to interact with.
    """
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager

    def set_path(self, path):
        """Sets the current path for the view."""
        raise NotImplementedError

    def get_current_path(self):
        """Returns the current path of the view."""
        raise NotImplementedError

    def refresh(self):
        """Refreshes the content of the view."""
        raise NotImplementedError

    def get_selected_paths(self):
        """Returns a list of absolute paths for selected items."""
        raise NotImplementedError
        
    def get_current_selected_path(self):
        """Returns the single, currently focused item's path."""
        raise NotImplementedError

    def go_up(self):
        """Navigates one level up in the directory structure."""
        raise NotImplementedError

    def update_view_settings(self):
        """Applies new settings (like show_dot_files) to the view/model."""
        raise NotImplementedError
        
    def on_item_double_clicked(self, index):
        """Handles double-click on an item."""
        raise NotImplementedError
        
    def toggle_selection(self):
        """Toggles the selection of the currently focused item."""
        raise NotImplementedError
