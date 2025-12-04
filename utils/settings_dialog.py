from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QPushButton, QCheckBox
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent, current_view_mode, current_show_dot_files):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Application Settings"))
        self.current_view_mode = current_view_mode
        self.selected_view_mode = current_view_mode
        self.current_show_dot_files = current_show_dot_files
        self.selected_show_dot_files = current_show_dot_files
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Group box for view mode
        view_mode_group = QGroupBox(self.tr("Folder View Mode"))
        view_mode_layout = QVBoxLayout()

        self.flat_view_radio = QRadioButton(self.tr("Flat View (current directory only, with '..')"))
        self.tree_view_radio = QRadioButton(self.tr("Tree View (entire partition, expandable directories)"))

        if self.current_view_mode == "flat":
            self.flat_view_radio.setChecked(True)
        else:
            self.tree_view_radio.setChecked(True)

        self.flat_view_radio.toggled.connect(lambda: self._set_selected_view_mode("flat"))
        self.tree_view_radio.toggled.connect(lambda: self._set_selected_view_mode("tree"))

        view_mode_layout.addWidget(self.flat_view_radio)
        view_mode_layout.addWidget(self.tree_view_radio)
        view_mode_group.setLayout(view_mode_layout)
        main_layout.addWidget(view_mode_group)

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

    def _set_selected_view_mode(self, mode):
        self.selected_view_mode = mode

    def _set_selected_show_dot_files(self, state):
        self.selected_show_dot_files = (state == Qt.CheckState.Checked.value)

    def get_selected_view_mode(self):
        return self.selected_view_mode

    def get_selected_show_dot_files(self):
        return self.selected_show_dot_files
