from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox

class SyncDialog(QDialog):
    def __init__(self, parent, source_dir, dest_dir):
        super().__init__(parent)
        self.setWindowTitle("Synchronizacja Katalogów")

        self.source_dir = source_dir
        self.dest_dir = dest_dir

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Scieżki
        path_layout = QVBoxLayout()
        path_layout.addWidget(QLabel(f"Źródło: {self.source_dir}"))
        path_layout.addWidget(QLabel(f"Cel: {self.dest_dir}"))
        layout.addLayout(path_layout)

        # Opcje
        options_group = QGroupBox("Opcje Synchronizacji")
        options_layout = QVBoxLayout()

        self.two_way_sync_checkbox = QCheckBox("Synchronizacja dwukierunkowa (kopiuj nowsze pliki w obie strony)")
        self.delete_files_checkbox = QCheckBox("Usuń pliki w folderze docelowym, jeśli nie istnieją w źródłowym")
        self.include_subdirs_checkbox = QCheckBox("Uwzględnij podkatalogi")
        self.include_subdirs_checkbox.setChecked(True)

        options_layout.addWidget(self.two_way_sync_checkbox)
        options_layout.addWidget(self.delete_files_checkbox)
        options_layout.addWidget(self.include_subdirs_checkbox)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Przyciski
        button_layout = QHBoxLayout()
        self.sync_button = QPushButton("Synchronizuj")
        self.cancel_button = QPushButton("Anuluj")
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
