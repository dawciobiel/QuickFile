import abc
import os

from PyQt6.QtCore import QEvent, pyqtSignal, Qt, QModelIndex
from PyQt6.QtWidgets import QWidget


# This metaclass inherits from the metaclasses of both QWidget and ABC.
# This resolves the metaclass conflict when a class needs to be both a QWidget and an ABC.
class AbstractViewMeta(type(QWidget), abc.ABCMeta):
    pass

class AbstractFileView(QWidget, metaclass=AbstractViewMeta):
    """
    Abstract base class for file views (e.g., flat, tree).
    Defines a common interface (contract) that all file views must implement.
    """
    path_changed = pyqtSignal(str)
    file_selected = pyqtSignal(str)

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager

    @abc.abstractmethod
    def set_path(self, path, select_item_name=None):
        """Sets the current path for the view."""
        pass

    @abc.abstractmethod
    def get_current_path(self):
        """Returns the current path of the view."""
        pass

    @abc.abstractmethod
    def refresh(self):
        """Refreshes the content of the view."""
        pass

    @abc.abstractmethod
    def get_selected_paths(self):
        """Returns a list of absolute paths for selected items."""
        pass
        
    @abc.abstractmethod
    def get_current_selected_path(self):
        """Returns the single, currently focused item's path."""
        pass

    def go_up(self):
        """Navigates one level up in the directory structure."""
        current_path = self.get_current_path()
        parent_path = os.path.dirname(current_path)
        
        if parent_path != current_path:
            current_dir_name = os.path.basename(current_path)
            self.set_path(parent_path, select_item_name=current_dir_name)

    @abc.abstractmethod
    def update_view_settings(self):
        """Applies new settings (like show_dot_files) to the view/model."""
        pass
        
    @abc.abstractmethod
    def on_item_double_clicked(self, index: QModelIndex):
        """Handles double-click on an item."""
        pass
        
    @abc.abstractmethod
    def toggle_selection(self):
        """Toggles the selection of the currently focused item."""
        pass

    def _handle_common_key_events(self, event: QEvent, current_index: QModelIndex):
        """
        Handles common key press events for file views.
        Returns True if the event was handled, False otherwise.
        """
        key = event.key()
        if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            if current_index.isValid():
                self.on_item_double_clicked(current_index)
            return True
        elif key == Qt.Key.Key_Insert:
            self.toggle_selection()
            return True
        return False

    @abc.abstractmethod
    def handle_key_event(self, event: QEvent):
        """Handles key press events specific to this view."""
        pass
