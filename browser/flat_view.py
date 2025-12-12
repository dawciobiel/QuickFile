import os
from PyQt6.QtWidgets import QTableView, QVBoxLayout, QAbstractItemView
from browser.base_view import AbstractFileView
from browser.flat_file_system_model import FlatFileSystemModel

class FlatFileView(AbstractFileView):
    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        
        self.model = FlatFileSystemModel(
            parent=self,
            show_dot_files=self.settings_manager.get_setting("showDotFiles", True),
            file_permissions_display_mode=self.settings_manager.get_setting("file_permissions_display_mode", "symbolic"),
            show_uid_column=self.settings_manager.get_setting("show_uid_column", True),
            show_gid_column=self.settings_manager.get_setting("show_gid_column", True)
        )
        
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self._configure_headers()

    def _configure_headers(self):
        header = self.view.horizontalHeader()
        # Configure header properties here if needed, e.g., resize modes

    def set_path(self, path):
        self.model.set_current_path(path)

    def get_current_path(self):
        return self.model._current_path

    def refresh(self):
        self.model.refresh()

    def get_selected_paths(self):
        return self.model.get_selected_paths()

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
        self.model.set_show_dot_files(self.settings_manager.get_setting("showDotFiles", True))
        self.model.set_file_permissions_display_mode(self.settings_manager.get_setting("file_permissions_display_mode", "symbolic"))
        self.model.set_show_uid_column(self.settings_manager.get_setting("show_uid_column", True))
        self.model.set_show_gid_column(self.settings_manager.get_setting("show_gid_column", True))
        self.refresh()
