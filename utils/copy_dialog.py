from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox
from app.translation_manager import translation_manager

class CopyDialog(QDialog):
    def __init__(self, parent, source_path, destination_path):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("CopyDialog", "Copy"))

        self.layout = QVBoxLayout(self)

        # Etykiety informacyjne
        self.layout.addWidget(QLabel(f"<b>{translation_manager.translate('CopyDialog', 'Source')}:</b> {source_path}"))
        self.layout.addWidget(QLabel(f"<b>{translation_manager.translate('CopyDialog', 'Destination')}:</b> {destination_path}"))

        # Opcje
        self.overwrite_checkbox = QCheckBox(translation_manager.translate("CopyDialog", "Overwrite existing files"))
        self.preserve_timestamp_checkbox = QCheckBox(translation_manager.translate("CopyDialog", "Preserve original modification date"))
        self.preserve_timestamp_checkbox.setChecked(True)  # Domyślnie zaznaczone

        self.layout.addWidget(self.overwrite_checkbox)
        self.layout.addWidget(self.preserve_timestamp_checkbox)

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_options(self):
        """Returns a dictionary with selected options."""
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "preserve_timestamp": self.preserve_timestamp_checkbox.isChecked(),
        }
