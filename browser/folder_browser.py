import os
import stat

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QWidget, QTreeView, QFileSystemModel, QSplitter, QVBoxLayout


class FolderBrowser(QWidget):
    def __init__(self):
        super().__init__()

        self.active_panel = None
        self.current_selected_path = None
        self.current_paths = {}  # Słownik do śledzenia ścieżek dla paneli

        self.left_panel = self.create_file_view()
        self.right_panel = self.create_file_view()

        home_path = os.path.expanduser("~")
        self.current_paths[self.left_panel] = self.left_panel.model().index(home_path)
        self.current_paths[self.right_panel] = self.right_panel.model().index(home_path)

        self.left_panel.setRootIndex(self.current_paths[self.left_panel])
        self.right_panel.setRootIndex(self.current_paths[self.right_panel])

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.set_active_panel(self.left_panel)

    def create_file_view(self):
        model = CustomFileSystemModel()
        model.setRootPath(os.path.expanduser("~"))

        view = QTreeView()
        view.setModel(model)

        view.setColumnWidth(0, 250)
        view.setColumnWidth(1, 100)
        view.setColumnWidth(2, 150)
        view.setColumnWidth(3, 150)
        view.setColumnWidth(4, 200)

        view.selectionModel().currentChanged.connect(self.update_current_selected_path)
        view.installEventFilter(self)
        view.doubleClicked.connect(self.on_double_clicked)

        return view

    def on_double_clicked(self, index: QModelIndex):
        """Obsługa podwójnego kliknięcia - nawigacja do folderu."""
        view = self.sender()
        if view.model().isDir(index):
            view.setRootIndex(index)
            self.current_paths[view] = index

    def set_active_panel(self, panel):
        self.active_panel = panel

    def update_current_selected_path(self, current: QModelIndex, previous: QModelIndex):
        if current.isValid():
            self.current_selected_path = current.model().filePath(current)
            print(f"Aktualnie wybrana ścieżka: {self.current_selected_path}")

    def eventFilter(self, source, event):
        if event.type() == event.FocusIn and (source == self.left_panel or source == self.right_panel):
            self.set_active_panel(source)
            print(f"Aktywny panel: {'lewy' if source == self.left_panel else 'prawy'}")
        return super().eventFilter(source, event)


class CustomFileSystemModel(QFileSystemModel):
    def columnCount(self, parent=None):
        return super().columnCount(parent) + 1

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() == 4:
            file_path = self.filePath(index)
            return self.get_permissions(file_path)
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and section == 4:
            return "Permissions"
        return super().headerData(section, orientation, role)

    @staticmethod
    def get_permissions(file_path):
        try:
            mode = os.stat(file_path).st_mode
            permissions = (("r" if mode & stat.S_IRUSR else "-") + ("w" if mode & stat.S_IWUSR else "-") + (
                "x" if mode & stat.S_IXUSR else "-") + ("r" if mode & stat.S_IRGRP else "-") + (
                               "w" if mode & stat.S_IWGRP else "-") + ("x" if mode & stat.S_IXGRP else "-") + (
                               "r" if mode & stat.S_IROTH else "-") + ("w" if mode & stat.S_IWOTH else "-") + (
                               "x" if mode & stat.S_IXOTH else "-"))
            return permissions
        except Exception:
            return "N/A"
