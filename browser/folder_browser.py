import os
import stat

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QFileSystemModel, QSplitter, QVBoxLayout, QWidget


class FileBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick File")

        # Globalne pola
        self.active_panel = None  # Wskaźnik na aktywny panel
        self.current_selected_path = None  # Ścieżka aktualnie wybranego pliku/folderu

        # Ustawienie widoków plików
        self.left_panel = self.create_file_view()
        self.right_panel = self.create_file_view()

        # Dodanie paneli do splittera
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)

        # Layout główny
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Ustawienie lewego panelu jako aktywnego na starcie
        self.set_active_panel(self.left_panel)

    def create_file_view(self):
        # Model systemu plików
        model = CustomFileSystemModel()
        model.setRootPath("")  # Ustaw root katalogu

        # Widok plików
        view = QTreeView()
        view.setModel(model)
        view.setRootIndex(model.index(""))  # Ustawienie początkowego folderu

        # Wyświetl kolumny: Nazwa, Rozmiar, Typ, Data modyfikacji, Uprawnienia
        view.setColumnWidth(0, 250)  # Nazwa
        view.setColumnWidth(1, 100)  # Rozmiar
        view.setColumnWidth(2, 150)  # Typ
        view.setColumnWidth(3, 150)  # Data modyfikacji
        view.setColumnWidth(4, 200)  # Uprawnienia (nasza kolumna)

        # Obsługa zdarzeń
        view.selectionModel().currentChanged.connect(self.update_current_selected_path)
        view.installEventFilter(self)  # Monitorowanie aktywności

        return view

    def set_active_panel(self, panel):
        """Ustaw aktywny panel"""
        self.active_panel = panel

    def update_current_selected_path(self, current: QModelIndex, previous: QModelIndex):
        """Aktualizuj wybraną ścieżkę"""
        if current.isValid():
            self.current_selected_path = current.model().filePath(current)
            print(f"Aktualnie wybrana ścieżka: {self.current_selected_path}")

    def eventFilter(self, source, event):
        """Wykrywanie aktywnego panelu"""
        if event.type() == event.FocusIn and (source == self.left_panel or source == self.right_panel):
            self.set_active_panel(source)
            print(f"Aktywny panel: {'lewy' if source == self.left_panel else 'prawy'}")
        return super().eventFilter(source, event)


class CustomFileSystemModel(QFileSystemModel):
    def columnCount(self, parent=None):
        """Zwiększ liczbę kolumn o 1 na potrzeby kolumny Uprawnienia"""
        return super().columnCount(parent) + 1

    def data(self, index, role=Qt.DisplayRole):
        """Dostarcz dane dla kolumny Uprawnienia"""
        if role == Qt.DisplayRole and index.column() == 4:  # Kolumna "Uprawnienia"
            file_path = self.filePath(index)
            return self.get_permissions(file_path)
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Zmień nazwę nagłówka dla kolumny Uprawnienia"""
        if role == Qt.DisplayRole and section == 4:
            return "Permissions"
        return super().headerData(section, orientation, role)

    @staticmethod
    def get_permissions(file_path):
        """Zwróć uprawnienia pliku/folderu w formacie rwx"""
        try:
            mode = os.stat(file_path).st_mode
            permissions = (("r" if mode & stat.S_IRUSR else "-") + ("w" if mode & stat.S_IWUSR else "-") + (
                "x" if mode & stat.S_IXUSR else "-") + ("r" if mode & stat.S_IRGRP else "-") + (
                               "w" if mode & stat.S_IWGRP else "-") + ("x" if mode & stat.S_IXGRP else "-") + (
                               "r" if mode & stat.S_IROTH else "-") + ("w" if mode & stat.S_IWOTH else "-") + (
                               "x" if mode & stat.S_IXOTH else "-"))
            return permissions
        except Exception as e:
            return "N/A"


if __name__ == "__main__":
    app = QApplication([])
    window = FileBrowser()
    window.resize(800, 600)
    window.show()
    app.exec_()
