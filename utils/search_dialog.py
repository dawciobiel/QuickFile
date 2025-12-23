from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager


class SearchDialog(QDialog):
    def __init__(self, parent=None, results=None):
        super().__init__(parent)
        uic.loadUi("ui/search_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("SearchDialog", "Search Results"))
        
        self.results = results if results is not None else []

        self._init_ui()

    def _init_ui(self):
        # Hide search input elements since we are only displaying results provided by MainWindow
        self.search_in_label.setVisible(False)
        self.path_label.setVisible(False)
        self.search_input.setVisible(False)
        self.search_button.setVisible(False)
        
        # Also hide the layouts containing them if possible, or just the widgets
        # Accessing layouts by name from .ui isn't direct attribute access usually, 
        # but hiding widgets is enough.

        if not self.results:
            self.stackedWidget.setCurrentWidget(self.no_results_page)
            self.no_results_label.setText(translation_manager.translate("SearchDialog", "No search results found."))
        else:
            self.stackedWidget.setCurrentWidget(self.results_page)
            self.results_list_widget.addItems(self.results)

        # Configure button box
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setText(translation_manager.translate("SearchDialog", "Close"))
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.accept)
