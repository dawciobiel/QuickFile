from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QPushButton, QCheckBox, QComboBox
from PyQt6.QtCore import Qt
from app.settings_manager import SettingsManager
from app.translation_manager import translation_manager # Import our new manager
from app.theme_manager import ThemeManager # Import ThemeManager

class SettingsDialog(QDialog):
    def __init__(self, parent, settings_manager: SettingsManager, theme_manager: ThemeManager):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("SettingsDialog", "Application Settings"))
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager # Store theme manager

        self.current_show_dot_files = self.settings_manager.get_setting("showDotFiles")
        self.current_file_permissions_display_mode = self.settings_manager.get_setting("file_permissions_display_mode")
        self.current_show_uid_column = self.settings_manager.get_setting("show_uid_column")
        self.current_show_gid_column = self.settings_manager.get_setting("show_gid_column")
        self.current_language_mode = self.settings_manager.get_setting("language_mode")
        self.current_manual_language = self.settings_manager.get_setting("manual_language")
        self.current_theme = self.settings_manager.get_setting("theme", "dark") # Get current theme

        self.selected_show_dot_files = self.current_show_dot_files
        self.selected_file_permissions_display_mode = self.current_file_permissions_display_mode
        self.selected_show_uid_column = self.current_show_uid_column
        self.selected_show_gid_column = self.current_show_gid_column
        self.selected_language_mode = self.current_language_mode
        self.selected_manual_language = self.current_manual_language
        self.selected_theme = self.current_theme # Initialize selected theme

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Group box for dot files
        dot_files_group = QGroupBox(translation_manager.translate("SettingsDialog", "Hidden Files (Dot Files)"))
        dot_files_layout = QVBoxLayout()
        self.show_dot_files_checkbox = QCheckBox(translation_manager.translate("SettingsDialog", "Show files and folders starting with '.'"))
        self.show_dot_files_checkbox.setChecked(self.current_show_dot_files)
        self.show_dot_files_checkbox.stateChanged.connect(self._set_selected_show_dot_files)
        dot_files_layout.addWidget(self.show_dot_files_checkbox)
        dot_files_group.setLayout(dot_files_layout)
        main_layout.addWidget(dot_files_group)

        # Group box for File Permissions Display
        permissions_group = QGroupBox(translation_manager.translate("SettingsDialog", "File Permissions Display"))
        permissions_layout = QVBoxLayout()
        self.symbolic_permissions_radio = QRadioButton(translation_manager.translate("SettingsDialog", "Symbolic (rwx)"))
        self.numeric_permissions_radio = QRadioButton(translation_manager.translate("SettingsDialog", "Numeric (755)"))

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
        columns_group = QGroupBox(translation_manager.translate("SettingsDialog", "Column Visibility"))
        columns_layout = QVBoxLayout()
        self.show_uid_checkbox = QCheckBox(translation_manager.translate("SettingsDialog", "Show UID Column"))
        self.show_uid_checkbox.setChecked(self.current_show_uid_column)
        self.show_uid_checkbox.stateChanged.connect(self._set_selected_show_uid_column)
        columns_layout.addWidget(self.show_uid_checkbox)

        self.show_gid_checkbox = QCheckBox(translation_manager.translate("SettingsDialog", "Show GID Column"))
        self.show_gid_checkbox.setChecked(self.current_show_gid_column)
        self.show_gid_checkbox.stateChanged.connect(self._set_selected_show_gid_column)
        columns_layout.addWidget(self.show_gid_checkbox)

        columns_group.setLayout(columns_layout)
        main_layout.addWidget(columns_group)
        
        # Group box for Language Settings
        language_group = QGroupBox(translation_manager.translate("SettingsDialog", "Language Settings"))
        language_layout = QVBoxLayout()

        self.auto_language_radio = QRadioButton(translation_manager.translate("SettingsDialog", "Auto-detect language"))
        self.manual_language_radio = QRadioButton(translation_manager.translate("SettingsDialog", "Manual language selection"))
        
        self.language_combo = QComboBox()
        self.language_combo.addItem("English (en_US)", "en_US")
        self.language_combo.addItem("Polski (pl_PL)", "pl_PL")
        # Add more languages here as needed
        
        # Select current manual language
        index = self.language_combo.findData(self.current_manual_language)
        if index != -1:
            self.language_combo.setCurrentIndex(index)
        
        self.auto_language_radio.toggled.connect(lambda checked: self._set_selected_language_mode("auto") if checked else None)
        self.manual_language_radio.toggled.connect(lambda checked: self._set_selected_language_mode("manual") if checked else None)
        self.language_combo.currentIndexChanged.connect(self._set_selected_manual_language)

        if self.current_language_mode == "auto":
            self.auto_language_radio.setChecked(True)
            self.language_combo.setEnabled(False)
        else:
            self.manual_language_radio.setChecked(True)
            self.language_combo.setEnabled(True)
            
        language_layout.addWidget(self.auto_language_radio)
        language_layout.addWidget(self.manual_language_radio)
        language_layout.addWidget(self.language_combo)
        language_group.setLayout(language_layout)
        main_layout.addWidget(language_group)

        # Group box for Theme Settings
        theme_group = QGroupBox(translation_manager.translate("SettingsDialog", "Theme Settings"))
        theme_layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        
        # Populate theme combo box
        available_themes = self.theme_manager.get_available_themes()
        for theme_name in available_themes:
            self.theme_combo.addItem(theme_name.capitalize(), theme_name) # Display capitalized name, store raw name
        
        # Select current theme
        index = self.theme_combo.findData(self.current_theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)
        
        self.theme_combo.currentIndexChanged.connect(self._set_selected_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        main_layout.addWidget(theme_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(translation_manager.translate("SettingsDialog", "Save"))
        self.cancel_button = QPushButton(translation_manager.translate("SettingsDialog", "Cancel"))
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
        
    def _set_selected_language_mode(self, mode):
        self.selected_language_mode = mode
        self.language_combo.setEnabled(mode == "manual")

    def _set_selected_manual_language(self, index):
        self.selected_manual_language = self.language_combo.itemData(index)

    def _set_selected_theme(self, index):
        self.selected_theme = self.theme_combo.itemData(index)

    def get_settings(self):
        return {
            "showDotFiles": self.selected_show_dot_files,
            "file_permissions_display_mode": self.selected_file_permissions_display_mode,
            "show_uid_column": self.selected_show_uid_column,
            "show_gid_column": self.selected_show_gid_column,
            "language_mode": self.selected_language_mode,
            "manual_language": self.selected_manual_language,
            "theme": self.selected_theme # Return selected theme
        }
