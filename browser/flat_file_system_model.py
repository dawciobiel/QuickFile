import logging # Added logging import
import os
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDir, QCoreApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileIconProvider
from utils.dialogs import show_error_message # Dodano import

class FlatFileSystemModel(QAbstractTableModel):
    def __init__(self, parent=None, show_dot_files=True):
        super().__init__(parent)
        self.parent_widget = parent # Store the parent widget
        self._current_path = os.path.expanduser("~")
        self._items = [] # Stores (name, path, is_dir, is_selected) tuples
        self._icon_provider = QFileIconProvider()
        self._show_dot_files = show_dot_files # New setting
        logging.debug(f"FlatFileSystemModel.__init__ called. Initial show_dot_files: {self._show_dot_files}")
        self._populate_items()

    def set_current_path(self, path):
        if self._current_path == path:
            return

        self.beginResetModel()
        self._current_path = path
        self._populate_items()
        self.endResetModel()

    def _populate_items(self):
        logging.debug(f"FlatFileSystemModel._populate_items called. Current _show_dot_files: {self._show_dot_files}")
        dot_dot_item = []
        other_items = []

        if self._current_path != QDir.rootPath():
            # Keep ".." separate
            dot_dot_item.append(("..", os.path.dirname(self._current_path), True, False))
        
        # Prevent listing /root directory directly due to permission issues
        if self._current_path == "/root":
            msg = QCoreApplication.translate("FlatFileSystemModel", f"Permission denied to access directory: {self._current_path}")
            logging.warning(f"Skipping listing of /root directory due to permission restrictions.")
            show_error_message(self.parent_widget, QCoreApplication.translate("FlatFileSystemModel", "Permission Error"), msg)
            self._items = dot_dot_item # Only show ".."
            self.endResetModel() # Ensure model is reset
            return # Exit early to prevent further processing

        try:
            for item_name in os.listdir(self._current_path):
                # Apply dot file filtering
                if not self._show_dot_files and item_name.startswith('.') and item_name != '..':
                    logging.debug(f"Filtering out dot file: {item_name} (show_dot_files is False).")
                    continue
                item_path = os.path.join(self._current_path, item_name)
                is_dir = os.path.isdir(item_path)
                other_items.append((item_name, item_path, is_dir, False))
            
            # Sort only the other items
            other_items.sort(key=lambda x: (not x[2], x[0].lower()))

        except OSError as e:
            msg = QCoreApplication.translate("FlatFileSystemModel", f"Permission denied to access directory: {self._current_path}") # Define msg
            logging.error(f"Permission error accessing {self._current_path}: {e}")
            show_error_message(self.parent_widget, QCoreApplication.translate("FlatFileSystemModel", "Permission Error"), msg)
            other_items = []

        # Combine the lists, with ".." always first
        self._items = dot_dot_item + other_items
        logging.debug(f"FlatFileSystemModel._populate_items finished. Total items: {len(self._items)}")

    def set_show_dot_files(self, new_dot_files_state):
        logging.debug(f"FlatFileSystemModel.set_show_dot_files called. New value (param): {new_dot_files_state}, Current internal _show_dot_files: {self._show_dot_files}")
        if self._show_dot_files == new_dot_files_state:
            logging.debug("FlatFileSystemModel.set_show_dot_files: Internal value is the same as new value, returning.")
            return
        self._show_dot_files = new_dot_files_state
        self.beginResetModel()
        self._populate_items()
        self.endResetModel()
        logging.debug("FlatFileSystemModel finished resetting model.")

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent=QModelIndex()):
        return 4 # Name, Size, Type, Selected (hidden state)

    def flags(self, index):
        default_flags = super().flags(index)
        if index.column() == 0:
            return default_flags | Qt.ItemFlag.ItemIsUserCheckable
        return default_flags

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item_name, item_path, is_dir, is_selected = self._items[index.row()]

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            if item_name == "..": # ".." should not be checkable
                return None
            return Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return item_name
            elif index.column() == 1: # Placeholder for size
                if not is_dir:
                    try:
                        size_bytes = os.path.getsize(item_path)
                        # Convert to human-readable format
                        if size_bytes < 1024:
                            return f"{size_bytes} B"
                        elif size_bytes < 1024**2:
                            return f"{size_bytes / 1024:.1f} KB"
                        elif size_bytes < 1024**3:
                            return f"{size_bytes / (1024**2):.1f} MB"
                        else:
                            return f"{size_bytes / (1024**3):.1f} GB"
                    except OSError:
                        return "N/A"
                return "" # Directories don't have size in this column
            elif index.column() == 2: # Placeholder for type
                if is_dir:
                    return "Folder"
                else:
                    return QCoreApplication.translate("FlatFileSystemModel", "File") # Get extension
            return None

        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == 0:
                if item_name == "..":
                    return self._icon_provider.icon(QFileIconProvider.IconType.Folder) # Using generic folder icon for ".."
                if is_dir:
                    return self._icon_provider.icon(QFileIconProvider.IconType.Folder)
                else:
                    return self._icon_provider.icon(QFileIconProvider.IconType.File)
            return None
        
        elif role == Qt.ItemDataRole.UserRole: # For internal data like full path and is_dir status
            return (item_path, is_dir)

        return None

    def setData(self, index, value, role):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return False

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            # Do not allow checking ".."
            if self._items[index.row()][0] == "..":
                return False

            current_item = self._items[index.row()]
            self._items[index.row()] = (current_item[0], current_item[1], current_item[2], value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
        
        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return QCoreApplication.translate("FlatFileSystemModel", "Name")
            elif section == 1:
                return QCoreApplication.translate("FlatFileSystemModel", "Size")
            elif section == 2:
                return QCoreApplication.translate("FlatFileSystemModel", "Type")
            # No header for column 3, it's hidden
        return None

    def filePath(self, index):
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()][1] # Return the full path
        return None

    def isDir(self, index):
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()][2] # Return is_dir status
        return False

    def fileName(self, index):
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()][0] # Return the item name
        return None

    def get_selected_paths(self):
        """Returns a list of paths for all items marked as selected."""
        return [item[1] for item in self._items if item[3] and item[0] != ".."] # item[1] is path, item[3] is is_selected

    def toggle_selection_by_index(self, index):
        """Toggles the selection state for the item at the given index."""
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return

        # We trigger the setData logic by faking a check state change event
        current_state = self.data(index, Qt.ItemDataRole.CheckStateRole)
        if current_state is None: # For ".." item
            return
            
        new_check_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
        self.setData(index, new_check_state, Qt.ItemDataRole.CheckStateRole)