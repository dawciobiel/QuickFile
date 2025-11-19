import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QWidget, QHBoxLayout

# Consts
WINDOW_TITLE = "File Manager - by dawciobiel"
APPLICATION_VERSION = "v0.1"
WINDOW_GEOMETRY = (100, 50, 1700, 900)
FILE_LIST_FONT_SIZE = "font-size: 22px;"
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

        # Lewa część z tabelą plików
        self.file_table_left = QTableWidget()
        self.file_table_left.setColumnCount(5)
        self.file_table_left.setHorizontalHeaderLabels(["Name", "Ext", "Size", "Date", "Attr"])
        self.file_table_left.setColumnWidth(0, 300)  # Kolumna "Name" - szerokość 300 pikseli
        self.file_table_left.setColumnWidth(1, 50)   # Kolumna "File Extension" - szerokość 150 pikseli
        self.file_table_left.setColumnWidth(2, 100)  # Kolumna "Size" - szerokość 100 pikseli
        self.file_table_left.setColumnWidth(3, 200)  # Kolumna "Date" - szerokość 200 pikseli
        self.file_table_left.setColumnWidth(4, 150)  # Kolumna "Attributes" - szerokość 150 pikseli
        self.file_table_left.setStyleSheet(FILE_LIST_FONT_SIZE)
        self.file_table_left.cellDoubleClicked.connect(self.enter_directory_left)
        self.update_file_table(self.file_table_left, self.current_path_left)

        # Prawa część z tabelą plików
        self.file_table_right = QTableWidget()
        self.file_table_right.setColumnCount(5)
        self.file_table_right.setHorizontalHeaderLabels(["Name", "Ext", "Size", "Date", "Attr"])
        self.file_table_right.setColumnWidth(0, 300)  # Kolumna "Name" - szerokość 300 pikseli
        self.file_table_right.setColumnWidth(1, 50)   # Kolumna "File Extension" - szerokość 150 pikseli
        self.file_table_right.setColumnWidth(2, 100)  # Kolumna "Size" - szerokość 100 pikseli
        self.file_table_right.setColumnWidth(3, 200)  # Kolumna "Date" - szerokość 200 pikseli
        self.file_table_right.setColumnWidth(4, 150)  # Kolumna "Attributes" - szerokość 150 pikseli
        self.file_table_right.setStyleSheet(FILE_LIST_FONT_SIZE)
        self.file_table_right.cellDoubleClicked.connect(self.enter_directory_right)
        self.update_file_table(self.file_table_right, self.current_path_right)

        # Dodanie tabel do layoutu
        main_layout.addWidget(self.file_table_left)
        main_layout.addWidget(self.file_table_right)

    def update_file_table(self, file_table, path):
        """Aktualizuje zawartość tabeli plików i folderów."""
        file_table.setRowCount(0)
        try:
            items = os.listdir(path)
        except PermissionError:
            file_table.setRowCount(1)
            file_table.setItem(0, 0, QTableWidgetItem("No permissions for this directory"))
            return
        except FileNotFoundError:
            file_table.setRowCount(1)
            file_table.setItem(0, 0, QTableWidgetItem("Directory does not exist"))
            return

        # Rozdziel foldery i pliki
        folders = sorted([item for item in items if os.path.isdir(os.path.join(path, item))])
        files = sorted([item for item in items if os.path.isfile(os.path.join(path, item))])

        for folder in folders + files:
            is_folder = os.path.isdir(os.path.join(path, folder))
            row_position = file_table.rowCount()
            file_table.insertRow(row_position)

            # Name
            name_item = QTableWidgetItem(f"{BRACKET_START}{folder}{BRACKET_END}" if is_folder else folder)
            if is_folder:
                name_item.setForeground(QColor("white"))
            file_table.setItem(row_position, 0, name_item)

            # File Extension
            ext = "" if is_folder else os.path.splitext(folder)[1]
            file_table.setItem(row_position, 1, QTableWidgetItem(ext))

            # Size
            size = "-" if is_folder else str(os.path.getsize(os.path.join(path, folder)))
            file_table.setItem(row_position, 2, QTableWidgetItem(size))

            # Date
            try:
                mtime = os.path.getmtime(os.path.join(path, folder))
                date = Qt.QDateTime.fromSecsSinceEpoch(int(mtime)).toString("yyyy-MM-dd HH:mm:ss")
            except Exception:
                date = "-"
            file_table.setItem(row_position, 3, QTableWidgetItem(date))

            # Attributes
            attributes = "Folder" if is_folder else "File"
            file_table.setItem(row_position, 4, QTableWidgetItem(attributes))

    def enter_directory_left(self, row, column):
        """Obsługuje wejście do katalogu po kliknięciu w tabeli po lewej."""
        selected_item = self.file_table_left.item(row, 0).text()
        if selected_item.startswith(BRACKET_START) and selected_item.endswith(BRACKET_END):
            selected_item = selected_item[1:-1]  # Usuń nawiasy z nazwy folderu
        new_path = os.path.join(self.current_path_left, selected_item)
        if os.path.isdir(new_path):
            self.current_path_left = new_path
            self.update_file_table(self.file_table_left, self.current_path_left)

    def enter_directory_right(self, row, column):
        """Obsługuje wejście do katalogu po kliknięciu w tabeli po prawej."""
        selected_item = self.file_table_right.item(row, 0).text()
        if selected_item.startswith(BRACKET_START) and selected_item.endswith(BRACKET_END):
            selected_item = selected_item[1:-1]  # Usuń nawiasy z nazwy folderu
        new_path = os.path.join(self.current_path_right, selected_item)
        if os.path.isdir(new_path):
            self.current_path_right = new_path
            self.update_file_table(self.file_table_right, self.current_path_right)

    def keyPressEvent(self, event):
        """Obsługuje naciśnięcia klawiszy, w tym BACKSPACE do przechodzenia do katalogu nadrzędnego."""
        if event.key() == Qt.Key_Backspace:
            # Przejście do katalogu nadrzędnego w obu panelach
            parent_path_left = os.path.dirname(self.current_path_left)
            if os.path.exists(parent_path_left):
                self.current_path_left = parent_path_left
                self.update_file_table(self.file_table_left, self.current_path_left)

            parent_path_right = os.path.dirname(self.current_path_right)
            if os.path.exists(parent_path_right):
                self.current_path_right = parent_path_right
                self.update_file_table(self.file_table_right, self.current_path_right)
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileBrowser()
    window.show()
    sys.exit(app.exec_())
