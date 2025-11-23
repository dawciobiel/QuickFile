import os
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDir
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileIconProvider

class FlatFileSystemModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = os.path.expanduser("~")
        self._items = [] # Stores (name, path, is_dir) tuples
        self._icon_provider = QFileIconProvider()
        self._populate_items()

    def set_current_path(self, path):
        if self._current_path == path:
            return

        self.beginResetModel()
        self._current_path = path
        self._populate_items()
        self.endResetModel()

    def _populate_items(self):
        self._items = []
        if self._current_path != QDir.rootPath():
            # Add ".." entry
            self._items.append(("..", os.path.dirname(self._current_path), True))
        
        try:
            for item_name in os.listdir(self._current_path):
                item_path = os.path.join(self._current_path, item_name)
                is_dir = os.path.isdir(item_path)
                self._items.append((item_name, item_path, is_dir))
            
            # Sort items: directories first, then files, both alphabetically
            self._items.sort(key=lambda x: (not x[2], x[0].lower()))

        except OSError:
            # Handle permission errors or invalid paths
            self._items = [] # Clear items if path is inaccessible

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent=QModelIndex()):
        return 3 # Name, Size, Type (or similar columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item_name, item_path, is_dir = self._items[index.row()]

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
                    return os.path.splitext(item_name)[1].lstrip('.') or "File" # Get extension
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

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return "Nazwa"
            elif section == 1:
                return "Rozmiar"
            elif section == 2:
                return "Typ"
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
