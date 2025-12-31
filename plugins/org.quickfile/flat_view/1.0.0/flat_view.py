import datetime
import grp
import json
import logging
import os
import pwd

from PyQt6.QtCore import pyqtSignal, Qt, QModelIndex, QDir, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QTableView, QHeaderView, QAbstractItemView, QFileIconProvider

from app.settings_manager import SettingsManager
from app.translation_manager import translation_manager
from browser.abstract_file_system_model import AbstractFileSystemModel
from browser.base_view import AbstractFileView
from browser.styling_delegate import FileStyleDelegate, FileStyleRole
from utils.dialogs import show_error_message


class FlatFileSystemModel(AbstractFileSystemModel):
    def __init__(self, parent=None, show_dot_files=True, file_permissions_display_mode="symbolic", show_uid_column=True,
                 show_gid_column=True, insert_selected_items=None, settings_manager: SettingsManager = None, theme_manager=None):
        super().__init__(parent)
        self.parent_widget = parent
        self._current_path = os.path.expanduser("~")
        self._items = []
        self._icon_provider = QFileIconProvider()
        self._show_dot_files = show_dot_files
        self._file_permissions_display_mode = file_permissions_display_mode
        self._show_uid_column = show_uid_column
        self._show_gid_column = show_gid_column
        self._file_styles = {}
        self._special_type_styles = {}
        self._insert_selected_items = insert_selected_items if insert_selected_items is not None else set()
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager
        self._directory_sizes = {}
        
        if self.theme_manager:
            self.on_theme_changed(self.theme_manager.get_theme_path())
            
        self._populate_items()

    def on_theme_changed(self, theme_path):
        if not theme_path:
            return
        styles_path = os.path.join(theme_path, "file_styles.json")
        if os.path.exists(styles_path):
            try:
                with open(styles_path, 'r') as f:
                    data = json.load(f)
                    self._file_styles = data
                    self._special_type_styles = data.get("special_types", {})
                    logging.info(f"Loaded file styles from {styles_path}. Special types: {list(self._special_type_styles.keys())}")
            except Exception as e:
                logging.error(f"Failed to load file styles: {e}")
        else:
            logging.warning(f"File styles not found at {styles_path}")
            self._file_styles = {}
            self._special_type_styles = {}
        self.layoutChanged.emit()

    def set_current_path(self, path):
        if self._current_path == path:
            self.refresh()
            return
        self.beginResetModel()
        self._current_path = path
        self._directory_sizes.clear()
        self._populate_items()
        self.endResetModel()

    def refresh(self):
        self.beginResetModel()
        self._directory_sizes.clear()
        self._populate_items()
        self.endResetModel()

    def _populate_items(self):
        dot_dot_item = []
        other_items = []

        if self._current_path != QDir.rootPath():
            dot_dot_item.append(("..", os.path.dirname(self._current_path), True, False))
        
        if self._current_path == "/root":
            msg = translation_manager.translate("FlatFileSystemModel", f"Permission denied to access directory: {self._current_path}")
            show_error_message(self.parent_widget, translation_manager.translate("FlatFileSystemModel", "Permission Error"), msg)
            other_items = []

        try:
            for item_name in os.listdir(self._current_path):
                if not self._show_dot_files and item_name.startswith('.') and item_name != '..':
                    continue
                item_path = os.path.join(self._current_path, item_name)
                is_dir = os.path.isdir(item_path)
                other_items.append((item_name, item_path, is_dir, False))
            
            other_items.sort(key=lambda x: (not x[2], x[0].lower()))

        except OSError as e:
            msg = translation_manager.translate("FlatFileSystemModel", f"Permission denied to access directory: {self._current_path}")
            show_error_message(self.parent_widget, translation_manager.translate("FlatFileSystemModel", "Permission Error"), msg)
            other_items = []

        self._items = dot_dot_item + other_items

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
        base_columns = 4
        extra_columns = 0
        if self._show_uid_column or self._show_gid_column:
            extra_columns += 1
        if self._show_uid_column:
            extra_columns += 1
        if self._show_gid_column:
            extra_columns += 1
        return base_columns + extra_columns + 1

    def flags(self, index):
        default_flags = super().flags(index)
        if index.column() == 0:
            return default_flags | Qt.ItemFlag.ItemIsUserCheckable
        return default_flags

    def update_directory_size(self, path, size):
        self._directory_sizes[path] = size
        for row in range(len(self._items)):
            if self._items[row][1] == path:
                index = self.index(row, 1)
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
                break

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item_name, item_path, is_dir, is_selected = self._items[index.row()]

        if item_path in self._insert_selected_items and self.settings_manager:
            if role == Qt.ItemDataRole.ForegroundRole:
                return QColor(self.settings_manager.get_setting("insert_selection_text_color"))
            elif role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(self.settings_manager.get_setting("insert_selection_font_bold"))
                font.setItalic(self.settings_manager.get_setting("insert_selection_font_italic"))
                return font

        if role == FileStyleRole:
            # Check for special types first
            if os.path.islink(item_path):
                if "symlink" in self._special_type_styles:
                    return self._special_type_styles["symlink"]

            # Check for hardlinks (only for files)
            if not is_dir:
                try:
                    stat_info = os.stat(item_path)
                    if stat_info.st_nlink > 1:
                        if "hardlink" in self._special_type_styles:
                            return self._special_type_styles["hardlink"]
                except OSError:
                    pass

            if item_name.startswith('.'):
                if "hidden" in self._special_type_styles:
                    return self._special_type_styles["hidden"]

            # Fallback to extension-based styling
            if not is_dir:
                extension = item_name.split('.')[-1].lower()
                if extension in self._file_styles:
                    return self._file_styles[extension]
            return None

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            if item_name == "..":
                return None
            return Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return item_name
            elif index.column() == 1:
                if not is_dir:
                    try:
                        size_bytes = os.path.getsize(item_path)
                        if size_bytes < 1024: return f"{size_bytes} B"
                        elif size_bytes < 1024**2: return f"{size_bytes / 1024:.1f} KB"
                        elif size_bytes < 1024**3: return f"{size_bytes / (1024**2):.1f} MB"
                        else: return f"{size_bytes / (1024**3):.1f} GB"
                    except OSError:
                        return "N/A"
                else:
                    if item_path in self._directory_sizes:
                         size_bytes = self._directory_sizes[item_path]
                         if size_bytes < 1024: return f"{size_bytes} B"
                         elif size_bytes < 1024**2: return f"{size_bytes / 1024:.1f} KB"
                         elif size_bytes < 1024**3: return f"{size_bytes / (1024**2):.1f} MB"
                         else: return f"{size_bytes / (1024**3):.1f} GB"
                    return ""
            elif index.column() == 2:
                if is_dir:
                    return "Folder"
                else:
                    return translation_manager.translate("FlatFileSystemModel", "File")
            elif index.column() == 3:
                try:
                    mtime = os.path.getmtime(item_path)
                    return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                except OSError:
                    return "N/A"
            
            base_columns = 4
            current_col = base_columns

            if self._show_uid_column or self._show_gid_column:
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
            
            if self._show_uid_column:
                if index.column() == current_col:
                    try:
                        stat_info = os.stat(item_path)
                        return self._get_username_from_uid(stat_info.st_uid)
                    except OSError:
                        return ""
                current_col += 1
            
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
                0: translation_manager.translate("FlatFileSystemModel", "Name"),
                1: translation_manager.translate("FlatFileSystemModel", "Size"),
                2: translation_manager.translate("FlatFileSystemModel", "Type"),
                3: translation_manager.translate("FlatFileSystemModel", "Date Modified")
            }
            if section in base_headers:
                return base_headers[section]
            
            current_col = 4
            if self._show_uid_column or self._show_gid_column:
                if section == current_col:
                    return translation_manager.translate("FlatFileSystemModel", "Permissions")
                current_col += 1
            if self._show_uid_column:
                if section == current_col:
                    return translation_manager.translate("FlatFileSystemModel", "Owner")
                current_col += 1
            if self._show_gid_column:
                if section == current_col:
                    return translation_manager.translate("FlatFileSystemModel", "Group")
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
        perm = []
        perm.append('r' if (mode & 0o400) else '_')
        perm.append('w' if (mode & 0o200) else '_')
        perm.append('x' if (mode & 0o100) else '_')
        perm.append('r' if (mode & 0o040) else '_')
        perm.append('w' if (mode & 0o020) else '_')
        perm.append('x' if (mode & 0o010) else '_')
        perm.append('r' if (mode & 0o004) else '_')
        perm.append('w' if (mode & 0o002) else '_')
        perm.append('x' if (mode & 0o001) else '_')
        return "".join(perm)

    def _get_file_permissions_numeric(self, mode):
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

class FlatFileView(AbstractFileView):
    path_changed = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    insert_selection_changed = pyqtSignal()

    def __init__(self, settings_manager, theme_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.theme_manager = theme_manager
        self.insert_selected_items = set()

        self.model = FlatFileSystemModel(
            parent=self,
            show_dot_files=self.settings_manager.get_setting("showDotFiles", True),
            file_permissions_display_mode=self.settings_manager.get_setting("file_permissions_display_mode", "symbolic"),
            show_uid_column=self.settings_manager.get_setting("show_uid_column", True),
            show_gid_column=self.settings_manager.get_setting("show_gid_column", True),
            insert_selected_items=self.insert_selected_items,
            settings_manager=self.settings_manager,
            theme_manager=self.theme_manager
        )
        
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        self.delegate = FileStyleDelegate(self.view)
        self.view.setItemDelegate(self.delegate)
        
        self.layout.addWidget(self.view)
        
        self.view.doubleClicked.connect(self.on_item_double_clicked)
        
        self.theme_manager.theme_changed.connect(self.model.on_theme_changed)

    def update_view_settings(self):
        self.model.set_show_dot_files(self.settings_manager.get_setting("showDotFiles", True))
        self.model.set_file_permissions_display_mode(self.settings_manager.get_setting("file_permissions_display_mode", "symbolic"))
        self.model.set_show_uid_column(self.settings_manager.get_setting("show_uid_column", True))
        self.model.set_show_gid_column(self.settings_manager.get_setting("show_gid_column", True))
        self.configure_columns()

    def configure_columns(self):
        header = self.view.horizontalHeader()
        for i in range(self.model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 300)

    def set_path(self, path, select_item_name=None):
        self.model.set_current_path(path)
        self.path_changed.emit(path)
        self.configure_columns()

        if select_item_name:
            for row in range(self.model.rowCount()):
                index = self.model.index(row, 0)
                file_name = self.model.fileName(index)
                if file_name == select_item_name:
                    self.view.setCurrentIndex(index)
                    self.view.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
                    break
        else:
            if self.model.rowCount() > 0:
                self.view.setCurrentIndex(self.model.index(0, 0))

    def get_current_path(self):
        return self.model._current_path

    def get_selected_paths(self):
        return self.model.get_selected_paths()

    def get_current_selected_path(self):
        selected_indexes = self.view.selectionModel().selectedIndexes()
        if selected_indexes:
            return self.model.filePath(selected_indexes[0])
        return None

    def on_item_double_clicked(self, index):
        if self.model.isDir(index):
            target_path = self.model.filePath(index)
            current_path = self.get_current_path()
            
            if os.path.abspath(target_path) == os.path.dirname(os.path.abspath(current_path)):
                current_dir_name = os.path.basename(os.path.abspath(current_path))
                self.set_path(target_path, select_item_name=current_dir_name)
            else:
                self.set_path(target_path)
        else:
            self.file_selected.emit(self.model.filePath(index))

    def refresh(self):
        self.model.refresh()

    def toggle_selection(self):
        current_index = self.view.currentIndex()
        if not current_index.isValid():
            return
        
        file_path = self.model.filePath(current_index)
        if file_path in self.insert_selected_items:
            self.insert_selected_items.remove(file_path)
        else:
            self.insert_selected_items.add(file_path)
        
        self.model.dataChanged.emit(current_index, current_index)
        self.insert_selection_changed.emit()

    def get_insert_selected_paths(self):
        return list(self.insert_selected_items)
        
    def handle_key_event(self, event):
        if event.key() == Qt.Key.Key_Insert:
            self.toggle_selection()
            
            current_idx = self.view.currentIndex()
            if current_idx.isValid() and current_idx.row() < self.model.rowCount() - 1:
                next_idx = self.model.index(current_idx.row() + 1, 0)
                
                def move():
                    self.view.setCurrentIndex(next_idx)
                    self.view.scrollTo(next_idx)
                
                QTimer.singleShot(10, move)
            return True
        elif event.key() == Qt.Key.Key_Home:
            if self.model.rowCount() > 0:
                index = self.model.index(0, 0)
                self.view.setCurrentIndex(index)
                self.view.scrollToTop()
            return True
        elif event.key() == Qt.Key.Key_End:
            if self.model.rowCount() > 0:
                index = self.model.index(self.model.rowCount() - 1, 0)
                self.view.setCurrentIndex(index)
                self.view.scrollToBottom()
            return True

        return self._handle_common_key_events(event, self.view.currentIndex())
