from PyQt6.QtWidgets import QApplication
from core.main_window import MainWindow
if __name__ == "__main__":
    app = QApplication([])

    window = MainWindow()
    app.installEventFilter(window)
    window.show()
    app.exec()
