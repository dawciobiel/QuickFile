from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
from app.translation_manager import translation_manager

class SearchInputDialog(QDialog):
    def __init__(self, parent, search_path):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("SearchInputDialog", "Search Files"))
        self.resize(400, 150)
        
        self.layout = QVBoxLayout(self)
        
        self.path_label = QLabel(translation_manager.translate("SearchInputDialog", f"Searching in: {search_path}"))
        self.layout.addWidget(self.path_label)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText(translation_manager.translate("SearchInputDialog", "Enter file name or pattern..."))
        self.layout.addWidget(self.query_input)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "Search"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_query(self):
        return self.query_input.text()
