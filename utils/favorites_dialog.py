from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QListWidgetItem
from app.translation_manager import translation_manager

class FavoritesDialog(QDialog):
    def __init__(self, favorites, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/favorites_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("FavoritesDialog", "Favorites"))
        self.favorites = favorites
        self.selected_favorite = None

        self._init_ui()

    def _init_ui(self):
        self.filter_input.setPlaceholderText(translation_manager.translate("FavoritesDialog", "Filter favorites..."))
        
        self.filter_input.textChanged.connect(self.filter_favorites)
        self.bookmarks_list.itemDoubleClicked.connect(self.accept_selection)
        self.bookmarks_list.itemActivated.connect(self.accept_selection)

        self.populate_favorites()

    def populate_favorites(self, filter_text=""):
        self.bookmarks_list.clear()
        for favorite in self.favorites:
            if filter_text.lower() in favorite.lower():
                item = QListWidgetItem(favorite)
                self.bookmarks_list.addItem(item)

    def filter_favorites(self, text):
        self.populate_favorites(text)

    def accept_selection(self, item):
        self.selected_favorite = item.text()
        self.accept()
