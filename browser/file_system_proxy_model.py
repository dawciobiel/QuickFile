# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pwd
import grp
import logging
from PyQt6.QtCore import QSortFilterProxyModel, Qt, QModelIndex, QCoreApplication

class FileSystemProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.update_settings()

    def update_settings(self):
        if self.settings_manager:
            self._file_permissions_display_mode = self.settings_manager.get_setting("file_permissions_display_mode", "symbolic")
            self._show_uid_column = self.settings_manager.get_setting("show_uid_column", True)
            self._show_gid_column = self.settings_manager.get_setting("show_gid_column", True)
        else:
            self._file_permissions_display_mode = "symbolic"
            self._show_uid_column = True
            self._show_gid_column = True
        logging.debug(f"Proxy settings updated: UID={self._show_uid_column}, GID={self._show_gid_column}")
        self.layoutChanged.emit()

    def columnCount(self, parent=QModelIndex()):
        return self.sourceModel().columnCount(parent) + 3

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            source_cols = self.sourceModel().columnCount()
            if section < source_cols:
                return self.sourceModel().headerData(section, orientation, role)
            
            if section == source_cols:
                return QCoreApplication.translate("FileSystemProxyModel", "Permissions")
            elif section == source_cols + 1:
                return QCoreApplication.translate("FileSystemProxyModel", "Owner")
            elif section == source_cols + 2:
                return QCoreApplication.translate("FileSystemProxyModel", "Group")
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        source_cols = self.sourceModel().columnCount()
        if index.column() < source_cols:
            source_index = self.mapToSource(index)
            return self.sourceModel().data(source_index, role)

        if role == Qt.ItemDataRole.DisplayRole:
            source_index_for_row = self.mapToSource(index.siblingAtColumn(0))
            if not source_index_for_row.isValid():
                return None

            file_path = self.sourceModel().filePath(source_index_for_row)
            if not os.path.exists(file_path):
                return None

            try:
                stat_info = os.stat(file_path)
            except OSError:
                return ""

            if index.column() == source_cols:
                if self._file_permissions_display_mode == "symbolic":
                    return self._get_file_permissions_symbolic(stat_info.st_mode)
                else:
                    return self._get_file_permissions_numeric(stat_info.st_mode)
            elif index.column() == source_cols + 1:
                return self._get_username_from_uid(stat_info.st_uid)
            elif index.column() == source_cols + 2:
                return self._get_groupname_from_gid(stat_info.st_gid)

        return None

    def filePath(self, index):
        source_index = self.mapToSource(index)
        return self.sourceModel().filePath(source_index)

    def isDir(self, index):
        source_index = self.mapToSource(index)
        return self.sourceModel().isDir(source_index)

    def fileName(self, index):
        source_index = self.mapToSource(index)
        return self.sourceModel().fileName(source_index)
        
    def index(self, path_or_row, column=0, parent=QModelIndex()):
        if isinstance(path_or_row, str):
            source_index = self.sourceModel().index(path_or_row, column)
            return self.mapFromSource(source_index)
        return super().index(path_or_row, column, parent)

    def set_file_permissions_display_mode(self, mode):
        self._file_permissions_display_mode = mode
        self.layoutChanged.emit()

    def set_show_uid_column(self, show):
        self._show_uid_column = show
        self.layoutChanged.emit()

    def set_show_gid_column(self, show):
        self._show_gid_column = show
        self.layoutChanged.emit()

    def _get_file_permissions_symbolic(self, mode):
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
