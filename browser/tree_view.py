import os

# import logging # Removed logging
from PyQt6.QtCore import QModelIndex, Qt, QEvent
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QAbstractItemView, QHeaderView

from app.theme_manager import ThemeManager  # Import ThemeManager
from browser.base_view import AbstractFileView
from browser.styling_delegate import FileStyleDelegate
from browser.tree_file_system_model import TreeFileSystemModel


class TreeFileView(AbstractFileView):
    def __init__(self, settings_manager, theme_manager: ThemeManager, parent=None):
        super().__init__(settings_manager, parent)
        self.theme_manager = theme_manager # Store theme_manager

        self._insert_selected_items = set()  # This will now store file paths (strings)

        self.model = TreeFileSystemModel(
            settings_manager,
            self,
            insert_selected_items=self._insert_selected_items  # Pass the set to the model
        )
        
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
        # logging.critical(f"[TreeFileView.handle_key_event] KeyPress event received. Key: {event.key()}") # Removed logging
        current_index = self.view.currentIndex()

        key = event.key()
        if key == Qt.Key.Key_Insert:
            # logging.critical("[TreeFileView.handle_key_event] INSERT key detected. Toggling selection.") # Removed logging
            self.toggle_insert_selection_for_current_item()

            # Move to the next item after toggling insert selection
            next_row = current_index.row() + 1
            parent = current_index.parent()
            if next_row < self.model.rowCount(parent):
                next_index = self.model.index(next_row, current_index.column(), parent)
                self.view.setCurrentIndex(next_index)
                self.view.scrollTo(next_index, QAbstractItemView.ScrollHint.EnsureVisible)
            return True  # Event handled

        if self._handle_common_key_events(event, current_index):
            return True
        
        if key == Qt.Key.Key_Backspace:
            self.go_up()
            return True
        return False

    def set_path(self, path, select_item_name=None):
        self.model.set_root_path(path)
        self.view.setRootIndex(QModelIndex())
        self.path_changed.emit(path)

        # Clear insert selections when path changes
        self._insert_selected_items.clear()

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

    def get_current_path(self):
        return self.model.root_item.path

    def refresh(self):
        self.model.update_settings()
        # After refresh, ensure insert selections are still valid or clear them
        # For simplicity, let's clear them on refresh for now.
        self._insert_selected_items.clear()

    def get_selected_paths(self):
        # Tree view does not support checkbox selection in this implementation
        return []

    def get_current_selected_path(self):
        if self.view.currentIndex().isValid():
            return self.model.filePath(self.view.currentIndex())
        return None
            
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

        # Load file styles when view settings are updated
        theme_path = self.theme_manager.get_theme_path() # Use self.theme_manager
        if theme_path:
            self.model.load_file_styles(theme_path)

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

    def toggle_insert_selection_for_current_item(self):
        # logging.critical("[TreeFileView.toggle_insert_selection_for_current_item] Called.") # Removed logging
        current_index = self.view.currentIndex()
        if current_index.isValid():
            item_path = self.model.filePath(current_index)  # Get the file path

            if item_path in self._insert_selected_items:
                self._insert_selected_items.remove(item_path)
                # logging.critical(f"[TreeFileView.toggle_insert_selection_for_current_item] Removed '{item_path}' from insert selection.") # Removed logging
            else:
                self._insert_selected_items.add(item_path)
                # logging.critical(f"[TreeFileView.toggle_insert_selection_for_current_item] Added '{item_path}' to insert selection.") # Removed logging

            # Force a full update of the view for diagnostic purposes
            self.view.update()
            # logging.critical("[TreeFileView.toggle_insert_selection_for_current_item] View updated.") # Removed logging
