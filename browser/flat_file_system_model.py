import logging
import os
import datetime
import pwd # Import for UID to username conversion
import grp # Import for GID to groupname conversion
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDir, QCoreApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileIconProvider
from utils.dialogs import show_error_message

class FlatFileSystemModel(QAbstractTableModel):
    def __init__(self, parent=None, show_dot_files=True, file_permissions_display_mode="symbolic", show_uid_column=True, show_gid_column=True):
        super().__init__(parent)
        self.parent_widget = parent
        self._current_path = os.path.expanduser("~")
        self._items = []
        self._icon_provider = QFileIconProvider()
        self._show_dot_files = show_dot_files
        self._file_permissions_display_mode = file_permissions_display_mode
        self._show_uid_column = show_uid_column
        self._show_gid_column = show_gid_column
        logging.debug(f"FlatFileSystemModel.__init__ called. Initial show_dot_files: {self._show_dot_files}")
        self._populate_items()

    def set_current_path(self, path):
        if self._current_path == path:
            self.refresh()
            return
        self.beginResetModel()
        self._current_path = path
        self._populate_items()
        self.endResetModel()

    def refresh(self):
        """Explicitly refreshes the model's data."""
        self.beginResetModel()
        self._populate_items()
        self.endResetModel()

    def _populate_items(self):
        logging.debug(f"FlatFileSystemModel._populate_items called. Current _show_dot_files: {self._show_dot_files}")
        dot_dot_item = []
        other_items = []

        if self._current_path != QDir.rootPath():
            dot_dot_item.append(("..", os.path.dirname(self._current_path), True, False))
        
        if self._current_path == "/root":
            msg = QCoreApplication.translate("FlatFileSystemModel", f"Permission denied to access directory: {self._current_path}")
            logging.warning(f"Skipping listing of /root directory due to permission restrictions.")
            show_error_message(self.parent_widget, QCoreApplication.translate("FlatFileSystemModel", "Permission Error"), msg)
            self._items = dot_dot_item
            return

        try:
            for item_name in os.listdir(self._current_path):
                if not self._show_dot_files and item_name.startswith('.') and item_name != '..':
                    logging.debug(f"Filtering out dot file: {item_name} (show_dot_files is False).")
                    continue
                item_path = os.path.join(self._current_path, item_name)
                is_dir = os.path.isdir(item_path)
                other_items.append((item_name, item_path, is_dir, False))
            
            other_items.sort(key=lambda x: (not x[2], x[0].lower()))

        except OSError as e:
            msg = QCoreApplication.translate("FlatFileSystemModel", f"Permission denied to access directory: {self._current_path}")
            logging.error(f"Permission error accessing {self._current_path}: {e}")
            show_error_message(self.parent_widget, QCoreApplication.translate("FlatFileSystemModel", "Permission Error"), msg)
            other_items = []

        self._items = dot_dot_item + other_items
        logging.debug(f"FlatFileSystemModel._populate_items finished. Total items: {len(self._items)}")

    def set_show_dot_files(self, new_dot_files_state):
        if self._show_dot_files == new_dot_files_state:
            return
        self._show_dot_files = new_dot_files_state
        self.beginResetModel()
        self._populate_items()
        self.endResetModel()

    def set_file_permissions_display_mode(self, mode):
        if self._file_permissions_display_mode != mode:
            self._file_permissions_display_mode = mode
            self.layoutChanged.emit()

    def set_show_uid_column(self, show):
        if self._show_uid_column != show:
            self._show_uid_column = show
            self.layoutChanged.emit()

    def set_show_gid_column(self, show):
        if self._show_gid_column != show:
            self._show_gid_column = show
            self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def columnCount(self, parent=QModelIndex()):
        base_columns = 4  # Name, Size, Type, Date Modified
        extra_columns = 0
        if self._show_uid_column or self._show_gid_column:
            extra_columns += 1 # Permissions column
        if self._show_uid_column:
            extra_columns += 1
        if self._show_gid_column:
            extra_columns += 1
        return base_columns + extra_columns + 1 # +1 for the hidden selection column

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
            if item_name == "..":
                return None
            return Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return item_name
            elif index.column() == 1:  # Size
                if not is_dir:
                    try:
                        size_bytes = os.path.getsize(item_path)
                        if size_bytes < 1024: return f"{size_bytes} B"
                        elif size_bytes < 1024**2: return f"{size_bytes / 1024:.1f} KB"
                        elif size_bytes < 1024**3: return f"{size_bytes / (1024**2):.1f} MB"
                        else: return f"{size_bytes / (1024**3):.1f} GB"
                    except OSError:
                        return "N/A"
                return ""
            elif index.column() == 2:  # Type
                if is_dir:
                    return "Folder"
                else:
                    return QCoreApplication.translate("FlatFileSystemModel", "File")
            elif index.column() == 3:  # Date Modified
                try:
                    mtime = os.path.getmtime(item_path)
                    return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                except OSError:
                    return "N/A"
            
            # New columns
            base_columns = 4
            current_col = base_columns

            # Permissions column
            if self._show_uid_column or self._show_gid_column: # Display permissions if owner/group are shown
                if index.column() == current_col:
                    try:
                        stat_info = os.stat(item_path)
                        if self._file_permissions_display_mode == "symbolic":
                            return self._get_file_permissions_symbolic(stat_info.st_mode)
                        else:
                            return self._get_file_permissions_numeric(stat_info.st_mode)
                    except OSError:
                        return ""
                current_col += 1
            
            # UID column
            if self._show_uid_column:
                if index.column() == current_col:
                    try:
                        stat_info = os.stat(item_path)
                        return self._get_username_from_uid(stat_info.st_uid)
                    except OSError:
                        return ""
                current_col += 1
            
            # GID column
            if self._show_gid_column:
                if index.column() == current_col:
                    try:
                        stat_info = os.stat(item_path)
                        return self._get_groupname_from_gid(stat_info.st_gid)
                    except OSError:
                        return ""
                current_col += 1

            return None

        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == 0:
                if item_name == "..":
                    return self._icon_provider.icon(QFileIconProvider.IconType.Folder)
                if is_dir:
                    return self._icon_provider.icon(QFileIconProvider.IconType.Folder)
                else:
                    return self._icon_provider.icon(QFileIconProvider.IconType.File)
            return None
        
        elif role == Qt.ItemDataRole.UserRole:
            return (item_path, is_dir)

        return None

    def setData(self, index, value, role):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return False

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            if self._items[index.row()][0] == "..":
                return False
            current_item = self._items[index.row()]
            self._items[index.row()] = (current_item[0], current_item[1], current_item[2], value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
        
        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            base_headers = {
                0: QCoreApplication.translate("FlatFileSystemModel", "Name"),
                1: QCoreApplication.translate("FlatFileSystemModel", "Size"),
                2: QCoreApplication.translate("FlatFileSystemModel", "Type"),
                3: QCoreApplication.translate("FlatFileSystemModel", "Date Modified")
            }
            if section in base_headers:
                return base_headers[section]
            
            current_col = 4
            if self._show_uid_column or self._show_gid_column:
                if section == current_col:
                    return QCoreApplication.translate("FlatFileSystemModel", "Permissions")
                current_col += 1
            if self._show_uid_column:
                if section == current_col:
                    return QCoreApplication.translate("FlatFileSystemModel", "Owner")
                current_col += 1
            if self._show_gid_column:
                if section == current_col:
                    return QCoreApplication.translate("FlatFileSystemModel", "Group")
                current_col += 1
        return None

    def filePath(self, index):
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()][1]
        return None

    def isDir(self, index):
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()][2]
        return False

    def fileName(self, index):
        if index.isValid() and 0 <= index.row() < len(self._items):
            return self._items[index.row()][0]
        return None

    def get_selected_paths(self):
        return [item[1] for item in self._items if item[3] and item[0] != ".."]

    def toggle_selection_by_index(self, index):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return
        current_state = self.data(index, Qt.ItemDataRole.CheckStateRole)
        if current_state is None:
            return
        new_check_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
        self.setData(index, new_check_state, Qt.ItemDataRole.CheckStateRole)

    def _get_file_permissions_symbolic(self, mode):
        # Helper to convert numeric permissions to symbolic (rwx)
        perm = []
        # Owner
        perm.append('r' if (mode & 0o400) else '_')
        perm.append('w' if (mode & 0o200) else '_')
        perm.append('x' if (mode & 0o100) else '_')
        # Group
        perm.append('r' if (mode & 0o040) else '_')
        perm.append('w' if (mode & 0o020) else '_')
        perm.append('x' if (mode & 0o010) else '_')
        # Others
        perm.append('r' if (mode & 0o004) else '_')
        perm.append('w' if (mode & 0o002) else '_')
        perm.append('x' if (mode & 0o001) else '_')
        return "".join(perm)

    def _get_file_permissions_numeric(self, mode):
        # Helper to convert numeric permissions to octal (755)
        return oct(mode)[-3:]

    def _get_username_from_uid(self, uid):
        try:
            return pwd.getpwuid(uid).pw_name
        except KeyError:
            return str(uid)

    def _get_groupname_from_gid(self, gid):
        try:
            return grp.getgrgid(gid).gr_name
        except KeyError:
            return str(gid)
