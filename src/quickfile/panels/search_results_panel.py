# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex

class SearchResultsModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.results = []
        self.headers = ["File Path"]

    def clear_results(self):
        self.beginResetModel()
        self.results = []
        self.endResetModel()

    def add_result(self, path: str):
        row_count = len(self.results)
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        self.results.append(path)
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        return len(self.results)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.results)):
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self.results[index.row()]
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

class SearchResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.table_view = QTableView()
        self.model = SearchResultsModel()
        self.table_view.setModel(self.model)
        
        # Configure header
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Set activePanel property to true to use the same header style as active browser panels
        header.setProperty("activePanel", True)
        
        self.layout.addWidget(self.table_view)

    def clear_results(self):
        self.model.clear_results()

    def add_search_result(self, path: str):
        self.model.add_result(path)
