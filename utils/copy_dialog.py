from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox


class CopyDialog(QDialog):
    def __init__(self, parent, source_path, destination_path):
        super().__init__(parent)
        self.setWindowTitle("Copy")

        self.layout = QVBoxLayout(self)

        # Etykiety informacyjne
        self.layout.addWidget(QLabel(f"<b>Source:</b> {source_path}"))
        self.layout.addWidget(QLabel(f"<b>Destination:</b> {destination_path}"))

        # Opcje
        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        self.preserve_timestamp_checkbox = QCheckBox("Preserve original modification date")
        self.preserve_timestamp_checkbox.setChecked(True)  # Domyślnie zaznaczone

        self.layout.addWidget(self.overwrite_checkbox)
        self.layout.addWidget(self.preserve_timestamp_checkbox)

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_options(self):
        """Returns a dictionary with selected options."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "preserve_timestamp": self.preserve_timestamp_checkbox.isChecked(),
        }
