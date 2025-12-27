import os
import logging
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QTimer, QItemSelectionModel
from PyQt6.QtWidgets import QTableView, QHeaderView, QAbstractItemView, QApplication
from PyQt6.QtGui import QKeyEvent

from browser.base_view import AbstractFileView
from browser.flat_file_system_model import FlatFileSystemModel
from browser.styling_delegate import FileStyleDelegate


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
            
            # Calculate next index immediately
            current_idx = self.view.currentIndex()
            if current_idx.isValid() and current_idx.row() < self.model.rowCount() - 1:
                next_idx = self.model.index(current_idx.row() + 1, 0)
                
                def move():
                    self.view.setCurrentIndex(next_idx)
                    self.view.scrollTo(next_idx)
                
                # Use a small delay to ensure dataChanged is processed
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
