import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTreeView, QHeaderView

from browser.base_view import AbstractFileView
from browser.tree_file_system_model import TreeFileSystemModel
from browser.styling_delegate import FileStyleDelegate


class TreeFileView(AbstractFileView):
    path_changed = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    insert_selection_changed = pyqtSignal()

    def __init__(self, settings_manager, theme_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.theme_manager = theme_manager
        self.insert_selected_items = set()

        self.model = TreeFileSystemModel(
            settings_manager=self.settings_manager,
            insert_selected_items=self.insert_selected_items,
            theme_manager=self.theme_manager
        )
        
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        
        self.delegate = FileStyleDelegate(self.view)
        self.view.setItemDelegate(self.delegate)
        
        self.layout.addWidget(self.view)
        
        self.view.doubleClicked.connect(self.on_item_double_clicked)
        
        self.theme_manager.theme_changed.connect(self.model.on_theme_changed)

    def update_view_settings(self):
        self.model.update_settings()
        self.configure_columns()

    def configure_columns(self):
        header = self.view.header()
        for i in range(self.model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        # Give the 'Name' column a larger initial width
        header.resizeSection(0, 300)

    def set_path(self, path, select_item_name=None):
        self.model.set_root_path(path)
        self.path_changed.emit(path)
        self.configure_columns()

    def get_current_path(self):
        return self.model.root_item.path

    def get_selected_paths(self):
        # Tree view selection is more complex, for now, we return the current item
        return [self.get_current_selected_path()]

    def get_current_selected_path(self):
        selected_indexes = self.view.selectionModel().selectedIndexes()
        if selected_indexes:
            return self.model.filePath(selected_indexes[0])
        return None

    def on_item_double_clicked(self, index):
        if not self.model.isDir(index):
            self.file_selected.emit(self.model.filePath(index))

    def refresh(self):
        self.model.update_settings()

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
        # For now, just pass to common handler
        return self._handle_common_key_events(event, self.view.currentIndex())
