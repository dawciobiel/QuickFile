from PyQt5.QtWidgets import QApplication

from folder_browser import FolderBrowser

if __name__ == "__main__":
    app = QApplication([])
    window = FolderBrowser()
    window.resize(800, 600)
    window.show()
    app.exec_()
