import os
import stat
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QSplitter, QMessageBox, QInputDialog, QTreeView, QFileSystemModel
)
from PyQt5.QtCore import Qt


class CustomFileSystemModel(QFileSystemModel):
    """Rozszerzony QFileSystemModel, dodający kolumnę z uprawnieniami."""
    def columnCount(self, parent=None):
        """Zwiększamy liczbę kolumn o jedną dla kolumny 'Permissions'."""
        return super().columnCount(parent) + 1

    def data(self, index, role=Qt.DisplayRole):
        """Zwracamy dane dla kolumny 'Permissions'."""
        if index.column() == 4 and role == Qt.DisplayRole:  # Kolumna z uprawnieniami
            file_path = self.filePath(index)
            return self.get_permissions(file_path)
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Nagłówek dla kolumny 'Permissions'."""
        if role == Qt.DisplayRole and section == 4:
            return "Permissions"
        return super().headerData(section, orientation, role)

    @staticmethod
    def get_permissions(file_path):
        """Zwraca uprawnienia w formacie: typ + 'rwx rwx rwx'."""
        try:
            mode = os.stat(file_path).st_mode

            # Typ pliku
            if stat.S_ISDIR(mode):
                file_type = "d"  # Katalog
            elif stat.S_ISLNK(mode):
                file_type = "l"  # Dowiązanie symboliczne
            elif stat.S_ISREG(mode):
                file_type = "-"  # Plik zwykły
            elif stat.S_ISCHR(mode):
                file_type = "c"  # Urządzenie znakowe
            elif stat.S_ISBLK(mode):
                file_type = "b"  # Urządzenie blokowe
            elif stat.S_ISSOCK(mode):
                file_type = "s"  # Socket
            elif stat.S_ISFIFO(mode):
                file_type = "p"  # FIFO (kolejka nazwijna)
            else:
                file_type = "?"  # Nieznany typ pliku

            # Uprawnienia
            user = (
                    ("r" if mode & stat.S_IRUSR else "-") +
                    ("w" if mode & stat.S_IWUSR else "-") +
                    ("x" if mode & stat.S_IXUSR else "-")
            )
            group = (
                    ("r" if mode & stat.S_IRGRP else "-") +
                    ("w" if mode & stat.S_IWGRP else "-") +
                    ("x" if mode & stat.S_IXGRP else "-")
            )
            others = (
                    ("r" if mode & stat.S_IROTH else "-") +
                    ("w" if mode & stat.S_IWOTH else "-") +
                    ("x" if mode & stat.S_IXOTH else "-")
            )

            # Zwracanie wynikowego ciągu
            return f"{file_type} {user} {group} {others}"
        except Exception as e:
            return "N/A"



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuickFile by dawciobiel")
        self.setGeometry(100, 100, 800, 600)

        # Menu bar setup
        self.menu_bar = self.menuBar()
        self.setup_menu_bar()

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Splitter for dynamic resizing
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_panel = FilePanel()
        self.right_panel = FilePanel()
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)

        # Add splitter to layout
        self.main_layout.addWidget(self.splitter)

        # Button panel at the bottom
        self.button_panel = ButtonPanel()
        self.main_layout.addWidget(self.button_panel)
        self.main_layout.setAlignment(self.button_panel, Qt.AlignBottom)

        # Ensure splitter takes all available space
        self.main_layout.setStretchFactor(self.splitter, 1)
        self.main_layout.setStretchFactor(self.button_panel, 0)

    def setup_menu_bar(self):
        file_menu = self.menu_bar.addMenu("File")
        view_menu = self.menu_bar.addMenu("View")
        help_menu = self.menu_bar.addMenu("Help")

        file_menu.addAction("Exit", self.close)
        view_menu.addAction("Refresh", self.refresh_panels)
        help_menu.addAction("About", self.show_about)

    def refresh_panels(self):
        self.left_panel.refresh()
        self.right_panel.refresh()

    def show_about(self):
        QMessageBox.information(self, "About", "Simple File Manager\nCreated using PyQt5")


class FilePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.file_view = QTreeView()
        self.file_model = CustomFileSystemModel()  # Używamy niestandardowego modelu
        self.file_model.setRootPath("")
        self.file_view.setModel(self.file_model)
        self.file_view.setRootIndex(self.file_model.index(""))

        # Ustawienia kolumn
        self.file_view.setColumnWidth(0, 250)  # Nazwa
        self.file_view.setColumnWidth(1, 100)  # Rozmiar
        self.file_view.setColumnWidth(2, 150)  # Typ
        self.file_view.setColumnWidth(3, 150)  # Data modyfikacji
        self.file_view.setColumnWidth(4, 200)  # Uprawnienia

        self.layout.addWidget(self.file_view)

    def refresh(self):
        self.file_view.setRootIndex(self.file_model.index(""))


class ButtonPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.rename_button = QPushButton("F2: Rename")
        self.view_button = QPushButton("F3: View")
        self.edit_button = QPushButton("F4: Edit")
        self.copy_button = QPushButton("F5: Copy")
        self.move_button = QPushButton("F6: Move")
        self.new_folder_button = QPushButton("F7: New Folder")
        self.delete_button = QPushButton("F8: Delete")
        self.menu_button = QPushButton("F9: Menu")
        self.quit_button = QPushButton("F10: Quit")

        buttons = [
            self.rename_button, self.view_button, self.edit_button, self.copy_button,
            self.move_button, self.new_folder_button, self.delete_button,
            self.menu_button, self.quit_button
        ]

        for button in buttons:
            self.layout.addWidget(button)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
