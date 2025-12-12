import os
import pwd
import grp
import logging
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from app.translation_manager import translation_manager # Import our new manager

class TreeItem:
    def __init__(self, path, parent=None):
        self.path = path
        self.parent = parent
        self.children = []
        self.is_populated = False
        self.is_marked = False

    def child(self, row):
        return self.children[row]

    def childCount(self):
        return len(self.children)

    def columnCount(self):
        return 7 # Name, Size, Type, Date Modified, Permissions, Owner, Group

    def data(self, column):
        if column == 0:
            return os.path.basename(self.path)
        
        try:
            stat_info = os.stat(self.path)
        except (OSError, FileNotFoundError):
            return None

        if column == 1: # Size
            if os.path.isdir(self.path):
                return ""
            size = stat_info.st_size
            if size < 1024: return f"{size} B"
            if size < 1024**2: return f"{size/1024:.1f} KB"
            if size < 1024**3: return f"{size/1024**2:.1f} MB"
            return f"{size/1024**3:.1f} GB"
        elif column == 2: # Type
            return "Folder" if os.path.isdir(self.path) else "File"
        elif column == 3: # Date Modified
            from datetime import datetime
            return datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        elif column == 4: # Permissions
            mode = stat_info.st_mode
            perm = []
            perm.append('r' if (mode & 0o400) else '-')
            perm.append('w' if (mode & 0o200) else '-')
            perm.append('x' if (mode & 0o100) else '-')
            perm.append('r' if (mode & 0o040) else '-')
            perm.append('w' if (mode & 0o020) else '-')
            perm.append('x' if (mode & 0o010) else '-')
            perm.append('r' if (mode & 0o004) else '-')
            perm.append('w' if (mode & 0o002) else '-')
            perm.append('x' if (mode & 0o001) else '-')
            return "".join(perm)
        elif column == 5: # Owner
            try:
                return pwd.getpwuid(stat_info.st_uid).pw_name
            except KeyError:
                return str(stat_info.st_uid)
        elif column == 6: # Group
            try:
                return grp.getgrgid(stat_info.st_gid).gr_name
            except KeyError:
                return str(stat_info.st_gid)
        return None

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def populate(self, show_hidden):
        if self.is_populated:
            return
        self.is_populated = True
        self.children = []
        try:
            for filename in sorted(os.listdir(self.path), key=str.lower):
                if not show_hidden and filename.startswith('.'):
                    continue
                child_path = os.path.join(self.path, filename)
                self.children.append(TreeItem(child_path, self))
        except OSError:
            pass

class TreeFileSystemModel(QAbstractItemModel):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.root_item = TreeItem(self.settings_manager.get_setting("leftPanelPath", os.path.expanduser("~")))
        self.update_settings()

    def update_settings(self):
        self.show_hidden = self.settings_manager.get_setting("showDotFiles", True)
        self.beginResetModel()
        self.root_item.is_populated = False
        self.root_item.populate(self.show_hidden)
        self.endResetModel()

    def set_root_path(self, path):
        self.beginResetModel()
        self.root_item = TreeItem(path)
        self.root_item.populate(self.show_hidden)
        self.endResetModel()

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = parent.internalPointer() if parent.isValid() else self.root_item
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent
        if parent_item == self.root_item:
            return QModelIndex()
        if parent_item is None:
            return QModelIndex()
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=QModelIndex()):
        parent_item = parent.internalPointer() if parent.isValid() else self.root_item
        if os.path.isdir(parent_item.path) and not parent_item.is_populated:
            parent_item.populate(self.show_hidden)
        return parent_item.childCount()

    def columnCount(self, parent=QModelIndex()):
        return 7

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        item = index.internalPointer()
        
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            return Qt.CheckState.Checked if item.is_marked else Qt.CheckState.Unchecked
            
        if role == Qt.ItemDataRole.DisplayRole:
            value = item.data(index.column())
            return value
            
        return None

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            item = index.internalPointer()
            item.is_marked = (value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
        return super().setData(index, value, role)

    def flags(self, index):
        base_flags = super().flags(index)
        if index.column() == 0:
            return base_flags | Qt.ItemFlag.ItemIsUserCheckable
        return base_flags

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            headers = {
                0: translation_manager.translate("TreeFileSystemModel", "Name"),
                1: translation_manager.translate("TreeFileSystemModel", "Size"),
                2: translation_manager.translate("TreeFileSystemModel", "Type"),
                3: translation_manager.translate("TreeFileSystemModel", "Date Modified"),
                4: translation_manager.translate("TreeFileSystemModel", "Permissions"),
                5: translation_manager.translate("TreeFileSystemModel", "Owner"),
                6: translation_manager.translate("TreeFileSystemModel", "Group")
            }
            return headers.get(section, None)
        return None

    def filePath(self, index):
        if not index.isValid():
            return ""
        return index.internalPointer().path

    def toggle_selection_by_index(self, index):
        if not index.isValid():
            return
        
        item = index.internalPointer()
        new_check_state = Qt.CheckState.Unchecked if item.is_marked else Qt.CheckState.Checked
        self.setData(index, new_check_state, Qt.ItemDataRole.CheckStateRole)
