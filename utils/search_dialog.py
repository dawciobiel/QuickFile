from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager # Import our new manager


class SearchDialog(QDialog):
    def __init__(self, parent=None, results=None):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("SearchDialog", "Search Results"))
        self.resize(600, 400)

        self.results = results if results is not None else []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if not self.results:
            no_results_label = QLabel(translation_manager.translate("SearchDialog", "No search results found."))
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_results_label)
        else:
            self.results_list_widget = QListWidget()
            self.results_list_widget.addItems(self.results)
            layout.addWidget(self.results_list_widget)

        close_button = QPushButton(translation_manager.translate("SearchDialog", "Close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
