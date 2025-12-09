import logging
import os
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QEvent, QItemSelectionModel, QDir, QStringListModel
from PyQt6.QtWidgets import QWidget, QTableView, QVBoxLayout, QAbstractItemView, QSplitter, QTreeView, QLineEdit, QCompleter
from PyQt6.QtGui import QFileSystemModel
from browser.flat_file_system_model import FlatFileSystemModel
from utils.dialogs import show_error_message
from app.settings_manager import SettingsManager # Import SettingsManager

class PanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(False)
        # Usunięto domyślne style, będą zarządzane przez FolderBrowser
        self.layout.addWidget(self.path_edit)

        self.file_view = None  # Placeholder for QTableView or QTreeView
        self.completer = None
        self.completer_model = None

    def set_file_view(self, view):
        if self.file_view:
            self.layout.removeWidget(self.file_view)
            self.file_view.deleteLater()
        self.file_view = view
        self.layout.addWidget(self.file_view)

    def get_file_view(self):
        return self.file_view

    def get_path_edit(self):
        return self.path_edit


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    # Styles for path_edit
    ACTIVE_PATH_STYLE = "QLineEdit { background-color: #336699; color: #FFFFFF; border: 1px solid #555; padding: 2px; }" # Ciemniejszy niebieski
    INACTIVE_PATH_STYLE = "QLineEdit { background-color: #555555; color: #EEEEEE; border: 1px solid #555; padding: 2px; }" # Ciemniejszy szary

    def __init__(self, view_mode="flat", settings_manager: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._show_dot_files = self.settings_manager.get_setting("showDotFiles", True) if self.settings_manager else True

        # Get selection colors from settings
        self.active_selection_color = self.settings_manager.get_setting("active_selection_color")
        self.inactive_selection_color = self.settings_manager.get_setting("inactive_selection_color")

        self.active_panel_widget = None
        self.current_selected_path = None
        self.current_paths = {}
        self.view_mode = view_mode
        self._select_on_load = ".."
        self._initial_load_complete = False
        self._key_handlers = self._init_key_handlers()

        logging.debug(f"FolderBrowser initialized with view_mode: {self.view_mode}")

        self.left_panel_widget = self.create_panel_widget(self.view_mode)
        self.right_panel_widget = self.create_panel_widget(self.view_mode)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel_widget)
        splitter.addWidget(self.right_panel_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.left_panel_widget.get_file_view().installEventFilter(self)
        self.right_panel_widget.get_file_view().installEventFilter(self)

        # Ustawienie początkowego aktywnego panelu i jego stylu
        self.set_active_panel(self.left_panel_widget)

    @property
    def left_panel(self):
        return self.left_panel_widget.get_file_view()

    @property
    def right_panel(self):
        return self.right_panel_widget.get_file_view()

    def _init_key_handlers(self):
        return {
            Qt.Key.Key_Tab: self._handle_tab_key,
            Qt.Key.Key_Insert: self._handle_insert_key,
            Qt.Key.Key_Home: self._handle_home_key,
            Qt.Key.Key_End: self._handle_end_key,
            Qt.Key.Key_Backspace: self._handle_backspace_key,
            Qt.Key.Key_Return: self._handle_enter_key,
            Qt.Key.Key_Enter: self._handle_enter_key,
        }

    def create_panel_widget(self, view_mode):
        panel_widget = PanelWidget(self)
        file_view, model = self._create_file_view_and_model(view_mode)
        panel_widget.set_file_view(file_view)
        self._setup_path_completion(panel_widget)
        return panel_widget

    def _create_file_view_and_model(self, view_mode):
        if view_mode == "flat":
            file_view = QTableView()
            model = FlatFileSystemModel(self, show_dot_files=self._show_dot_files)
            file_view.setModel(model)
            file_view.setColumnHidden(3, True)
            file_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Zaznaczanie całego wiersza
            file_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Zaznaczanie pojedynczego wiersza
        else:  # "tree"
            model = QFileSystemModel()
            model.setRootPath(os.path.expanduser("~"))
            self._apply_dot_file_filter(model)
            file_view = QTreeView()
            file_view.setExpandsOnDoubleClick(False)
            file_view.setModel(model)
            file_view.setRootIndex(model.index(os.path.expanduser("~")))

        # Connect the clicked signal to perform 'Enter' action on directories
        file_view.clicked.connect(self.on_item_clicked)

        # Connect the currentChanged signal to update_current_selection
        file_view.selectionModel().currentChanged.connect(
            lambda current, previous, view=file_view: self.update_current_selection(current, previous, view)
        )

        self._configure_view_headers(file_view, view_mode)
        return file_view, model

    def _setup_path_completion(self, panel_widget):
        path_edit = panel_widget.get_path_edit()
        path_model = QStringListModel()
        completer = QCompleter(path_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        path_edit.setCompleter(completer)

        panel_widget.completer = completer
        panel_widget.completer_model = path_model

        path_edit.textChanged.connect(lambda text, pw=panel_widget: self._update_path_completions(text, pw))
        path_edit.returnPressed.connect(lambda pw=panel_widget: self._navigate_from_path_edit(pw))

    def _setup_panel(self, panel_widget, path):
        file_view = panel_widget.get_file_view()
        model = file_view.model()

        if isinstance(model, FlatFileSystemModel):
            model.set_current_path(path)
        else:
            file_view.setRootIndex(model.index(path))

        panel_widget.get_path_edit().setText(path)

    def _apply_dot_file_filter(self, model):
        if self._show_dot_files:
            model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.Hidden)
        else:
            model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)

    def _configure_view_headers(self, file_view, view_mode):
        header = file_view.horizontalHeader() if isinstance(file_view, QTableView) else file_view.header()
        setting_key = "table_column_widths" if view_mode == "flat" else "tree_column_widths"
        saved_widths = self.settings_manager.get_setting(setting_key)

        if saved_widths:
            for i, width in enumerate(saved_widths):
                if i < header.count():
                    header.resizeSection(i, width)

        header.sectionResized.connect(
            lambda section, old_size, new_size, view=file_view: self._on_header_section_resized(view)
        )

    def _on_header_section_resized(self, view):
        header = view.horizontalHeader() if isinstance(view, QTableView) else view.header()
        column_widths = [header.sectionSize(i) for i in range(header.count())]
        setting_key = "table_column_widths" if isinstance(view, QTableView) else "tree_column_widths"
        self.settings_manager.set_setting(setting_key, column_widths)

    def get_column_widths(self):
        """Returns the current column widths for both panels."""
        widths = {}
        for panel_widget in [self.left_panel_widget, self.right_panel_widget]:
            panel = panel_widget.get_file_view()
            if isinstance(panel.model(), FlatFileSystemModel):
                header = panel.horizontalHeader()
                setting_key = "table_column_widths"
            else:
                header = panel.header()
                setting_key = "tree_column_widths"
            
            column_widths = [header.sectionSize(i) for i in range(header.count())]
            widths[setting_key] = column_widths
        return widths

    def set_show_dot_files(self, show_dot_files):
        if self._show_dot_files != show_dot_files:
            self._show_dot_files = show_dot_files
            self.refresh_all_views()

    def on_double_clicked(self, index, view):
        model = view.model()
        if model.isDir(index):
            new_path = model.filePath(index)
            if isinstance(view, QTreeView):
                if os.access(new_path, os.R_OK):
                    view.setExpanded(index, not view.isExpanded(index))
                    self.current_paths[view] = new_path
                    self.current_directory_changed.emit(new_path)
                else:
                    show_error_message(self, self.tr("Permission Error"), f"Permission denied to read directory:\n{new_path}")
            else:
                current_panel_path = self.current_paths.get(view.parent())
                select_path = current_panel_path if model.fileName(index) == ".." else None
                self.navigate_to_path(new_path, panel=view, select_entry_path=select_path)
        else:
            self.file_selected.emit(model.filePath(index))

    def on_item_clicked(self, index):
        """Handle single-click on an item. If it's a directory, perform the double-click action."""
        view = self.sender()
        if view and view.model().isDir(index):
            self.on_double_clicked(index, view)

    def update_current_selection(self, current, previous, view):
        if current.isValid():
            self.current_selected_path = view.model().filePath(current)

    def select_item_after_load(self, panel):
        if not self._select_on_load:
            return

        model = panel.model()
        target_name = self._select_on_load
        root = panel.rootIndex() if isinstance(panel, QTreeView) else QModelIndex()

        for row in range(model.rowCount(root)):
            index = model.index(row, 0, root)
            if model.fileName(index) == target_name:
                self._select_and_scroll_to(panel, index)
                self._select_on_load = None
                return

        if target_name != "..":
            for row in range(model.rowCount(root)):
                index = model.index(row, 0, root)
                if model.fileName(index) == "..":
                    self._select_and_scroll_to(panel, index)
                    break
        self._select_on_load = None

    def _select_and_scroll_to(self, panel, index):
        selection_model = panel.selectionModel()
        selection_model.select(index, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
        panel.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)

    def go_up_directory(self):
        if self.active_panel_widget:
            active_view = self.active_panel_widget.get_file_view()
            current_path = self.current_paths.get(self.active_panel_widget)
            if current_path:
                parent_path = os.path.dirname(current_path)
                if parent_path != current_path:
                    self.navigate_to_path(parent_path, active_view, select_entry_path=current_path)

    def refresh_all_views(self):
        logging.info("Refreshing all views.")
        self.refresh_view_for_panel(self.left_panel_widget.get_file_view())
        self.refresh_view_for_panel(self.right_panel_widget.get_file_view())

    def refresh_view_for_panel(self, panel):
        if not panel:
            return
        panel_widget = panel.parent()
        current_path = self.current_paths.get(panel_widget)
        if not current_path:
            return

        model = panel.model()
        if isinstance(model, FlatFileSystemModel):
            model.set_show_dot_files(self._show_dot_files)
            model.layoutChanged.emit()
        else:
            self._apply_dot_file_filter(model)
            index = model.index(current_path)
            if index.isValid():
                panel.setRootIndex(index)

        panel.viewport().update()
        panel_widget.get_path_edit().setText(current_path)

    def set_active_panel(self, panel_widget):
        # Apply inactive style to previously active panel's path_edit
        if self.active_panel_widget and self.active_panel_widget != panel_widget:
            self.active_panel_widget.get_path_edit().setStyleSheet(self.INACTIVE_PATH_STYLE)
            # Apply inactive selection style to the file view
            self.active_panel_widget.get_file_view().setStyleSheet(f"QAbstractItemView::item:selected {{ background-color: {self.inactive_selection_color}; }}")

        # Set new active panel and apply active style to its path_edit
        self.active_panel_widget = panel_widget
        self.active_panel_widget.get_path_edit().setStyleSheet(self.ACTIVE_PATH_STYLE)
        # Apply active selection style to the file view
        self.active_panel_widget.get_file_view().setStyleSheet(f"QAbstractItemView::item:selected {{ background-color: {self.active_selection_color}; }}")
        
        current_path = self.current_paths.get(self.active_panel_widget)
        if current_path:
            self.current_directory_changed.emit(current_path)

        self._ensure_selection(self.active_panel_widget.get_file_view())

    def _ensure_selection(self, panel):
        selection_model = panel.selectionModel()
        if not selection_model.currentIndex().isValid() and panel.model().rowCount() > 0:
            first_index = panel.model().index(0, 0, panel.rootIndex() if isinstance(panel, QTreeView) else QModelIndex())
            if first_index.isValid():
                self._select_and_scroll_to(panel, first_index)

    def get_active_panel_id(self):
        return "left" if self.active_panel_widget == self.left_panel_widget else "right"

    def set_active_panel_by_id(self, panel_id):
        panel_to_set = self.left_panel_widget if panel_id == "left" else self.right_panel_widget
        if panel_to_set:
            self.set_active_panel(panel_to_set)
            panel_to_set.get_file_view().setFocus()

    def get_selected_paths(self):
        if not self.active_panel_widget:
            return []
        
        active_view = self.active_panel_widget.get_file_view()
        model = active_view.model()
        
        if isinstance(model, FlatFileSystemModel):
            selected = model.get_selected_paths()
            if not selected and active_view.currentIndex().isValid():
                path = model.filePath(active_view.currentIndex())
                if os.path.basename(path) != "..":
                    return [path]
            return selected
        else: # QTreeView
            selection_model = active_view.selectionModel()
            return [model.filePath(index) for index in selection_model.selectedRows() if os.path.basename(model.filePath(index)) != ".."]

    def get_selected_path_for_panel(self, panel):
        selection_model = panel.selectionModel()
        if selection_model.hasSelection():
            index = selection_model.selectedIndexes()[0]
            path = panel.model().filePath(index)
            return path if os.path.basename(path) != ".." else None
        return None

    def initial_load_done(self):
        self._initial_load_complete = True

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if handler := self._key_handlers.get(event.key()):
                if handler(source, event):
                    return True
        elif event.type() == QEvent.Type.FocusIn and self._initial_load_complete:
            if source.parent() in [self.left_panel_widget, self.right_panel_widget]:
                self.set_active_panel(source.parent())
        
        return super().eventFilter(source, event)

    def _handle_tab_key(self, source, event):
        next_panel = self.right_panel_widget if source.parent() == self.left_panel_widget else self.left_panel_widget
        self.set_active_panel(next_panel)
        next_panel.get_file_view().setFocus()
        return True

    def _handle_insert_key(self, source, event):
        model = source.model()
        if hasattr(model, 'toggle_selection_by_index'):
            current_index = source.currentIndex()
            model.toggle_selection_by_index(current_index)
            next_row = current_index.row() + 1
            if next_row < model.rowCount(current_index.parent()):
                next_index = model.index(next_row, current_index.column(), current_index.parent())
                source.setCurrentIndex(next_index)
        return True

    def _handle_home_key(self, source, event):
        root = source.rootIndex() if isinstance(source, QTreeView) else QModelIndex()
        first_index = source.model().index(0, 0, root)
        if first_index.isValid():
            self._select_and_scroll_to(source, first_index)
        return True

    def _handle_end_key(self, source, event):
        root = source.rootIndex() if isinstance(source, QTreeView) else QModelIndex()
        row_count = source.model().rowCount(root)
        if row_count > 0:
            last_index = source.model().index(row_count - 1, 0, root)
            if last_index.isValid():
                self._select_and_scroll_to(source, last_index)
        return True

    def _handle_backspace_key(self, source, event):
        if not self.active_panel_widget.get_path_edit().hasFocus():
            self.go_up_directory()
            return True
        return False

    def _handle_enter_key(self, source, event):
        if not self.active_panel_widget.get_path_edit().hasFocus():
            if selection_model := source.selectionModel():
                if selected_indexes := selection_model.selectedIndexes():
                    self.on_double_clicked(selected_indexes[0], source)
                    return True
        return False

    def _update_path_completions(self, text, panel_widget):
        completer = panel_widget.completer
        if not completer or not completer.model():
            return

        base_path = os.path.dirname(text) or "/"
        while not os.path.isdir(base_path) and base_path != "/":
            base_path = os.path.dirname(base_path)

        try:
            if os.access(base_path, os.R_OK):
                suggestions = [os.path.join(base_path, entry) for entry in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, entry))]
                completer.model().setStringList(suggestions)
        except OSError as e:
            logging.error(f"Error listing directory for completions: {e}")

    def _navigate_from_path_edit(self, panel_widget):
        path = panel_widget.get_path_edit().text()
        self.navigate_to_path(path, panel=panel_widget.get_file_view())

    def navigate_to_path(self, path, panel=None, select_entry_path=None):
        if panel is None:
            panel = self.active_panel_widget.get_file_view()
        
        panel_widget = panel.parent()
        if not os.path.isdir(path):
            show_error_message(self, "Navigation Error", f"Path '{path}' is not a valid directory.")
            return

        panel_widget.get_path_edit().setText(path)
        self.current_paths[panel_widget] = path
        self._select_on_load = os.path.basename(select_entry_path) if select_entry_path else ".."

        model = panel.model()
        if isinstance(model, FlatFileSystemModel):
            model.set_current_path(path)
            model.layoutChanged.emit()
        else:
            index = model.index(path)
            if index.isValid():
                panel.setRootIndex(index)
            else:
                show_error_message(self, "Navigation Error", f"Could not set root to '{path}'.")
                return
        
        self.current_directory_changed.emit(path)
        self.select_item_after_load(panel)
        panel.setFocus()

    def set_view_mode(self, mode):
        if self.view_mode == mode:
            return
        self.view_mode = mode

        left_path = self.current_paths.get(self.left_panel_widget, os.path.expanduser("~"))
        right_path = self.current_paths.get(self.right_panel_widget, os.path.expanduser("~"))

        splitter = self.findChild(QSplitter)
        
        new_left_widget = self.create_panel_widget(mode)
        new_right_widget = self.create_panel_widget(mode)

        splitter.replaceWidget(0, new_left_widget)
        splitter.replaceWidget(1, new_right_widget)
        
        self.left_panel_widget.deleteLater()
        self.right_panel_widget.deleteLater()

        self.left_panel_widget = new_left_widget
        self.right_panel_widget = new_right_widget
        
        self._setup_panel(self.left_panel_widget, left_path)
        self._setup_panel(self.right_panel_widget, right_path)

        self.current_paths = {self.left_panel_widget: left_path, self.right_panel_widget: right_path}

        self.left_panel_widget.get_file_view().installEventFilter(self)
        self.right_panel_widget.get_file_view().installEventFilter(self)

        self.set_active_panel(self.left_panel_widget)

    def load_panel_settings(self):
        """Loads panel paths, active panel, and column widths from settings."""
        if not self.settings_manager:
            return

        default_path = os.path.expanduser("~")
        
        left_panel_path = self.settings_manager.get_setting("leftPanelPath", default_path)
        right_panel_path = self.settings_manager.get_setting("rightPanelPath", default_path)
            
        self.navigate_to_path(left_panel_path, self.left_panel)
        self.navigate_to_path(right_panel_path, self.right_panel)

        active_panel_id = self.settings_manager.get_setting("activePanel", "left")
        self.set_active_panel_by_id(active_panel_id)

        # Column widths are handled by _configure_view_headers when views are created/recreated.
        # Ensure they are applied after navigation.
        self._configure_view_headers(self.left_panel, self.view_mode)
        self._configure_view_headers(self.right_panel, self.view_mode)

        self.initial_load_done() # Signal that initial load is complete

    def save_panel_settings(self):
        """Saves panel paths, active panel, and column widths to settings."""
        if not self.settings_manager:
            return

        default_path = os.path.expanduser("~")
        
        # Get left panel path
        left_panel_model = self.left_panel.model()
        left_panel_root_index = self.left_panel.rootIndex()
        if isinstance(left_panel_model, QFileSystemModel): # For tree view
            left_panel_path = left_panel_model.filePath(left_panel_root_index) if left_panel_root_index.isValid() else default_path
        else: # For flat view (FlatFileSystemModel)
            left_panel_path = self.current_paths.get(self.left_panel_widget, default_path)
        
        # Get right panel path
        right_panel_model = self.right_panel.model()
        right_panel_root_index = self.right_panel.rootIndex()
        if isinstance(right_panel_model, QFileSystemModel): # For tree view
            right_panel_path = right_panel_model.filePath(right_panel_root_index) if right_panel_root_index.isValid() else default_path
        else: # For flat view (FlatFileSystemModel)
            right_panel_path = self.current_paths.get(self.right_panel_widget, default_path)

        # Save paths
        self.settings_manager.set_setting("leftPanelPath", left_panel_path)
        self.settings_manager.set_setting("rightPanelPath", right_panel_path)
        
        # Save active panel
        self.settings_manager.set_setting("activePanel", self.get_active_panel_id())

        # Save column widths (already handled by _on_header_section_resized, but ensure it's saved on close)
        column_widths = self.get_column_widths()
        if "table_column_widths" in column_widths:
            self.settings_manager.set_setting("table_column_widths", column_widths["table_column_widths"])
        if "tree_column_widths" in column_widths:
            self.settings_manager.set_setting("tree_column_widths", column_widths["tree_column_widths"])
