from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from browser.folder_browser import FolderBrowser
from panels.menu_panel import MenuPanel
from file_operations.file_manager import FileManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick File")
        self.resize(1200, 800)

        # Inicjalizacja menedżera plików
        self.file_manager = FileManager()

        # Inicjalizacja paska menu i paska stanu
        self.menu_panel = MenuPanel(self)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Gotowy")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.folder_browser = FolderBrowser()
        layout.addWidget(self.folder_browser)
