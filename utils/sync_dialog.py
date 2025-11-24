from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox

class SyncDialog(QDialog):
    def __init__(self, parent, source_dir, dest_dir):
        super().__init__(parent)
        self.setWindowTitle("Directory Synchronization")

        self.source_dir = source_dir
        self.dest_dir = dest_dir

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Scieżki
        path_layout = QVBoxLayout()
        path_layout.addWidget(QLabel(f"Source: {self.source_dir}"))
        path_layout.addWidget(QLabel(f"Destination: {self.dest_dir}"))
        layout.addLayout(path_layout)

        # Opcje
        options_group = QGroupBox("Synchronization Options")
        options_layout = QVBoxLayout()

        self.two_way_sync_checkbox = QCheckBox("Two-way synchronization (copy newer files both ways)")
        self.delete_files_checkbox = QCheckBox("Delete files in destination folder if they don't exist in source")
        self.include_subdirs_checkbox = QCheckBox("Include subdirectories")
        self.include_subdirs_checkbox.setChecked(True)

        options_layout.addWidget(self.two_way_sync_checkbox)
        options_layout.addWidget(self.delete_files_checkbox)
        options_layout.addWidget(self.include_subdirs_checkbox)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Przyciski
        button_layout = QHBoxLayout()
        self.sync_button = QPushButton("Synchronize")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.sync_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Połączenia
        self.sync_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_options(self):
        return {
            "two_way": self.two_way_sync_checkbox.isChecked(),
            "delete": self.delete_files_checkbox.isChecked(),
            "include_subdirs": self.include_subdirs_checkbox.isChecked(),
        }
