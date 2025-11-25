from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox


class DeleteDialog(QDialog):
    def __init__(self, parent, item_path):
        super().__init__(parent)
        self.setWindowTitle("Delete")

        self.layout = QVBoxLayout(self)

        # Etykieta informacyjna
        self.layout.addWidget(QLabel(f"Are you sure you want to delete: <b>{item_path}</b>?"))
        self.layout.addWidget(QLabel("This operation cannot be undone."))

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
