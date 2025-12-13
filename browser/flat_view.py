import os
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import QTableView, QVBoxLayout, QAbstractItemView, QHeaderView

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
        
        self._configure_view()
        
        self.view.doubleClicked.connect(self.on_item_double_clicked)
        self.view.installEventFilter(self)

    def eventFilter(self, source, event):
        if source is self.view and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                current_index = self.view.currentIndex()
                if current_index.isValid():
                    self.on_item_double_clicked(current_index)
                return True # Event handled
            elif key == Qt.Key.Key_Home:
                first_index = self.model.index(0, 0)
                if first_index.isValid():
                    self.view.setCurrentIndex(first_index)
                return True # Event handled
            elif key == Qt.Key.Key_End:
                last_row = self.model.rowCount() - 1
                if last_row >= 0:
                    last_index = self.model.index(last_row, 0)
                    if last_index.isValid():
                        self.view.setCurrentIndex(last_index)
                return True # Event handled
            elif key == Qt.Key.Key_Insert:
                self.toggle_selection()
                return True
        
        return super().eventFilter(source, event)

    def _configure_view(self):
        header = self.view.horizontalHeader()
        self.view.verticalHeader().setDefaultSectionSize(20) # Set row height
        self.view.verticalHeader().hide() # Hide vertical header
        
        # Restore widths
        setting_key = "table_column_widths"
        saved_widths = self.settings_manager.get_setting(setting_key)
        if saved_widths and len(saved_widths) == header.count():
            for i, width in enumerate(saved_widths):
                if width > 0:
                    header.resizeSection(i, width)
        else:
            header.resizeSections(QHeaderView.ResizeMode.ResizeToContents)
            
        header.sectionResized.connect(self.on_header_section_resized)

    def on_header_section_resized(self, section, old_size, new_size):
        header = self.view.horizontalHeader()
        column_widths = [header.sectionSize(i) for i in range(header.count())]
        self.settings_manager.set_setting("table_column_widths", column_widths)

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
        
    def on_item_double_clicked(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.set_path(path)
        # else: emit signal to open file
        
    def toggle_selection(self):
        current_index = self.view.currentIndex()
        if current_index.isValid():
            self.model.toggle_selection_by_index(current_index)
            # Move to the next item
            next_row = current_index.row() + 1
            if next_row < self.model.rowCount():
                next_index = self.model.index(next_row, current_index.column())
                self.view.setCurrentIndex(next_index)
