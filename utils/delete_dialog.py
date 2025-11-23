from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox


class DeleteDialog(QDialog):
    def __init__(self, parent, item_path):
        super().__init__(parent)
        self.setWindowTitle("Usuwanie")

        self.layout = QVBoxLayout(self)

        # Etykieta informacyjna
        self.layout.addWidget(QLabel(f"Czy na pewno chcesz usunąć: <b>{item_path}</b>?"))
        self.layout.addWidget(QLabel("Tej operacji nie można cofnąć."))

        # Przyciski OK/Anuluj
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
