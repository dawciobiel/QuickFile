from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QPushButton, QCheckBox
from PyQt6.QtCore import Qt, QCoreApplication
from app.settings_manager import SettingsManager

class SettingsDialog(QDialog):
    def __init__(self, parent, settings_manager: SettingsManager):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("SettingsDialog", "Application Settings"))
        self.settings_manager = settings_manager

        self.current_show_dot_files = self.settings_manager.get_setting("showDotFiles")
        self.current_file_permissions_display_mode = self.settings_manager.get_setting("file_permissions_display_mode")
        self.current_show_uid_column = self.settings_manager.get_setting("show_uid_column")
        self.current_show_gid_column = self.settings_manager.get_setting("show_gid_column")

        self.selected_show_dot_files = self.current_show_dot_files
        self.selected_file_permissions_display_mode = self.current_file_permissions_display_mode
        self.selected_show_uid_column = self.current_show_uid_column
        self.selected_show_gid_column = self.current_show_gid_column

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Group box for dot files
        dot_files_group = QGroupBox(QCoreApplication.translate("SettingsDialog", "Hidden Files (Dot Files)"))
        dot_files_layout = QVBoxLayout()
        self.show_dot_files_checkbox = QCheckBox(QCoreApplication.translate("SettingsDialog", "Show files and folders starting with '.'"))
        self.show_dot_files_checkbox.setChecked(self.current_show_dot_files)
        self.show_dot_files_checkbox.stateChanged.connect(self._set_selected_show_dot_files)
        dot_files_layout.addWidget(self.show_dot_files_checkbox)
        dot_files_group.setLayout(dot_files_layout)
        main_layout.addWidget(dot_files_group)

        # Group box for File Permissions Display
        permissions_group = QGroupBox(QCoreApplication.translate("SettingsDialog", "File Permissions Display"))
        permissions_layout = QVBoxLayout()
        self.symbolic_permissions_radio = QRadioButton(QCoreApplication.translate("SettingsDialog", "Symbolic (rwx)"))
        self.numeric_permissions_radio = QRadioButton(QCoreApplication.translate("SettingsDialog", "Numeric (755)"))

        if self.current_file_permissions_display_mode == "symbolic":
            self.symbolic_permissions_radio.setChecked(True)
        else:
            self.numeric_permissions_radio.setChecked(True)

        self.symbolic_permissions_radio.toggled.connect(lambda: self._set_selected_file_permissions_display_mode("symbolic"))
        self.numeric_permissions_radio.toggled.connect(lambda: self._set_selected_file_permissions_display_mode("numeric"))

        permissions_layout.addWidget(self.symbolic_permissions_radio)
        permissions_layout.addWidget(self.numeric_permissions_radio)
        permissions_group.setLayout(permissions_layout)
        main_layout.addWidget(permissions_group)

        # Group box for Column Visibility
        columns_group = QGroupBox(QCoreApplication.translate("SettingsDialog", "Column Visibility"))
        columns_layout = QVBoxLayout()
        self.show_uid_checkbox = QCheckBox(QCoreApplication.translate("SettingsDialog", "Show UID Column"))
        self.show_uid_checkbox.setChecked(self.current_show_uid_column)
        self.show_uid_checkbox.stateChanged.connect(self._set_selected_show_uid_column)
        columns_layout.addWidget(self.show_uid_checkbox)

        self.show_gid_checkbox = QCheckBox(QCoreApplication.translate("SettingsDialog", "Show GID Column"))
        self.show_gid_checkbox.setChecked(self.current_show_gid_column)
        self.show_gid_checkbox.stateChanged.connect(self._set_selected_show_gid_column)
        columns_layout.addWidget(self.show_gid_checkbox)

        columns_group.setLayout(columns_layout)
        main_layout.addWidget(columns_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(QCoreApplication.translate("SettingsDialog", "Save"))
        self.cancel_button = QPushButton(QCoreApplication.translate("SettingsDialog", "Cancel"))
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _set_selected_show_dot_files(self, state):
        self.selected_show_dot_files = (state == Qt.CheckState.Checked.value)

    def _set_selected_file_permissions_display_mode(self, mode):
        self.selected_file_permissions_display_mode = mode

    def _set_selected_show_uid_column(self, state):
        self.selected_show_uid_column = (state == Qt.CheckState.Checked.value)

    def _set_selected_show_gid_column(self, state):
        self.selected_show_gid_column = (state == Qt.CheckState.Checked.value)

    def get_settings(self):
        return {
            "showDotFiles": self.selected_show_dot_files,
            "file_permissions_display_mode": self.selected_file_permissions_display_mode,
            "show_uid_column": self.selected_show_uid_column,
            "show_gid_column": self.selected_show_gid_column
        }
