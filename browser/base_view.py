from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QWidget

class AbstractFileView(QWidget, ABC):
    """
    Abstract base class for file views (e.g., flat, tree).
    Defines a common interface for the FolderBrowser to interact with.
    """
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager

    @abstractmethod
    def set_path(self, path):
        """Sets the current path for the view."""
        pass

    @abstractmethod
    def get_current_path(self):
        """Returns the current path of the view."""
        pass

    @abstractmethod
    def refresh(self):
        """Refreshes the content of the view."""
        pass

    @abstractmethod
    def get_selected_paths(self):
        """Returns a list of absolute paths for selected items."""
        pass
        
    @abstractmethod
    def get_current_selected_path(self):
        """Returns the single, currently focused item's path."""
        pass

    @abstractmethod
    def go_up(self):
        """Navigates one level up in the directory structure."""
        pass

    @abstractmethod
    def update_view_settings(self):
        """Applies new settings (like show_dot_files) to the view/model."""
        pass
