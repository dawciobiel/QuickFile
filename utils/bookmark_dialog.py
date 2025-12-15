from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from app.translation_manager import translation_manager # Import our new manager

class BookmarkDialog(QDialog):
    def __init__(self, bookmarks, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("BookmarkDialog", "Bookmarks"))
        self.bookmarks = bookmarks
        self.selected_bookmark = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(translation_manager.translate("BookmarkDialog", "Filter bookmarks..."))
        self.layout.addWidget(self.filter_input)

        self.bookmarks_list = QListWidget()
        self.layout.addWidget(self.bookmarks_list)

        self.filter_input.textChanged.connect(self.filter_bookmarks)
        self.bookmarks_list.itemDoubleClicked.connect(self.accept_selection)
        self.bookmarks_list.itemActivated.connect(self.accept_selection)

        self.populate_bookmarks()

        # Set a new default size
        self.resize(600, 400) # Increased width and a reasonable height

    def populate_bookmarks(self, filter_text=""):
        self.bookmarks_list.clear()
        for bookmark in self.bookmarks:
            if filter_text.lower() in bookmark.lower():
                item = QListWidgetItem(bookmark)
                self.bookmarks_list.addItem(item)

    def filter_bookmarks(self, text):
        self.populate_bookmarks(text)

    def accept_selection(self, item):
        self.selected_bookmark = item.text()
        self.accept()
