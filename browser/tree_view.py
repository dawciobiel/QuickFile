import os
from PyQt6.QtCore import QModelIndex, Qt, QEvent, pyqtSignal, QPoint
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QAbstractItemView, QHeaderView, QMenu
from PyQt6.QtGui import QAction

from app.theme_manager import ThemeManager
from browser.base_view import AbstractFileView
from browser.styling_delegate import FileStyleDelegate
from browser.tree_file_system_model import TreeFileSystemModel
from app.application_logic_handler import ApplicationLogicHandler
from app.translation_manager import translation_manager


class TreeFileView(AbstractFileView):
    insert_selection_changed = pyqtSignal()
    file_selected = pyqtSignal(str)

    def __init__(self, settings_manager, theme_manager: ThemeManager, parent=None):
        super().__init__(settings_manager, parent)
        self.theme_manager = theme_manager
        self._insert_selected_items = set()

        self.model = TreeFileSystemModel(
            settings_manager,
            self,
            insert_selected_items=self._insert_selected_items
        )
        
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setItemDelegate(FileStyleDelegate(self.view))
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setExpandsOnDoubleClick(False)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        
        self.update_view_settings()
        
        self.view.doubleClicked.connect(self.on_item_double_clicked)
        self.view.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos: QPoint):
        main_window = self.window()
        if not hasattr(main_window, 'application_logic_handler'):
            return
            
        app_logic: ApplicationLogicHandler = main_window.application_logic_handler
        
        menu = QMenu()
        
        copy_action = QAction(translation_manager.translate("MenuPanel", "Copy"), self)
        copy_action.triggered.connect(app_logic.copy_selected_item)
        menu.addAction(copy_action)
        
        move_action = QAction(translation_manager.translate("MenuPanel", "Move"), self)
        move_action.triggered.connect(app_logic.move_selected_item)
        menu.addAction(move_action)
        
        delete_action = QAction(translation_manager.translate("MenuPanel", "Delete"), self)
        delete_action.triggered.connect(app_logic.delete_selected_item)
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        properties_action = QAction(translation_manager.translate("MenuPanel", "Properties"), self)
        properties_action.triggered.connect(app_logic.show_properties_dialog)
        menu.addAction(properties_action)
        
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def handle_key_event(self, event: QEvent):
        current_index = self.view.currentIndex()
        key = event.key()
        if key == Qt.Key.Key_Insert:
            self.toggle_insert_selection_for_current_item()
            next_row = current_index.row() + 1
            parent = current_index.parent()
            if next_row < self.model.rowCount(parent):
                next_index = self.model.index(next_row, current_index.column(), parent)
                self.view.setCurrentIndex(next_index)
                self.view.scrollTo(next_index, QAbstractItemView.ScrollHint.EnsureVisible)
            return True

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
        self._insert_selected_items.clear()
        self.insert_selection_changed.emit()

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
        self._insert_selected_items.clear()
        self.insert_selection_changed.emit()

    def get_selected_paths(self):
        return []

    def get_insert_selected_paths(self):
        return list(self._insert_selected_items)

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

        theme_path = self.theme_manager.get_theme_path()
        if theme_path:
            self.model.load_file_styles(theme_path)

    def on_header_section_resized(self, section, old_size, new_size):
        header = self.view.header()
        column_widths = [header.sectionSize(i) for i in range(header.count())]
        self.settings_manager.set_setting("tree_column_widths", column_widths)
        
    def on_item_double_clicked(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            if self.view.isExpanded(index):
                self.view.collapse(index)
            else:
                self.view.expand(index)
        else:
            self.file_selected.emit(path)

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
        current_index = self.view.currentIndex()
        if current_index.isValid():
            item_path = self.model.filePath(current_index)

            if item_path in self._insert_selected_items:
                self._insert_selected_items.remove(item_path)
            else:
                self._insert_selected_items.add(item_path)

            self.view.update()
            self.insert_selection_changed.emit()
