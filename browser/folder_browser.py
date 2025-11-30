import logging
import os
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QEvent, QItemSelectionModel, QItemSelection, QDir
from PyQt6.QtWidgets import QWidget, QTableView, QVBoxLayout, QAbstractItemView, QHeaderView, QSplitter, QTreeView
from PyQt6.QtGui import QFileSystemModel, QColor, QPalette
# from browser.flat_view_proxy_model import FlatViewProxyModel # Old import
from browser.flat_file_system_model import FlatFileSystemModel # New import
from utils.dialogs import show_error_message # Dodano import


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self, view_mode="flat", settings_manager=None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager # Store settings_manager
        self._show_dot_files = self.settings_manager.get_setting("showDotFiles", True)

        self.active_panel = None
        self.current_selected_path = None
        self.current_paths = {} # To track paths for each panel
        self.view_mode = view_mode # Store view mode
        self._select_on_load = ".." # Default item to select after model reset
        self._initial_load_complete = False
        logging.debug(f"FolderBrowser initialized with view_mode: {self.view_mode}")

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
        
        # Install event filter on panels for key events (Home, End, Tab, Insert)
        self.left_panel.installEventFilter(self)
        self.right_panel.installEventFilter(self)

    def create_file_view(self, view_mode):
        if view_mode == "flat":
            view = QTableView()
            model = FlatFileSystemModel(self, show_dot_files=self._show_dot_files) # Pass setting to custom model
            view.setModel(model)
            view.setColumnHidden(3, True) # Hide the 'Selected' state column
        else: # view_mode == "tree" (QFileSystemModel)
            model = QFileSystemModel()
            model.setRootPath(os.path.expanduser("~"))
            
            # Apply dot file filtering for QFileSystemModel
            if self._show_dot_files:
                logging.debug(f"Setting QFileSystemModel filter to show hidden files: AllDirs | Files | Hidden")
                model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.Hidden)
            else:
                logging.debug(f"Setting QFileSystemModel filter to hide hidden files: AllDirs | Files | NoDotAndDotDot")
                model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)

            view = QTreeView() # Use QTreeView for tree mode
            view.setExpandsOnDoubleClick(False)
            view.setModel(model)
            view.setRootIndex(model.index(os.path.expanduser("~")))
            horizontal_header = view.header()

        if view_mode == "flat":
            # Load and apply column widths for QTableView (flat view)
            horizontal_header = view.horizontalHeader()
            saved_widths = self.settings_manager.get_setting("table_column_widths")
            if saved_widths:
                for i, width in enumerate(saved_widths):
                    # Ensure we don't go out of bounds for the header count
                    if i < horizontal_header.count():
                        horizontal_header.resizeSection(i, width)
        else: # view_mode == "tree"
            # Load and apply column widths for QTreeView (tree view)
            saved_widths = self.settings_manager.get_setting("tree_column_widths")
            if saved_widths:
                for i, width in enumerate(saved_widths):
                    # Ensure we don't go out of bounds for the header count
                    if i < horizontal_header.count():
                        horizontal_header.resizeSection(i, width)

        # Connect signal for saving column widths
        # This part also needs to use view.header()
        horizontal_header.sectionResized.connect(lambda section, old_size, new_size: self._on_header_section_resized(view, section, old_size, new_size))

        return view
    
    def _on_header_section_resized(self, view, section, old_size, new_size):
        """Saves the current column widths for the given view."""
        if isinstance(view, QTableView):
            horizontal_header = view.horizontalHeader()
        else: # Assuming QTreeView
            horizontal_header = view.header()
        column_widths = []
        for i in range(horizontal_header.count()):
            column_widths.append(horizontal_header.sectionSize(i))

        if isinstance(view, QTableView):
            self.settings_manager.set_setting("table_column_widths", column_widths)
        elif isinstance(view, QTreeView):
            self.settings_manager.set_setting("tree_column_widths", column_widths)


    def get_column_widths(self):
        """Returns the current column widths for both panels."""
        widths = {}
        
        for panel in [self.left_panel, self.right_panel]:
            # Get the header view. QTableView uses horizontalHeader(), QTreeView uses header().
            if isinstance(panel.model(), FlatFileSystemModel): # It's a QTableView
                horizontal_header = panel.horizontalHeader()
            else: # It's a QTreeView
                horizontal_header = panel.header()
            column_widths = []
            for i in range(horizontal_header.count()):
                column_widths.append(horizontal_header.sectionSize(i))
            
            if isinstance(panel.model(), FlatFileSystemModel):
                widths["table_column_widths"] = column_widths
            elif isinstance(panel.model(), QFileSystemModel):
                widths["tree_column_widths"] = column_widths
        return widths

    def set_show_dot_files(self, show_dot_files):
        if self._show_dot_files == show_dot_files:
            logging.debug(f"FolderBrowser.set_show_dot_files: Value is already {show_dot_files}, no change needed.")
            return
        self._show_dot_files = show_dot_files  # This line updates FolderBrowser's internal attribute
        logging.debug(f"FolderBrowser.set_show_dot_files: Updated _show_dot_files to {self._show_dot_files} before refreshing views.")
        self.refresh_all_views() # Refresh all views to apply the new filter

    def on_double_clicked(self, index: QModelIndex, view): # Note: 'view' can be QTableView or QTreeView
        model = view.model()
        if model.isDir(index):
            new_path = model.filePath(index)

            if isinstance(view, QTreeView):
                # Add a permission check before trying to expand
                if not os.access(new_path, os.R_OK):
                    msg = f"Permission denied to read directory:\n{new_path}"
                    logging.error(f"Permission denied for '{new_path}'.")
                    show_error_message(self, "Permission Error", msg)
                    return

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
                model.set_current_path(path) # This is for FlatFileSystemModel
                model.layoutChanged.emit()
                panel.viewport().update()
                self.current_paths[panel] = path
                self.current_directory_changed.emit(path)
                self.select_item_after_load(panel)
            else: # QFileSystemModel (for tree view)
                index = model.index(path)
                if index.isValid():
                    panel.setRootIndex(index)
                    self.current_paths[panel] = path
                    self.current_directory_changed.emit(path)
                    self.select_item_after_load(panel)
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

    def refresh_all_views(self):
        """Refreshes both the left and right panels."""
        logging.info("Refreshing all views.")
        self.refresh_view_for_panel(self.left_panel)
        self.refresh_view_for_panel(self.right_panel)

    def refresh_view_for_panel(self, panel):
        """Helper to refresh a specific panel."""
        if panel:
            logging.debug(f"Refreshing view for panel: {panel} (type: {type(panel.model())})")
            current_path = self.current_paths.get(panel)
            if current_path:
                model = panel.model()
                if isinstance(model, FlatFileSystemModel):
                    logging.debug(f"In FolderBrowser.refresh_view_for_panel: Preparing to call FlatFileSystemModel.set_show_dot_files with value: {self._show_dot_files}")
                    # Update filter by calling the model's specific setter
                    model.set_show_dot_files(self._show_dot_files)
                    # Explicitly emit signals to ensure QTableView updates
                    model.layoutChanged.emit() 
                    panel.viewport().update() # Force viewport update
                    logging.debug(f"FlatFileSystemModel for panel {panel} refreshed and viewport updated.")
                    if self.current_paths.get(panel) != current_path:
                        self.current_paths[panel] = current_path
                        self.current_directory_changed.emit(current_path)
                else: # QFileSystemModel (tree view)
                    logging.debug(f"Entering QFileSystemModel refresh logic for panel: {panel}.")
                    # Apply dot file filtering for QFileSystemModel before refreshing
                    if self._show_dot_files:
                        logging.debug(f"Refreshing QFileSystemModel filter to show hidden files: AllDirs | Files | Hidden")
                        model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.Hidden)
                    else:
                        logging.debug(f"Refreshing QFileSystemModel filter to hide hidden files: AllDirs | Files | NoDotAndDotDot")
                        model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
                    
                    # For QFileSystemModel, reset the root index to force a refresh
                    # (the filter will have already been updated)
                    index = model.index(current_path)
                    if index.isValid():
                        panel.setRootIndex(index)
                    else:
                        logging.error(f"Could not set root index to '{current_path}' for panel refresh.")
                    
                    model.layoutChanged.emit()
                    panel.viewport().update()
    
    def set_active_panel(self, panel):
        # Define stylesheets
        active_stylesheet = """
            QTableView { border: 2px solid blue; }
            QTreeView { border: 2px solid blue; }
            QTableView::item:selected { background-color: #ADD8E6; color: black; }
            QTreeView::item:selected { background-color: #ADD8E6; color: black; }
        """
        inactive_stylesheet = """
            QTableView { border: none; }
            QTreeView { border: none; }
            QTableView::item:selected { background-color: #D3D3D3; color: black; }
            QTreeView::item:selected { background-color: #D3D3D3; color: black; }
        """

        if self.active_panel and self.active_panel != panel:
            self.active_panel.setStyleSheet(inactive_stylesheet)

        self.active_panel = panel
        self.active_panel.setStyleSheet(active_stylesheet)
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

    def get_selected_paths(self):
        """Returns a list of all selected file paths from the active panel."""
        if not self.active_panel:
            return []

        model = self.active_panel.model()

        # If it's our new model, use its internal selection logic
        if isinstance(model, FlatFileSystemModel):
            # Also include the currently focused item if no checkboxes are ticked
            selected_paths = model.get_selected_paths()
            if not selected_paths:
                current_index = self.active_panel.currentIndex()
                if current_index.isValid():
                    file_name = model.fileName(current_index)
                    if file_name != "..":
                        return [model.filePath(current_index)]
            return selected_paths

        # Otherwise, use the standard QItemSelectionModel logic (for tree view)
        selection_model = self.active_panel.selectionModel()
        selected_rows = selection_model.selectedRows()
        
        if selected_rows:
            paths = [model.filePath(index) for index in selected_rows]
            return [p for p in paths if p and os.path.basename(p) != ".."]

        # Fallback for single selection in tree view
        current_index = self.active_panel.currentIndex()
        if current_index.isValid():
            path = model.filePath(current_index)
            if path and os.path.basename(path) != "..":
                return [path]

        return []
    def get_selected_path_for_panel(self, panel):
        """Returns the path to the currently selected file or directory in the given panel."""
        selection_model = panel.selectionModel()
        indexes = selection_model.selectedIndexes()
        if indexes:
            # We only care about the first selected item for comparison
            selected_index = indexes[0]
            # Ensure it's the 0th column index to get the file path correctly
            if selected_index.column() != 0:
                selected_index = selected_index.sibling(selected_index.row(), 0)

            model = panel.model()
            path = model.filePath(selected_index)
            # Exclude '..' entry for selection
            if os.path.basename(path) == "..":
                return None
            return path
        return None

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

            if key == Qt.Key.Key_Insert:
                model = source.model()
                # Check if it's our custom model that has the toggle method
                if hasattr(model, 'toggle_selection_by_index'):
                    current_index = source.currentIndex()
                    model.toggle_selection_by_index(current_index)

                    # Move to the next item
                    next_row = current_index.row() + 1
                    parent = current_index.parent()
                    if next_row < model.rowCount(parent):
                        next_index = model.index(next_row, current_index.column(), parent)
                        if next_index.isValid():
                            source.setCurrentIndex(next_index) # Move focus rect
                            source.scrollTo(next_index, QAbstractItemView.ScrollHint.EnsureVisible)
                return True
            
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
                # Unconditionally update active_panel when focus changes to a panel
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

        # Re-install event filters on new panels
        self.left_panel.installEventFilter(self)
        self.right_panel.installEventFilter(self)

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
