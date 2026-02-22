# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QAbstractItemView
from quickfile.app.translation_manager import translation_manager
from quickfile.favorites.favorites_manager import FavoritesManager
from quickfile.utils.resource_path import get_resource_path

class FavoritesDialog(QDialog):
    def __init__(self, favorites, parent=None):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/favorites_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("FavoritesDialog", "Favorites"))
        self.favorites = favorites
        self.selected_favorite = None
        self.favorites_manager = FavoritesManager()

        self._init_ui()

    def _init_ui(self):
        self.filter_input.setPlaceholderText(translation_manager.translate("FavoritesDialog", "Filter favorites..."))
        self.bookmarks_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        self.filter_input.textChanged.connect(self.filter_favorites)
        self.bookmarks_list.itemDoubleClicked.connect(self.accept_selection)
        self.bookmarks_list.itemActivated.connect(self.accept_selection)
        self.delete_button.clicked.connect(self.delete_selected_favorites)
        self.delete_button.setText(translation_manager.translate("FavoritesDialog", "Delete"))
        self.close_button.clicked.connect(self.reject)
        self.close_button.setText(translation_manager.translate("FavoritesDialog", "Close"))

        self.populate_favorites()

    def populate_favorites(self, filter_text=""):
        self.bookmarks_list.clear()
        self.favorites = self.favorites_manager.get_favorites()
        for favorite in self.favorites:
            if filter_text.lower() in favorite.lower():
                item = QListWidgetItem(favorite)
                self.bookmarks_list.addItem(item)

    def filter_favorites(self, text):
        self.populate_favorites(text)

    def accept_selection(self, item):
        self.selected_favorite = item.text()
        self.accept()

    def delete_selected_favorites(self):
        selected_items = self.bookmarks_list.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            self.favorites_manager.remove_favorite(item.text())
        
        self.populate_favorites(self.filter_input.text())
