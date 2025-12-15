from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QDialogButtonBox, QTextEdit
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager # Import our new manager


class PropertiesDialog(QDialog):
    def __init__(self, properties, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("PropertiesDialog", "Properties"))

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        if properties:
            for key, value in properties.items():
                if key == 'Full path':
                    path_text_edit = QTextEdit()
                    path_text_edit.setReadOnly(True)
                    path_text_edit.setText(str(value))
                    path_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                    path_text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                    path_text_edit.setFixedHeight(60) # Fixed height for the path display
                    form_layout.addRow(QLabel(f"{key}:"), path_text_edit)
                else:
                    label_value = QLabel(str(value))
                    label_value.setWordWrap(True) # Enable word wrap for other long properties
                    form_layout.addRow(QLabel(f"{key}:"), label_value)

        layout.addLayout(form_layout)

        # OK Button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setMaximumWidth(600) # Set maximum width for the dialog
        self.resize(500, 300) # Start with a reasonable size, but respect max width
