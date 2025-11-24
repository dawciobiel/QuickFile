import logging
import os
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QEvent, QItemSelectionModel
from PyQt6.QtWidgets import QWidget, QTableView, QVBoxLayout, QAbstractItemView, QHeaderView, QSplitter, QTreeView
from PyQt6.QtGui import QFileSystemModel, QColor, QPalette
# from browser.flat_view_proxy_model import FlatViewProxyModel # Old import
from browser.flat_file_system_model import FlatFileSystemModel # New import
from utils.dialogs import show_error_message # Dodano import


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self, view_mode="flat", parent=None):
        super().__init__(parent)

        self.active_panel = None
        self.current_selected_path = None
        self.current_paths = {} # To track paths for each panel
        self.view_mode = view_mode # Store view mode
        self._select_on_load = ".." # Default item to select after model reset
        self._initial_load_complete = False

        self.left_panel = self.create_file_view(self.view_mode)
        self.right_panel = self.create_file_view(self.view_mode)

        # Set initial paths for panels
        home_path = os.path.expanduser("~")
        self.current_paths[self.left_panel] = home_path
        self.current_paths[self.right_panel] = home_path

        # Initialize models with current paths
        if self.view_mode == "flat":
            self.left_panel.model().set_current_path(self.current_paths[self.left_panel])
            self.right_panel.model().set_current_path(self.current_paths[self.right_panel])
        else: # tree view (QFileSystemModel)
            self.left_panel.setRootIndex(self.left_panel.model().index(self.current_paths[self.left_panel]))
            self.right_panel.setRootIndex(self.right_panel.model().index(self.current_paths[self.right_panel]))


        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

    def create_file_view(self, view_mode):
        if view_mode == "flat":
            view = QTableView()
            model = FlatFileSystemModel(self) # New custom model
            view.setModel(model)
        else: # view_mode == "tree" (QFileSystemModel)
            model = QFileSystemModel()
            model.setRootPath(os.path.expanduser("~"))
            view = QTreeView() # Use QTreeView for tree mode
            view.setExpandsOnDoubleClick(False)
            view.setModel(model)
            view.setRootIndex(model.index(os.path.expanduser("~")))

        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        if isinstance(view, QTableView): # Apply only to QTableView
            view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Modyfikacja palety dla zaznaczonych elementów - zakomentowano, ponieważ powoduje segmentation fault w PyQt6
        # palette = view.palette()
        # palette.setColor(QPalette.ColorRole.Highlight, QColor("#ADD8E6")) # Jasnoniebieskie tło zaznaczenia
        # palette.setColor(QPalette.ColorRole.HighlightedText, QColor("orange")) # Pomarańczowy tekst zaznaczenia
        # view.setPalette(palette)

        model.modelReset.connect(lambda: self.select_item_after_load(view))
        view.doubleClicked.connect(lambda index: self.on_double_clicked(index, view))
        view.selectionModel().currentChanged.connect(lambda current, previous: self.update_current_selection(current, previous, view))
        view.setMouseTracking(True) # Enable mouse tracking for focus events
        view.installEventFilter(self) # Install event filter for focus events

        return view
    
    def on_double_clicked(self, index: QModelIndex, view): # Note: 'view' can be QTableView or QTreeView
        model = view.model()
        if model.isDir(index):
            new_path = model.filePath(index)

            if isinstance(view, QTreeView):
                # In Tree view, double-clicking a directory should expand/collapse it
                view.setExpanded(index, not view.isExpanded(index))
                # Update current path without changing the tree root
                self.current_paths[view] = new_path
                self.current_directory_changed.emit(new_path)
            else: # QTableView (Flat view)
                file_name = model.fileName(index)
                if file_name == "..":
                    current_panel_path = self.current_paths.get(view)
                    self.navigate_to_path(new_path, panel=view, select_entry_path=current_panel_path)
                else:
                    self.navigate_to_path(new_path, panel=view)
        else:
            # If it's a file, emit file_selected (same for both views)
            self.file_selected.emit(model.filePath(index))

    def update_current_selection(self, current: QModelIndex, previous: QModelIndex, view: QTableView):
        if current.isValid():
            self.current_selected_path = view.model().filePath(current)
            # No need to emit current_directory_changed here, it's handled by on_double_clicked
    
    def select_item_after_load(self, panel):
        if not self._select_on_load:
            return

        model = panel.model()
        target_name = self._select_on_load
        found_index = QModelIndex()

        # Helper to get the correct index based on model type
        def get_index(r):
            if isinstance(model, FlatFileSystemModel):
                return model.index(r, 0)
            else:
                return model.index(r, 0, panel.rootIndex())

        for row in range(model.rowCount()):
            index = get_index(row)
            if model.fileName(index) == target_name:
                found_index = index
                break
        
        # If the target is not found, try to select '..' as a fallback
        if not found_index.isValid() and target_name != "..":
             for row in range(model.rowCount()):
                index = get_index(row)
                if model.fileName(index) == "..":
                    found_index = index
                    break

        if found_index.isValid():
            selection_model = panel.selectionModel()
            selection_model.setCurrentIndex(found_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            selection_model.select(found_index, QItemSelectionModel.SelectionFlag.Rows | QItemSelectionModel.SelectionFlag.ClearAndSelect)
            panel.scrollTo(found_index, QAbstractItemView.ScrollHint.PositionAtCenter)
        
        # Reset the flag
        self._select_on_load = None

    def navigate_to_path(self, path, panel=None, select_entry_path=None):
        if panel is None:
            panel = self.active_panel

        if not os.path.exists(path) or not os.path.isdir(path):
            msg = f"Path '{path}' is invalid or does not exist."
            logging.error(msg)
            show_error_message(self, "Navigation Error", msg)
            return

        if not os.access(path, os.R_OK):
            msg = f"Permission denied to read directory:\n{path}"
            logging.error(f"Permission denied for '{path}'.")
            show_error_message(self, "Permission Error", msg)
            return

        if panel:
            # Decide what to select after the model reloads
            if select_entry_path:
                self._select_on_load = os.path.basename(select_entry_path)
            else:
                self._select_on_load = ".."

            # Trigger the model reset
            model = panel.model()
            if isinstance(model, FlatFileSystemModel):
                model.set_current_path(path)
                self.current_paths[panel] = path
                self.current_directory_changed.emit(path)
            else: # QFileSystemModel
                index = model.index(path)
                if index.isValid():
                    panel.setRootIndex(index)
                    self.current_paths[panel] = path
                    self.current_directory_changed.emit(path)
                else:
                    msg = f"Could not set directory to '{path}'."
                    logging.error(msg)
                    show_error_message(self, "Navigation Error", msg)

    def set_panel_path(self, panel, path):
        self.navigate_to_path(path, panel)

    def go_up_directory(self):
        if self.active_panel:
            current_path = self.current_paths.get(self.active_panel)
            if current_path:
                parent_path = os.path.dirname(current_path)
                if parent_path and parent_path != current_path:
                    # Pass the current_path (the subdirectory we are leaving) to navigate_to_path
                    self.navigate_to_path(parent_path, self.active_panel, select_entry_path=current_path)

    def refresh_view(self):
        if self.active_panel:
            current_path = self.current_paths.get(self.active_panel)
            if current_path:
                self.navigate_to_path(current_path, self.active_panel)
    
    def set_active_panel(self, panel):
        if self.active_panel and self.active_panel != panel:
            self.active_panel.setStyleSheet("") # Reset style sheet
            self.active_panel.clearSelection()

        self.active_panel = panel
        self.active_panel.setStyleSheet("QTableView { border: 1px solid blue; } QTreeView { border: 1px solid blue; }") # Highlight active
        current_path = self.current_paths.get(self.active_panel)
        if current_path: # current_path is now a string
            self.current_directory_changed.emit(current_path)

        # Ensure full-row selection on the newly activated panel
        selection_model = self.active_panel.selectionModel()
        current_index = selection_model.currentIndex()

        if not current_index.isValid() and self.active_panel.model().rowCount() > 0:
            # If no item is current, select the first one
            current_index = self.active_panel.model().index(0, 0)
        
        if current_index.isValid():
            selection_model.setCurrentIndex(current_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            selection_model.select(current_index, QItemSelectionModel.SelectionFlag.Rows | QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def get_active_panel_id(self):
        if self.active_panel == self.left_panel:
            return "left"
        elif self.active_panel == self.right_panel:
            return "right"
        return None

    def set_active_panel_by_id(self, panel_id):
        panel_to_set = None
        if panel_id == "left":
            panel_to_set = self.left_panel
        elif panel_id == "right":
            panel_to_set = self.right_panel
        
        if panel_to_set:
            self.set_active_panel(panel_to_set)
            panel_to_set.setFocus()

    def initial_load_done(self):
        self._initial_load_complete = True

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress and source in [self.left_panel, self.right_panel]:
            key = event.key()

            if key == Qt.Key.Key_Tab:
                if self.active_panel == self.left_panel:
                    new_panel = self.right_panel
                else:
                    new_panel = self.left_panel
                
                self.set_active_panel(new_panel)
                new_panel.setFocus()
                return True # Event handled

            if key == Qt.Key.Key_Home:
                model = source.model()
                selection_model = source.selectionModel()
                
                parent_index = QModelIndex()
                if not isinstance(model, FlatFileSystemModel):
                    parent_index = source.rootIndex()

                first_index = model.index(0, 0, parent_index)
                if first_index.isValid():
                    selection_model.setCurrentIndex(first_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
                    selection_model.select(first_index, QItemSelectionModel.SelectionFlag.Rows | QItemSelectionModel.SelectionFlag.ClearAndSelect)
                    source.scrollTo(first_index, QAbstractItemView.ScrollHint.PositionAtTop)
                return True # Event handled

            if key == Qt.Key.Key_End:
                model = source.model()
                selection_model = source.selectionModel()

                parent_index = QModelIndex()
                if not isinstance(model, FlatFileSystemModel):
                    parent_index = source.rootIndex()

                row_count = model.rowCount(parent_index)
                if row_count > 0:
                    last_index = model.index(row_count - 1, 0, parent_index)
                    if last_index.isValid():
                        selection_model.setCurrentIndex(last_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
                        selection_model.select(last_index, QItemSelectionModel.SelectionFlag.Rows | QItemSelectionModel.SelectionFlag.ClearAndSelect)
                        source.scrollTo(last_index, QAbstractItemView.ScrollHint.PositionAtBottom)
                return True # Event handled

        if event.type() == QEvent.Type.FocusIn:
            if self._initial_load_complete and source in [self.left_panel, self.right_panel]:
                if self.active_panel != source:
                    self.set_active_panel(source)
        
        return super().eventFilter(source, event)

    def set_view_mode(self, mode):
        # Store the new view mode
        self.view_mode = mode

        # Need to store current paths before recreating to restore them
        left_path = self.current_paths.get(self.left_panel) # current_paths already stores strings
        right_path = self.current_paths.get(self.right_panel) # current_paths already stores strings
        
        # Remove old panels from layout and delete them
        layout = self.layout()
        splitter = self.findChild(QSplitter)

        # Store old panels before creating new ones
        old_left_panel = self.left_panel
        old_right_panel = self.right_panel

        # Create new panels
        self.left_panel = self.create_file_view(self.view_mode)
        self.right_panel = self.create_file_view(self.view_mode)

        if splitter:
            # Replace old panels with new ones in the splitter
            splitter.replaceWidget(0, self.left_panel) # Assuming left panel is at index 0
            splitter.replaceWidget(1, self.right_panel) # Assuming right panel is at index 1
            old_left_panel.deleteLater()
            old_right_panel.deleteLater()
        else:
            # If no splitter, directly replace in the layout (though this case might not be reached with current structure)
            layout.removeWidget(old_left_panel)
            layout.removeWidget(old_right_panel)
            layout.addWidget(self.left_panel)
            layout.addWidget(self.right_panel)
            old_left_panel.deleteLater()
            old_right_panel.deleteLater()

        # Restore paths
        self.navigate_to_path(left_path, self.left_panel)
        self.navigate_to_path(right_path, self.right_panel)

        self.set_active_panel(self.left_panel)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            self.go_up_directory()
            event.accept()
            return

        if self.active_panel:
            model = self.active_panel.model()
            selection_model = self.active_panel.selectionModel()

            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                selected_indexes = selection_model.selectedIndexes()
                if selected_indexes:
                    index = selected_indexes[0]
                    if model.isDir(index):
                        self.on_double_clicked(index, self.active_panel)
                        event.accept()
                        return

        super().keyPressEvent(event)