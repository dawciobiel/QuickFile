from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QAbstractItemView, QVBoxLayout

class AbstractFileView(QWidget):
    path_changed = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    insert_selection_changed = pyqtSignal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # These attributes should be initialized by subclasses
        self.view: QAbstractItemView | None = None
        self.model = None 

    def set_path(self, path):
        raise NotImplementedError

    def get_current_path(self):
        raise NotImplementedError

    def get_selected_paths(self):
        raise NotImplementedError

    def get_current_selected_path(self):
        raise NotImplementedError

    def refresh(self):
        raise NotImplementedError

    def go_up(self):
        import os
        current_path = self.get_current_path()
        parent_path = os.path.dirname(current_path)
        if os.path.exists(parent_path):
            self.set_path(parent_path)

    def toggle_selection(self):
        raise NotImplementedError

    def get_insert_selected_paths(self):
        return []

    def clear_selection(self):
        pass

    def _handle_common_key_events(self, event, current_index):
        if not self.view or not self.model:
            return False

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if current_index.isValid():
                # Emit doubleClicked signal to handle navigation or file opening
                self.view.doubleClicked.emit(current_index)
                return True

        return False
