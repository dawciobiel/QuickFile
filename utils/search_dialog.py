from PyQt6 import uic
from PyQt6.QtWidgets import QDialog

from app.translation_manager import translation_manager


class SearchDialog(QDialog):
    def __init__(self, current_path, file_manager, parent=None):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/search_dialog.ui", self)

        self.current_path = current_path
        self.file_manager = file_manager
        self.selected_file = None

        self.setWindowTitle(translation_manager.translate("SearchDialog", "Search"))
        self.path_label.setText(self.current_path)

        # Connect signals
        self.search_button.clicked.connect(self._perform_search)
        self.search_input.returnPressed.connect(self._perform_search)
        self.results_list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Initialize UI state
        self.stackedWidget.setCurrentWidget(self.no_results_page)

    def _perform_search(self):
        query = self.search_input.text()
        if not query:
            return

        self.no_results_label.setText(translation_manager.translate("SearchDialog", "Searching..."))
        self.stackedWidget.setCurrentWidget(self.no_results_page)

        # Perform search (this might block UI for large dirs, ideally should be threaded)
        results, message = self.file_manager.search_files(self.current_path, query)

        self.results_list_widget.clear()
        if results:
            self.results_list_widget.addItems(results)
            self.stackedWidget.setCurrentWidget(self.results_page)
        else:
            self.no_results_label.setText(translation_manager.translate("SearchDialog", "No search results found."))
            self.stackedWidget.setCurrentWidget(self.no_results_page)

    def on_item_double_clicked(self, item):
        """
        When an item is double-clicked, store it and accept the dialog.
        """
        self.selected_file = item.text()
        self.accept()
