from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from app.translation_manager import translation_manager


class BookmarkDialog(QDialog):
    def __init__(self, bookmarks, parent=None):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/bookmark_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("BookmarkDialog", "Bookmarks"))
        self.bookmarks = bookmarks
        self.selected_bookmark = None

        self.filter_input.setPlaceholderText(translation_manager.translate("BookmarkDialog", "Filter bookmarks..."))

        self.filter_input.textChanged.connect(self.filter_bookmarks)
        self.bookmarks_list.itemDoubleClicked.connect(self.accept_selection)
        self.bookmarks_list.itemActivated.connect(self.accept_selection)

        self.populate_bookmarks()

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
