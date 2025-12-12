import os
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QAbstractItemView, QHeaderView
from browser.base_view import AbstractFileView
from browser.tree_file_system_model import TreeFileSystemModel

class TreeFileView(AbstractFileView):
    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        
        self.model = TreeFileSystemModel(settings_manager, self)
        
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setExpandsOnDoubleClick(False) # We handle this manually
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self.update_view_settings() # Apply initial settings

    def set_path(self, path):
        self.model.set_root_path(path)
        self.view.setRootIndex(self.model.index(0, 0, QModelIndex()))

    def get_current_path(self):
        return self.model.root_item.path

    def refresh(self):
        self.model.update_settings()

    def get_selected_paths(self):
        indexes = self.view.selectionModel().selectedRows()
        return [self.model.filePath(index) for index in indexes]

    def get_current_selected_path(self):
        if self.view.currentIndex().isValid():
            return self.model.filePath(self.view.currentIndex())
        return None

    def go_up(self):
        current_path = self.get_current_path()
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path:
            self.set_path(parent_path)

    def update_view_settings(self):
        self.model.update_settings()
        header = self.view.header()
        header.setStretchLastSection(False)
        for i in range(header.count()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        show_uid = self.settings_manager.get_setting("show_uid_column", True)
        show_gid = self.settings_manager.get_setting("show_gid_column", True)
        
        # Columns: 0:Name, 1:Size, 2:Type, 3:Date, 4:Perms, 5:Owner, 6:Group
        self.view.setColumnHidden(4, not (show_uid or show_gid))
        self.view.setColumnHidden(5, not show_uid)
        self.view.setColumnHidden(6, not show_gid)
        
        # Restore widths
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
