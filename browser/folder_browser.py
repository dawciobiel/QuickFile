import logging
import os
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QEvent, QItemSelectionModel, QItemSelection, QDir, QStringListModel
from PyQt6.QtWidgets import QWidget, QTableView, QVBoxLayout, QAbstractItemView, QHeaderView, QSplitter, QTreeView, QLineEdit, QCompleter
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
        self.active_panel_widget = None # Initialize active_panel_widget
        logging.debug(f"FolderBrowser initialized with view_mode: {self.view_mode}")

        self.left_panel_widget = self.create_file_view(self.view_mode)
        self.right_panel_widget = self.create_file_view(self.view_mode)

        # Store references to the actual file views and path displays
        self.left_panel = self.left_panel_widget.file_view
        self.left_path_display = self.left_panel_widget.path_edit
        self.right_panel = self.right_panel_widget.file_view
        self.right_path_display = self.right_panel_widget.path_edit

        # Set initial paths for panels
        home_path = os.path.expanduser("~")
        self.current_paths[self.left_panel_widget] = home_path
        self.current_paths[self.right_panel_widget] = home_path

        # Initialize models with current paths and update path displays
        if self.view_mode == "flat":
            self.left_panel.model().set_current_path(self.current_paths[self.left_panel_widget])
            self.right_panel.model().set_current_path(self.current_paths[self.right_panel_widget])
        else: # tree view (QFileSystemModel)
            self.left_panel.setRootIndex(self.left_panel.model().index(self.current_paths[self.left_panel_widget]))
            self.right_panel.setRootIndex(self.right_panel.model().index(self.current_paths[self.right_panel_widget]))
        
        # Update path display fields initially
        self.left_path_display.setText(home_path)
        self.right_path_display.setText(home_path)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel_widget)
        splitter.addWidget(self.right_panel_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        
        # Install event filter on file views for key events (Home, End, Tab, Insert)
        self.left_panel.installEventFilter(self)
        self.right_panel.installEventFilter(self)

    def create_file_view(self, view_mode):
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Editable path display with autocompletion
        # Editable path display with autocompletion
        # Editable path display with autocompletion
        path_edit = QLineEdit() # Use editable QLineEdit
        path_edit.setReadOnly(False) # Make it editable
        path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: #EEE;
                border: 1px solid #555;
                padding: 2px;
            }
        """)

        # Initialize completer for path suggestions
        path_model = QStringListModel() # Create the model
        completer = QCompleter(path_model, self) # Create completer with the model
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        
        # Store completer and path_edit on panel_widget FIRST
        panel_widget.path_edit = path_edit
        panel_widget.completer = completer # Assign completer to panel_widget
        panel_widget.completer_model = path_model # Explicitly store the model

        # Set the completer for the QLineEdit
        path_edit.setCompleter(completer)

        # Connect signals for path editing and completion
        # Use lambda to pass panel_widget to the slot (slots will be defined later)
        path_edit.textChanged.connect(lambda text, pw=panel_widget: self._update_path_completions(text, pw))
        path_edit.returnPressed.connect(lambda pw=panel_widget: self._navigate_from_path_edit(pw))

        panel_layout.addWidget(path_edit) # Add the new path_edit

        if view_mode == "flat":
            file_view = QTableView()
            model = FlatFileSystemModel(self, show_dot_files=self._show_dot_files)
            file_view.setModel(model)
            file_view.setColumnHidden(3, True)
        else: # view_mode == "tree" (QFileSystemModel)
            model = QFileSystemModel()
            model.setRootPath(os.path.expanduser("~"))
            
            if self._show_dot_files:
                logging.debug(f"Setting QFileSystemModel filter to show hidden files: AllDirs | Files | Hidden")
                model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.Hidden)
            else:
                logging.debug(f"Setting QFileSystemModel filter to hide hidden files: AllDirs | Files | NoDotAndDotDot")
                model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)

            file_view = QTreeView()
            file_view.setExpandsOnDoubleClick(False)
            file_view.setModel(model)
            file_view.setRootIndex(model.index(os.path.expanduser("~")))
        
        panel_layout.addWidget(file_view)

        # Store the new path_edit and completer, and file_view in the panel_widget
        panel_widget.path_edit = path_edit
        panel_widget.completer = completer
        panel_widget.file_view = file_view

        # Apply column widths
        if view_mode == "flat":
            horizontal_header = file_view.horizontalHeader()
            saved_widths = self.settings_manager.get_setting("table_column_widths")
        else: # view_mode == "tree"
            horizontal_header = file_view.header()
            saved_widths = self.settings_manager.get_setting("tree_column_widths")

        if saved_widths:
            for i, width in enumerate(saved_widths):
                if i < horizontal_header.count():
                    horizontal_header.resizeSection(i, width)
        
        horizontal_header.sectionResized.connect(lambda section, old_size, new_size: self._on_header_section_resized(file_view, section, old_size, new_size))

        return panel_widget
    
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
        
        for panel_widget in [self.left_panel_widget, self.right_panel_widget]:
            panel = panel_widget.file_view # Get the actual file view (QTableView or QTreeView)
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

        panel_widget = None
        if panel == self.left_panel:
            panel_widget = self.left_panel_widget
        elif panel == self.right_panel:
            panel_widget = self.right_panel_widget
        else:
            logging.error(f"navigate_to_path: Could not determine panel_widget for file_view: {panel}")
            return

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

        if panel_widget:
            # Decide what to select after the model reloads
            if select_entry_path:
                self._select_on_load = os.path.basename(select_entry_path)
            else:
                self._select_on_load = ".."

            # Trigger the model reset
            model = panel.model()
            if isinstance(model, FlatFileSystemModel):
                model.set_current_path(path)
                model.layoutChanged.emit()
                panel.viewport().update()
                self.current_paths[panel_widget] = path
                panel_widget.path_display.setText(path) # Update path display
                self.current_directory_changed.emit(path)
                self.select_item_after_load(panel)
            else: # QFileSystemModel (for tree view)
                index = model.index(path)
                if index.isValid():
                    panel.setRootIndex(index)
                    self.current_paths[panel_widget] = path
                    panel_widget.path_display.setText(path) # Update path display
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
            
            panel_widget = None
            if panel == self.left_panel:
                panel_widget = self.left_panel_widget
            elif panel == self.right_panel:
                panel_widget = self.right_panel_widget
            else:
                logging.error(f"refresh_view_for_panel: Could not determine panel_widget for file_view: {panel}")
                return

            current_path = self.current_paths.get(panel_widget) # Use panel_widget here
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
                    if self.current_paths.get(panel_widget) != current_path:
                        self.current_paths[panel_widget] = current_path
                        panel_widget.path_display.setText(current_path) # Update path display
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
                    
                    panel_widget.path_display.setText(current_path) # Update path display
                    model.layoutChanged.emit()
                    panel.viewport().update()
    
    def set_active_panel(self, panel_widget):
        # Define stylesheets
        active_stylesheet = """
            QWidget { border: 2px solid blue; }
            QTableView::item:selected { background-color: #ADD8E6; color: black; }
            QTreeView::item:selected { background-color: #ADD8E6; color: black; }
        """
        inactive_stylesheet = """
            QWidget { border: none; }
            QTableView::item:selected { background-color: #D3D3D3; color: black; }
            QTreeView::item:selected { background-color: #D3D3D3; color: black; }
        """

        # Deactivate previously active panel if any
        if self.active_panel_widget and self.active_panel_widget != panel_widget:
            self.active_panel_widget.setStyleSheet(inactive_stylesheet)

        # Set new active panel
        self.active_panel_widget = panel_widget
        self.active_panel = panel_widget.file_view
        self.active_path_display = panel_widget.path_display
        self.active_panel_widget.setStyleSheet(active_stylesheet)

        current_path = self.current_paths.get(self.active_panel_widget)
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
        panel_widget_to_set = None
        if panel_id == "left":
            panel_widget_to_set = self.left_panel_widget
        elif panel_id == "right":
            panel_widget_to_set = self.right_panel_widget
        
        if panel_widget_to_set:
            self.set_active_panel(panel_widget_to_set)
            panel_widget_to_set.file_view.setFocus()

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
                # Determine the next panel_widget to activate
                if self.active_panel_widget == self.left_panel_widget:
                    new_panel_widget = self.right_panel_widget
                else:
                    new_panel_widget = self.left_panel_widget
                
                # Set the new active panel and focus on its file view
                self.set_active_panel(new_panel_widget)
                new_panel_widget.file_view.setFocus()
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
                if source == self.left_panel:
                    self.set_active_panel(self.left_panel_widget)
                elif source == self.right_panel:
                    self.set_active_panel(self.right_panel_widget)
        
        return super().eventFilter(source, event)

    def _update_path_completions(self, text, panel_widget):
        """Updates path completions based on the text entered in the path edit field."""
        if not panel_widget:
            logging.error("_update_path_completions: panel_widget is None.")
            return
            
        completer = panel_widget.completer
        if not completer:
            logging.error(f"_update_path_completions: Completer not found for panel_widget.")
            return
        
        # Check if completer model is valid before using it
        if not completer.model():
            logging.error(f"_update_path_completions: Completer model is None for panel_widget.")
            return

        # Get the directory part of the path for listing
        base_path = os.path.dirname(text)
        if not base_path: # If text is just a filename or root
            base_path = "/"
        elif not os.path.isdir(base_path):
            # If the base path itself is not a valid directory, try to find a parent that is
            # This handles cases like typing in a non-existent subdirectory
            parent_dir = os.path.dirname(base_path)
            while parent_dir and not os.path.isdir(parent_dir):
                parent_dir = os.path.dirname(parent_dir)
            if parent_dir:
                base_path = parent_dir
            else:
                # Fallback to root if no valid parent is found
                base_path = "/"
                
        suggestions = []
        try:
            if os.path.isdir(base_path) and os.access(base_path, os.R_OK):
                # List all entries (files and directories) in the base_path
                for entry in os.listdir(base_path):
                    full_path = os.path.join(base_path, entry)
                    if os.path.isdir(full_path): # Only suggest directories
                        suggestions.append(full_path)
                # Add a suggestion for the current directory itself if it's a valid path
                # Ensure text is a directory and starts with base_path to avoid issues
                if os.path.isdir(text) and text.startswith(base_path) and text not in suggestions:
                    suggestions.append(text)

            completer.model().setStringList(suggestions)
        except OSError as e:
            logging.error(f"Error listing directory for path completions: {base_path} - {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred in _update_path_completions: {e}")


    def _navigate_from_path_edit(self, panel_widget):
        """Navigates to the path entered in the path edit field."""
        path_edit = panel_widget.path_edit
        path = path_edit.text()

        # Use the existing navigate_to_path method
        # We need to get the actual file view (QTableView or QTreeView) for the panel
        file_view = panel_widget.file_view
        self.navigate_to_path(path, panel=file_view)


    def navigate_to_path(self, path, panel=None, select_entry_path=None):
        if panel is None:
            panel = self.active_panel # Default to active panel if not specified

        panel_widget = None
        if panel == self.left_panel:
            panel_widget = self.left_panel_widget
        elif panel == self.right_panel:
            panel_widget = self.right_panel_widget
        else:
            logging.error(f"navigate_to_path: Could not determine panel_widget for file_view: {panel}")
            return

        if not panel_widget:
            logging.error(f"navigate_to_path: Panel widget not found for panel: {panel}")
            return

        if not os.path.exists(path) or not os.path.isdir(path):
            msg = f"Path '{path}' is invalid or does not exist."
            logging.error(msg)
            show_error_message(self, "Navigation Error", msg)
            # Reset the path edit to the current valid path if navigation fails
            current_valid_path = self.current_paths.get(panel_widget)
            if current_valid_path:
                path_edit = panel_widget.path_edit
                if path_edit:
                    path_edit.setText(current_valid_path)
            return

        if not os.access(path, os.R_OK):
            msg = f"Permission denied to read directory:\n{path}"
            logging.error(f"Permission denied for '{path}'.")
            show_error_message(self, "Permission Error", msg)
            # Reset the path edit to the current valid path if navigation fails
            current_valid_path = self.current_paths.get(panel_widget)
            if current_valid_path:
                path_edit = panel_widget.path_edit
                if path_edit:
                    path_edit.setText(current_valid_path)
            return

        # Update the path edit field FIRST
        path_edit = panel_widget.path_edit
        if path_edit:
            path_edit.setText(path)
            # Ensure the cursor is at the end of the path for better UX
            path_edit.setCursorPosition(len(path))

        self.current_paths[panel_widget] = path # Update current path storage

        # Decide what to select after the model reloads
        if select_entry_path:
            self._select_on_load = os.path.basename(select_entry_path)
        else:
            self._select_on_load = ".." # Default to selecting '..' for upward navigation

        # Trigger the model reset
        model = panel.model()
        if isinstance(model, FlatFileSystemModel):
            model.set_current_path(path)
            model.layoutChanged.emit()
            panel.viewport().update()
            self.current_directory_changed.emit(path)
            self.select_item_after_load(panel)
        else: # QFileSystemModel (for tree view)
            index = model.index(path)
            if index.isValid():
                panel.setRootIndex(index)
                self.current_directory_changed.emit(path)
                self.select_item_after_load(panel)
            else:
                msg = f"Could not set root index to '{path}' for panel."
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
            
            panel_widget = None
            if panel == self.left_panel:
                panel_widget = self.left_panel_widget
            elif panel == self.right_panel:
                panel_widget = self.right_panel_widget
            else:
                logging.error(f"refresh_view_for_panel: Could not determine panel_widget for file_view: {panel}")
                return

            current_path = self.current_paths.get(panel_widget) # Use panel_widget here
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
                    if self.current_paths.get(panel_widget) != current_path:
                        self.current_paths[panel_widget] = current_path
                        # Update the path edit field
                        if panel_widget.path_edit:
                            panel_widget.path_edit.setText(current_path)
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
                    
                    # Update the path edit field
                    if panel_widget.path_edit:
                        panel_widget.path_edit.setText(current_path)
                    model.layoutChanged.emit()
                    panel.viewport().update()
    
    def set_active_panel(self, panel_widget):
        # Define stylesheets
        active_stylesheet = """
            QWidget { border: 2px solid blue; }
            QTableView::item:selected { background-color: #ADD8E6; color: black; }
            QTreeView::item:selected { background-color: #ADD8E6; color: black; }
        """
        inactive_stylesheet = """
            QWidget { border: none; }
            QTableView::item:selected { background-color: #D3D3D3; color: black; }
            QTreeView::item:selected { background-color: #D3D3D3; color: black; }
        """

        # Deactivate previously active panel if any
        if self.active_panel_widget and self.active_panel_widget != panel_widget:
            self.active_panel_widget.setStyleSheet(inactive_stylesheet)

        # Set new active panel
        self.active_panel_widget = panel_widget
        self.active_panel = panel_widget.file_view
        # self.active_path_display = panel_widget.path_display # This line might need adjustment as path_display is now path_edit
        self.active_panel_widget.setStyleSheet(active_stylesheet)

        current_path = self.current_paths.get(self.active_panel_widget)
        if current_path: # current_path is now a string
            self.current_directory_changed.emit(current_path)
            # Update the path edit field of the newly active panel
            if panel_widget.path_edit:
                panel_widget.path_edit.setText(current_path)
                # Ensure focus is on the path edit when it becomes active
                panel_widget.path_edit.setFocus()

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
        panel_widget_to_set = None
        if panel_id == "left":
            panel_widget_to_set = self.left_panel_widget
        elif panel_id == "right":
            panel_widget_to_set = self.right_panel_widget
        
        if panel_widget_to_set:
            self.set_active_panel(panel_widget_to_set)
            # Set focus to the path edit field of the activated panel
            if panel_widget_to_set.path_edit:
                panel_widget_to_set.path_edit.setFocus()

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
                # Determine the next panel_widget to activate
                if self.active_panel_widget == self.left_panel_widget:
                    new_panel_widget = self.right_panel_widget
                else:
                    new_panel_widget = self.left_panel_widget
                
                # Set the new active panel and focus on its file view
                self.set_active_panel(new_panel_widget)
                # Ensure focus goes to the path edit field of the activated panel
                if new_panel_widget.path_edit:
                    new_panel_widget.path_edit.setFocus()
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
                if source == self.left_panel:
                    self.set_active_panel(self.left_panel_widget)
                elif source == self.right_panel:
                    self.set_active_panel(self.right_panel_widget)
        
        return super().eventFilter(source, event)

    def set_view_mode(self, mode):
        # Store the new view mode
        self.view_mode = mode

        # Need to store current paths and text from path_edit before recreating to restore them
        left_path_text = self.left_panel_widget.path_edit.text() if self.left_panel_widget and hasattr(self.left_panel_widget, 'path_edit') else os.path.expanduser("~")
        right_path_text = self.right_panel_widget.path_edit.text() if self.right_panel_widget and hasattr(self.right_panel_widget, 'path_edit') else os.path.expanduser("~")

        # Remove old panels from layout and delete them
        layout = self.layout()
        splitter = self.findChild(QSplitter)

        # Store old file views before creating new ones
        old_left_file_view = self.left_panel
        old_right_file_view = self.right_panel

        # Create new panels
        # self.left_panel_widget and self.right_panel_widget will be re-assigned by create_file_view
        new_left_panel_widget = self.create_file_view(self.view_mode)
        new_right_panel_widget = self.create_file_view(self.view_mode)

        if splitter:
            # Replace old panels with new ones in the splitter
            splitter.replaceWidget(0, new_left_panel_widget) # Assuming left panel is at index 0
            splitter.replaceWidget(1, new_right_panel_widget) # Assuming right panel is at index 1
            old_left_file_view.deleteLater()
            old_right_file_view.deleteLater()
        else:
            # If no splitter, directly replace in the layout
            layout.removeWidget(old_left_file_view)
            layout.removeWidget(old_right_file_view)
            layout.addWidget(new_left_panel_widget)
            layout.addWidget(new_right_panel_widget)
            old_left_file_view.deleteLater()
            old_right_file_view.deleteLater()

        # Update internal references
        self.left_panel_widget = new_left_panel_widget
        self.right_panel_widget = new_right_panel_widget
        self.left_panel = self.left_panel_widget.file_view
        self.right_panel = self.right_panel_widget.file_view

        # Re-install event filters on new panels' file views
        self.left_panel.installEventFilter(self)
        self.right_panel.installEventFilter(self)

        # Restore paths and update path_edit widgets
        self.navigate_to_path(left_path_text, self.left_panel)
        self.navigate_to_path(right_path_text, self.right_panel)

        # Update current_paths dictionary with new widget instances
        self.current_paths[self.left_panel_widget] = left_path_text
        self.current_paths[self.right_panel_widget] = right_path_text

        self.set_active_panel(self.left_panel_widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            if self.active_panel_widget and self.active_panel_widget.path_edit and self.active_panel_widget.path_edit.hasFocus():
                # If path edit has focus, Backspace should not go up directory
                pass # Let the QLineEdit handle backspace
            else:
                self.go_up_directory()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Tab:
            # Handle tab to switch between panels, ensuring focus goes to path_edit first
            if self.active_panel_widget == self.left_panel_widget:
                next_panel_widget = self.right_panel_widget
            else:
                next_panel_widget = self.left_panel_widget
            
            self.set_active_panel(next_panel_widget)
            if next_panel_widget.path_edit:
                next_panel_widget.path_edit.setFocus()
            event.accept()
            return

        if self.active_panel:
            model = self.active_panel.model()
            selection_model = self.active_panel.selectionModel()

            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                # If path_edit has focus, let _navigate_from_path_edit handle it (implicitly via returnPressed)
                if self.active_panel_widget and self.active_panel_widget.path_edit and self.active_panel_widget.path_edit.hasFocus():
                    # The returnPressed signal is already connected, so it will trigger navigation
                    pass # Do nothing here, the signal handler will take care of it
                else:
                    # Otherwise, handle it as directory navigation
                    selected_indexes = selection_model.selectedIndexes()
                    if selected_indexes:
                        index = selected_indexes[0]
                        if model.isDir(index):
                            self.on_double_clicked(index, self.active_panel)
                            event.accept()
                            return

        super().keyPressEvent(event)
