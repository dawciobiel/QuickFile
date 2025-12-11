from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox
from PyQt6.QtCore import QCoreApplication

class SyncDialog(QDialog):
    def __init__(self, parent, source_dir, dest_dir):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("SyncDialog", "Directory Synchronization"))

        self.source_dir = source_dir
        self.dest_dir = dest_dir

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Scieżki
        path_layout = QVBoxLayout()
        source_label_text = QCoreApplication.translate("SyncDialog", "Source")
        dest_label_text = QCoreApplication.translate("SyncDialog", "Destination")
        path_layout.addWidget(QLabel(f"{source_label_text}: {self.source_dir}"))
        path_layout.addWidget(QLabel(f"{dest_label_text}: {self.dest_dir}"))
        layout.addLayout(path_layout)

        # Opcje
        options_group = QGroupBox(QCoreApplication.translate("SyncDialog", "Synchronization Options"))
        options_layout = QVBoxLayout()

        self.two_way_sync_checkbox = QCheckBox(QCoreApplication.translate("SyncDialog", "Two-way synchronization (copy newer files both ways)"))
        self.delete_files_checkbox = QCheckBox(QCoreApplication.translate("SyncDialog", "Delete files in destination folder if they don't exist in source"))
        self.include_subdirs_checkbox = QCheckBox(QCoreApplication.translate("SyncDialog", "Include subdirectories"))
        self.include_subdirs_checkbox.setChecked(True)

        options_layout.addWidget(self.two_way_sync_checkbox)
        options_layout.addWidget(self.delete_files_checkbox)
        options_layout.addWidget(self.include_subdirs_checkbox)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Przyciski
        button_layout = QHBoxLayout()
        self.sync_button = QPushButton(QCoreApplication.translate("SyncDialog", "Synchronize"))
        self.cancel_button = QPushButton(QCoreApplication.translate("SyncDialog", "Cancel"))
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
