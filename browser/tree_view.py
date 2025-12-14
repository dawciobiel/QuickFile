import os
from PyQt6.QtCore import QModelIndex, Qt, QEvent
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QAbstractItemView, QHeaderView
from browser.base_view import AbstractFileView
from browser.tree_file_system_model import TreeFileSystemModel
from browser.styling_delegate import FileStyleDelegate

class TreeFileView(AbstractFileView):
    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        
        self.model = TreeFileSystemModel(settings_manager, self)
        
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setItemDelegate(FileStyleDelegate(self.view))
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setExpandsOnDoubleClick(False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self.update_view_settings()
        
        self.view.doubleClicked.connect(self.on_item_double_clicked)

    def handle_key_event(self, event: QEvent):
        key = event.key()
        if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            current_index = self.view.currentIndex()
            if current_index.isValid():
                self.on_item_double_clicked(current_index)
            return True
        elif key == Qt.Key.Key_Insert:
            self.toggle_selection()
            return True
        elif key == Qt.Key.Key_Backspace:
            self.go_up()
            return True
        return False

    def set_path(self, path, select_item_name=None):
        self.model.set_root_path(path)
        self.view.setRootIndex(QModelIndex())
        self.path_changed.emit(path)
        
        if select_item_name:
            found_index = None
            for row in range(self.model.rowCount(QModelIndex())):
                index = self.model.index(row, 0, QModelIndex())
                if self.model.fileName(index) == select_item_name:
                    found_index = index
                    break
            if found_index:
                self.view.setCurrentIndex(found_index)
                self.view.scrollTo(found_index, QAbstractItemView.ScrollHint.EnsureVisible)
            else:
                first_index = self.model.index(0, 0)
                if first_index.isValid():
                    self.view.setCurrentIndex(first_index)
                    self.view.scrollTo(first_index, QAbstractItemView.ScrollHint.EnsureVisible)
        else:
            first_index = self.model.index(0, 0)
            if first_index.isValid():
                self.view.setCurrentIndex(first_index)
                self.view.scrollTo(first_index, QAbstractItemView.ScrollHint.EnsureVisible)

    def get_current_path(self):
        return self.model.root_item.path

    def refresh(self):
        self.model.update_settings()

    def get_selected_paths(self):
        return []

    def get_current_selected_path(self):
        if self.view.currentIndex().isValid():
            return self.model.filePath(self.view.currentIndex())
        return None

    def go_up(self):
        current_path = self.get_current_path()
        parent_path = os.path.dirname(current_path)
        
        if parent_path != current_path:
            current_dir_name = os.path.basename(current_path)
            self.set_path(parent_path, select_item_name=current_dir_name)
            
    def update_view_settings(self):
        self.model.update_settings()
        header = self.view.header()
        header.setStretchLastSection(False)
        for i in range(header.count()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        show_uid = self.settings_manager.get_setting("show_uid_column", True)
        show_gid = self.settings_manager.get_setting("show_gid_column", True)
        
        self.view.setColumnHidden(4, not (show_uid or show_gid))
        self.view.setColumnHidden(5, not show_uid)
        self.view.setColumnHidden(6, not show_gid)
        
        setting_key = "tree_column_widths"
        saved_widths = self.settings_manager.get_setting(setting_key)
        if saved_widths and len(saved_widths) == header.count():
            for i, width in enumerate(saved_widths):
                if width > 0:
                    header.resizeSection(i, width)
        else:
            header.resizeSections(QHeaderView.ResizeMode.ResizeToContents)
            
        header.sectionResized.connect(self.on_header_section_resized)

    def on_header_section_resized(self, section, old_size, new_size):
        header = self.view.header()
        column_widths = [header.sectionSize(i) for i in range(header.count())]
        self.settings_manager.set_setting("tree_column_widths", column_widths)
        
    def on_item_double_clicked(self, index):
        if os.path.isdir(self.model.filePath(index)):
            if self.view.isExpanded(index):
                self.view.collapse(index)
            else:
                self.view.expand(index)

    def toggle_selection(self):
        current_index = self.view.currentIndex()
        if current_index.isValid():
            self.model.toggle_selection_by_index(current_index)
            next_row = current_index.row() + 1
            parent = current_index.parent()
            if next_row < self.model.rowCount(parent):
                next_index = self.model.index(next_row, current_index.column(), parent)
                self.view.setCurrentIndex(next_index)
