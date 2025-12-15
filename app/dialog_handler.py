import logging
from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog

from utils.properties_dialog import PropertiesDialog
from utils.shortcuts_dialog import ShortcutsDialog
from utils.settings_dialog import SettingsDialog
from utils.search_dialog import SearchDialog
from utils.bookmark_dialog import BookmarkDialog
from utils.compare_dialog import CompareDialog
from utils.copy_dialog import CopyDialog
from utils.move_dialog import MoveDialog
from utils.delete_dialog import DeleteDialog
from utils.sync_dialog import SyncDialog
from app.translation_manager import translation_manager


class DialogHandler:
    def __init__(self, main_window, application_logic_handler):
        self.main_window = main_window
        self.logic_handler = application_logic_handler

    # Tutaj przeniesiemy metody związane z oknami dialogowymi
    # z ApplicationLogicHandler

    def show_properties_dialog(self, checked=False):
        # Ta metoda zostanie przeniesiona i dostosowana
        pass

    def open_general_settings_dialog(self, checked=False):
        # Ta metoda zostanie przeniesiona i dostosowana
        pass

    def open_shortcuts_dialog(self, checked=False):
        # Ta metoda zostanie przeniesiona i dostosowana
        pass

    # ... i tak dalej dla pozostałych metod dialogowych
