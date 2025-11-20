from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox


class CopyDialog(QDialog):
    def __init__(self, parent, source_path, destination_path):
        super().__init__(parent)
        self.setWindowTitle("Kopiowanie")

        self.layout = QVBoxLayout(self)

        # Etykiety informacyjne
        self.layout.addWidget(QLabel(f"<b>Źródło:</b> {source_path}"))
        self.layout.addWidget(QLabel(f"<b>Cel:</b> {destination_path}"))

        # Opcje
        self.overwrite_checkbox = QCheckBox("Nadpisz istniejące pliki")
        self.preserve_timestamp_checkbox = QCheckBox("Zachowaj oryginalną datę modyfikacji")
        self.preserve_timestamp_checkbox.setChecked(True)  # Domyślnie zaznaczone

        self.layout.addWidget(self.overwrite_checkbox)
        self.layout.addWidget(self.preserve_timestamp_checkbox)

        # Przyciski OK/Anuluj
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_options(self):
        """Zwraca słownik z wybranymi opcjami."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "preserve_timestamp": self.preserve_timestamp_checkbox.isChecked(),
        }
