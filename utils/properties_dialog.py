from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QPushButton, QDialogButtonBox


class PropertiesDialog(QDialog):
    def __init__(self, properties, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Properties")

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        if properties:
            for key, value in properties.items():
                form_layout.addRow(QLabel(f"{key}:"), QLabel(str(value)))

        layout.addLayout(form_layout)

        # OK Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.resize(400, 300) # Start with a reasonable size
