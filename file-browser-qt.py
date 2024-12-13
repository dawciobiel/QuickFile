import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QListWidget, QScrollArea, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt

# Consts
WINDOW_TITLE = "File Manager - by dawciobiel"
APPLICATION_VERSION = "v0.1"
WINDOW_GEOMETRY = (100, 50, 1700, 900)
FONT_STYLE = "font-size: 24px;"
BRACKET_START = "["
BRACKET_END = "]"

class FileBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE + " " + APPLICATION_VERSION)
        self.setGeometry(*WINDOW_GEOMETRY)

        # Ścieżka początkowa
        self.current_path_left = "/"
        self.current_path_right = "/"

        # Główny widget i layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # Lewa część z listą plików
        self.file_list_left = QListWidget()
        self.file_list_left.setStyleSheet(FONT_STYLE)
        self.file_list_left.itemActivated.connect(self.enter_directory_left)
        self.update_file_list(self.file_list_left, self.current_path_left)

        # Prawa część z listą plików
        self.file_list_right = QListWidget()
        self.file_list_right.setStyleSheet(FONT_STYLE)
        self.file_list_right.itemActivated.connect(self.enter_directory_right)
        self.update_file_list(self.file_list_right, self.current_path_right)

        # Dodanie list do layoutu
        main_layout.addWidget(self.file_list_left)
        main_layout.addWidget(self.file_list_right)

    def update_file_list(self, file_list, path):
        """Aktualizuje zawartość listy plików i folderów, sortując je."""
        file_list.clear()
        try:
            items = os.listdir(path)
        except PermissionError:
            items = ["No permissions for this directory"]
            file_list.addItems(items)
            return
        except FileNotFoundError:
            items = ["Directory does not exist"]
            file_list.addItems(items)
            return

        # Rozdziel foldery i pliki
        folders = sorted([f"{BRACKET_START}{item}{BRACKET_END}" for item in items if os.path.isdir(os.path.join(path, item))])
        files = sorted([item for item in items if os.path.isfile(os.path.join(path, item))])

        # Dodaj foldery i pliki do listy
        file_list.addItems(folders)
        file_list.addItems(files)

    def enter_directory_left(self, item):
        """Obsługuje wejście do katalogu po naciśnięciu Enter na elemencie listy w lewym panelu."""
        selected_item = item.text()
        if selected_item.startswith(BRACKET_START) and selected_item.endswith(BRACKET_END):
            selected_item = selected_item[1:-1]  # Usuń nawiasy z nazwy folderu
        new_path = os.path.join(self.current_path_left, selected_item)
        if os.path.isdir(new_path):
            self.current_path_left = new_path
            self.update_file_list(self.file_list_left, self.current_path_left)

    def enter_directory_right(self, item):
        """Obsługuje wejście do katalogu po naciśnięciu Enter na elemencie listy w prawym panelu."""
        selected_item = item.text()
        if selected_item.startswith(BRACKET_START) and selected_item.endswith(BRACKET_END):
            selected_item = selected_item[1:-1]  # Usuń nawiasy z nazwy folderu
        new_path = os.path.join(self.current_path_right, selected_item)
        if os.path.isdir(new_path):
            self.current_path_right = new_path
            self.update_file_list(self.file_list_right, self.current_path_right)

    def keyPressEvent(self, event):
        """Obsługuje naciśnięcia klawiszy, w tym BACKSPACE do przechodzenia do katalogu nadrzędnego."""
        if event.key() == Qt.Key_Backspace:
            # Przejście do katalogu nadrzędnego w obu panelach
            parent_path_left = os.path.dirname(self.current_path_left)
            if os.path.exists(parent_path_left):
                self.current_path_left = parent_path_left
                self.update_file_list(self.file_list_left, self.current_path_left)

            parent_path_right = os.path.dirname(self.current_path_right)
            if os.path.exists(parent_path_right):
                self.current_path_right = parent_path_right
                self.update_file_list(self.file_list_right, self.current_path_right)
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileBrowser()
    window.show()
    sys.exit(app.exec_())