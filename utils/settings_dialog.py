from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QPushButton, QCheckBox
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent, current_show_dot_files):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Application Settings"))
        self.current_show_dot_files = current_show_dot_files
        self.selected_show_dot_files = current_show_dot_files
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Group box for dot files
        dot_files_group = QGroupBox(self.tr("Hidden Files (Dot Files)"))
        dot_files_layout = QVBoxLayout()
        self.show_dot_files_checkbox = QCheckBox(self.tr("Show files and folders starting with '.'"))
        self.show_dot_files_checkbox.setChecked(self.current_show_dot_files)
        self.show_dot_files_checkbox.stateChanged.connect(self._set_selected_show_dot_files)
        dot_files_layout.addWidget(self.show_dot_files_checkbox)
        dot_files_group.setLayout(dot_files_layout)
        main_layout.addWidget(dot_files_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(self.tr("Save"))
        self.cancel_button = QPushButton(self.tr("Cancel"))
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _set_selected_show_dot_files(self, state):
        self.selected_show_dot_files = (state == Qt.CheckState.Checked.value)

    def get_selected_show_dot_files(self):
        return self.selected_show_dot_files
