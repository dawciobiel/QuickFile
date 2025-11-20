import os
import stat

from PyQt5.QtCore import Qt, QModelIndex, pyqtSignal, QEvent
from PyQt5.QtWidgets import QWidget, QTreeView, QFileSystemModel, QSplitter, QVBoxLayout


class CustomTreeView(QTreeView):
    """Niestandardowy QTreeView, który ignoruje klawisze F1-F10, pozwalając im propagować dalej."""
    def keyPressEvent(self, event):
        # print(f"CustomTreeView keyPressEvent: KeyPress event detected. Key: {event.key()}, Source: {self.objectName() if self.objectName() else self.__class__.__name__}")
        if event.key() >= Qt.Key_F1 and event.key() <= Qt.Key_F12:
            # print(f"CustomTreeView: Ignoring F-key event {event.key()}")
            event.ignore() # Ignoruj zdarzenie, aby mogło propagować dalej
            return
        super().keyPressEvent(event)


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.active_panel = None
        self.current_selected_path = None
        self.current_paths = {}  # Słownik do śledzenia ścieżek dla paneli

        self.left_panel = self.create_file_view()
        self.right_panel = self.create_file_view()

        # home_path = os.path.expanduser("~") # Przeniesiono do load_settings w MainWindow
        # self.current_paths[self.left_panel] = self.left_panel.model().index(home_path)
        # self.current_paths[self.right_panel] = self.right_panel.model().index(home_path)

        # self.left_panel.setRootIndex(self.current_paths[self.left_panel])
        # self.right_panel.setRootIndex(self.current_paths[self.right_panel])

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.set_active_panel(self.left_panel)

    def create_file_view(self):
        model = CustomFileSystemModel()
        model.setRootPath(os.path.expanduser("~")) # Domyślny root, zostanie nadpisany przez ustawienia

        view = CustomTreeView() # Użyj CustomTreeView
        view.setModel(model)

        view.setColumnWidth(0, 250)
        view.setColumnWidth(1, 100)
        view.setColumnWidth(2, 150)
        view.setColumnWidth(3, 150)
        view.setColumnWidth(4, 200)

        view.selectionModel().currentChanged.connect(self.update_current_selected_path)
        # view.installEventFilter(self) # Filtr zdarzeń nie jest już potrzebny tutaj
        view.installEventFilter(self)
        view.doubleClicked.connect(self.on_double_clicked)

        return view

    def on_double_clicked(self, index: QModelIndex):
        """Obsługa podwójnego kliknięcia - nawigacja do folderu lub otwarcie pliku."""
        view = self.sender()
        file_path = view.model().filePath(index)
        if view.model().isDir(index):
            self.navigate_to_path(file_path, view)
        else:
            self.file_selected.emit(file_path) # Emituj sygnał do otwarcia pliku zewnętrznie

    def go_up_directory(self):
        """Przechodzi do katalogu nadrzędnego w aktywnym panelu."""
        if self.active_panel:
            current_index = self.current_paths.get(self.active_panel)
            if current_index and current_index.isValid():
                parent_index = current_index.parent()
                if parent_index.isValid():
                    self.navigate_to_path(self.active_panel.model().filePath(parent_index), self.active_panel)
                else:
                    root_path = self.active_panel.model().rootPath()
                    if root_path and os.path.dirname(root_path) != root_path:
                        new_root_path = os.path.dirname(root_path)
                        self.navigate_to_path(new_root_path, self.active_panel)

    def refresh_view(self):
        """Odświeża widok aktywnego panelu."""
        if self.active_panel:
            current_index = self.current_paths.get(self.active_panel)
            if current_index and current_index.isValid():
                self.navigate_to_path(self.active_panel.model().filePath(current_index), self.active_panel)

    def navigate_to_path(self, path, panel=None):
        """Nawiguje aktywny panel do podanej ścieżki."""
        if panel is None:
            panel = self.active_panel

        if panel and os.path.exists(path) and os.path.isdir(path):
            index = panel.model().index(path)
            if index.isValid():
                panel.setRootIndex(index)
                self.current_paths[panel] = index
                self.current_directory_changed.emit(path)
            else:
                self.current_directory_changed.emit(f"Błąd: Nie można nawigować do '{path}'")
        else:
            self.current_directory_changed.emit(f"Błąd: Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")

    def set_panel_path(self, panel, path):
        """Ustawia ścieżkę dla podanego panelu."""
        if panel and os.path.exists(path) and os.path.isdir(path):
            index = panel.model().index(path)
            if index.isValid():
                panel.setRootIndex(index)
                self.current_paths[panel] = index
                if panel == self.active_panel: # Emituj tylko jeśli to aktywny panel
                    self.current_directory_changed.emit(path)
            else:
                if panel == self.active_panel:
                    self.current_directory_changed.emit(f"Błąd: Nie można ustawić ścieżki '{path}'")
        else:
            if panel == self.active_panel:
                self.current_directory_changed.emit(f"Błąd: Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")

    def set_active_panel(self, panel):
        if self.active_panel:
            self.active_panel.setStyleSheet("") # Reset style sheet
            self.active_panel.clearSelection()
        self.active_panel = panel
        self.active_panel.setStyleSheet("QTreeView { border: 1px solid blue; }") # Highlight active
        current_index = self.current_paths.get(self.active_panel)
        if current_index and current_index.isValid():
            self.current_directory_changed.emit(self.active_panel.model().filePath(current_index))

    def update_current_selected_path(self, current: QModelIndex, previous: QModelIndex):
        if current.isValid():
            self.current_selected_path = current.model().filePath(current)
            # Nie emitujemy już file_selected tutaj, bo to robi on_double_clicked
            # if not current.model().isDir(current):
            #     self.file_selected.emit(self.current_selected_path)

    def eventFilter(self, source, event):
        if event.type() == QEvent.FocusIn:
            if source in [self.left_panel, self.right_panel]:
                self.set_active_panel(source)
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
