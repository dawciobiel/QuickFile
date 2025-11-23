import os
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QEvent
from PyQt6.QtWidgets import QWidget, QTableView, QVBoxLayout, QAbstractItemView, QHeaderView, QSplitter, QTreeView
from PyQt6.QtGui import QFileSystemModel, QColor, QPalette
# from browser.flat_view_proxy_model import FlatViewProxyModel # Old import
from browser.flat_file_system_model import FlatFileSystemModel # New import

class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self, view_mode="flat", parent=None):
        super().__init__(parent)

        self.active_panel = None
        self.current_selected_path = None
        self.current_paths = {} # To track paths for each panel
        self.view_mode = view_mode # Store view mode

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

        self.set_active_panel(self.left_panel)

    def create_file_view(self, view_mode):
        if view_mode == "flat":
            view = QTableView()
            model = FlatFileSystemModel(self) # New custom model
            view.setModel(model)
        else: # view_mode == "tree" (QFileSystemModel)
            model = QFileSystemModel()
            model.setRootPath(os.path.expanduser("~"))
            view = QTreeView() # Use QTreeView for tree mode
            view.setModel(model)
            view.setRootIndex(model.index(os.path.expanduser("~")))

        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        if isinstance(view, QTableView): # Apply only to QTableView
            view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Modyfikacja palety dla zaznaczonych elementów - zakomentowano, ponieważ powoduje segmentation fault w PyQt6
        # palette = view.palette()
        # palette.setColor(QPalette.ColorRole.Highlight, QColor("#ADD8E6")) # Jasnoniebieskie tło zaznaczenia
        # palette.setColor(QPalette.ColorRole.HighlightedText, QColor("orange")) # Pomarańczowy tekst zaznaczenia
        # view.setPalette(palette)

        view.doubleClicked.connect(lambda index: self.on_double_clicked(index, view))
        view.selectionModel().currentChanged.connect(lambda current, previous: self.update_current_selection(current, previous, view))
        view.setMouseTracking(True) # Enable mouse tracking for focus events
        view.installEventFilter(self) # Install event filter for focus events

        return view
    
    def on_double_clicked(self, index: QModelIndex, view: QTableView):
        model = view.model()
        if model.isDir(index):
            new_path = model.filePath(index)
            if isinstance(model, FlatFileSystemModel):
                model.set_current_path(new_path)
            else: # QFileSystemModel
                view.setRootIndex(index)
            self.current_paths[view] = new_path
            self.current_directory_changed.emit(new_path)
        else:
            self.file_selected.emit(model.filePath(index))

    def update_current_selection(self, current: QModelIndex, previous: QModelIndex, view: QTableView):
        if current.isValid():
            self.current_selected_path = view.model().filePath(current)
            # No need to emit current_directory_changed here, it's handled by on_double_clicked
    
    def navigate_to_path(self, path, panel=None):
        if panel is None:
            panel = self.active_panel

        if panel and os.path.exists(path) and os.path.isdir(path):
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
                    self.current_directory_changed.emit(f"Error: Could not set directory to '{path}'.")
        else:
            self.current_directory_changed.emit(f"Error: Path '{path}' is invalid or does not exist.")

    def set_panel_path(self, panel, path):
        self.navigate_to_path(path, panel)

    def go_up_directory(self):
        if self.active_panel:
            current_path = self.current_paths.get(self.active_panel)
            if current_path:
                parent_path = os.path.dirname(current_path)
                if parent_path and parent_path != current_path:
                    self.navigate_to_path(parent_path, self.active_panel)

    def refresh_view(self):
        if self.active_panel:
            current_path = self.current_paths.get(self.active_panel)
            if current_path:
                self.navigate_to_path(current_path, self.active_panel)
    
    def set_active_panel(self, panel):
        if self.active_panel:
            self.active_panel.setStyleSheet("") # Reset style sheet
            self.active_panel.clearSelection()
        self.active_panel = panel
        self.active_panel.setStyleSheet("QTableView { border: 1px solid blue; }") # Highlight active
        current_path = self.current_paths.get(self.active_panel)
        if current_path: # current_path is now a string
            self.current_directory_changed.emit(current_path)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.FocusIn:
            if source in [self.left_panel, self.right_panel]:
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