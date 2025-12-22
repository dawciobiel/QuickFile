from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtWidgets import QDialog, QColorDialog

from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager


class SettingsDialog(QDialog):
    def __init__(self, parent, settings_manager: SettingsManager, theme_manager: ThemeManager):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/settings_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("SettingsDialog", "Application Settings"))
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager

        # Load current settings
        self.current_show_dot_files = self.settings_manager.get_setting("showDotFiles")
        self.current_file_permissions_display_mode = self.settings_manager.get_setting("file_permissions_display_mode")
        self.current_show_uid_column = self.settings_manager.get_setting("show_uid_column")
        self.current_show_gid_column = self.settings_manager.get_setting("show_gid_column")
        self.current_language_mode = self.settings_manager.get_setting("language_mode")
        self.current_manual_language = self.settings_manager.get_setting("manual_language")
        self.current_theme = self.settings_manager.get_setting("theme", "dark")

        # New settings for Insert selection style
        self.current_insert_selection_text_color = self.settings_manager.get_setting("insert_selection_text_color")
        self.current_insert_selection_font_bold = self.settings_manager.get_setting("insert_selection_font_bold")
        self.current_insert_selection_font_italic = self.settings_manager.get_setting("insert_selection_font_italic")

        # Initialize selected settings with current values
        self.selected_show_dot_files = self.current_show_dot_files
        self.selected_file_permissions_display_mode = self.current_file_permissions_display_mode
        self.selected_show_uid_column = self.current_show_uid_column
        self.selected_show_gid_column = self.current_show_gid_column
        self.selected_language_mode = self.current_language_mode
        self.selected_manual_language = self.current_manual_language
        self.selected_theme = self.current_theme

        self.selected_insert_selection_text_color = self.current_insert_selection_text_color
        self.selected_insert_selection_font_bold = self.current_insert_selection_font_bold
        self.selected_insert_selection_font_italic = self.current_insert_selection_font_italic

        self._init_ui_state()
        self._connect_signals()
        self._translate_ui()

    def _init_ui_state(self):
        # General Tab
        # Language
        self.language_combo.addItem("English (en_US)", "en_US")
        self.language_combo.addItem("Polski (pl_PL)", "pl_PL")
        
        index = self.language_combo.findData(self.current_manual_language)
        if index != -1:
            self.language_combo.setCurrentIndex(index)

        if self.current_language_mode == "auto":
            self.auto_language_radio.setChecked(True)
            self.language_combo.setEnabled(False)
        else:
            self.manual_language_radio.setChecked(True)
            self.language_combo.setEnabled(True)

        # Theme
        available_themes = self.theme_manager.get_available_themes()
        for theme_name in available_themes:
            self.theme_combo.addItem(theme_name.capitalize(), theme_name)
        
        index = self.theme_combo.findData(self.current_theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)

        # View Tab
        self.show_dot_files_checkbox.setChecked(self.current_show_dot_files)

        if self.current_file_permissions_display_mode == "symbolic":
            self.symbolic_permissions_radio.setChecked(True)
        else:
            self.numeric_permissions_radio.setChecked(True)

        self.show_uid_checkbox.setChecked(self.current_show_uid_column)
        self.show_gid_checkbox.setChecked(self.current_show_gid_column)

        # Appearance Tab
        self.insert_text_color_button.setFixedSize(QSize(30, 20))
        self._update_color_button_icon(self.insert_text_color_button, self.selected_insert_selection_text_color)
        self.insert_font_bold_checkbox.setChecked(self.current_insert_selection_font_bold)
        self.insert_font_italic_checkbox.setChecked(self.current_insert_selection_font_italic)

    def _connect_signals(self):
        # General
        self.auto_language_radio.toggled.connect(lambda checked: self._set_selected_language_mode("auto") if checked else None)
        self.manual_language_radio.toggled.connect(lambda checked: self._set_selected_language_mode("manual") if checked else None)
        self.language_combo.currentIndexChanged.connect(self._set_selected_manual_language)
        self.theme_combo.currentIndexChanged.connect(self._set_selected_theme)

        # View
        self.show_dot_files_checkbox.stateChanged.connect(self._set_selected_show_dot_files)
        self.symbolic_permissions_radio.toggled.connect(lambda: self._set_selected_file_permissions_display_mode("symbolic"))
        self.numeric_permissions_radio.toggled.connect(lambda: self._set_selected_file_permissions_display_mode("numeric"))
        self.show_uid_checkbox.stateChanged.connect(self._set_selected_show_uid_column)
        self.show_gid_checkbox.stateChanged.connect(self._set_selected_show_gid_column)

        # Appearance
        self.insert_text_color_button.clicked.connect(self._pick_insert_text_color)
        self.insert_font_bold_checkbox.stateChanged.connect(self._set_selected_insert_font_bold)
        self.insert_font_italic_checkbox.stateChanged.connect(self._set_selected_insert_font_italic)

    def _translate_ui(self):
        # Translate tab titles
        self.tabWidget.setTabText(0, translation_manager.translate("SettingsDialog", "General"))
        self.tabWidget.setTabText(1, translation_manager.translate("SettingsDialog", "View"))
        self.tabWidget.setTabText(2, translation_manager.translate("SettingsDialog", "Appearance"))

        # Translate group boxes
        self.language_group.setTitle(translation_manager.translate("SettingsDialog", "Language"))
        self.theme_group.setTitle(translation_manager.translate("SettingsDialog", "Theme"))
        self.dot_files_group.setTitle(translation_manager.translate("SettingsDialog", "Hidden Files (Dot Files)"))
        self.permissions_group.setTitle(translation_manager.translate("SettingsDialog", "File Permissions Display"))
        self.columns_group.setTitle(translation_manager.translate("SettingsDialog", "Column Visibility"))
        self.insert_selection_group.setTitle(translation_manager.translate("SettingsDialog", "Insert Selection Style"))

        # Translate controls
        self.auto_language_radio.setText(translation_manager.translate("SettingsDialog", "Auto-detect language"))
        self.manual_language_radio.setText(translation_manager.translate("SettingsDialog", "Manual language selection"))
        self.show_dot_files_checkbox.setText(translation_manager.translate("SettingsDialog", "Show files and folders starting with '.'"))
        self.symbolic_permissions_radio.setText(translation_manager.translate("SettingsDialog", "Symbolic (rwx)"))
        self.numeric_permissions_radio.setText(translation_manager.translate("SettingsDialog", "Numeric (755)"))
        self.show_uid_checkbox.setText(translation_manager.translate("SettingsDialog", "Show UID Column"))
        self.show_gid_checkbox.setText(translation_manager.translate("SettingsDialog", "Show GID Column"))
        self.insert_font_bold_checkbox.setText(translation_manager.translate("SettingsDialog", "Bold"))
        self.insert_font_italic_checkbox.setText(translation_manager.translate("SettingsDialog", "Italic"))

        # Translate buttons (standard buttons are usually translated by Qt, but we can force it if needed)
        # self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText(translation_manager.translate("SettingsDialog", "Save"))
        # self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("SettingsDialog", "Cancel"))

    def _update_color_button_icon(self, button, color_hex: str):
        pixmap = QPixmap(button.size())
        pixmap.fill(QColor(color_hex))
        button.setIcon(QIcon(pixmap))

    def _pick_insert_text_color(self):
        color = QColorDialog.getColor(QColor(self.selected_insert_selection_text_color), self)
        if color.isValid():
            self.selected_insert_selection_text_color = color.name()
            self._update_color_button_icon(self.insert_text_color_button, self.selected_insert_selection_text_color)

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

    def _set_selected_insert_font_bold(self, state):
        self.selected_insert_selection_font_bold = (state == Qt.CheckState.Checked.value)

    def _set_selected_insert_font_italic(self, state):
        self.selected_insert_selection_font_italic = (state == Qt.CheckState.Checked.value)

    def get_settings(self):
        return {
            "showDotFiles": self.selected_show_dot_files,
            "file_permissions_display_mode": self.selected_file_permissions_display_mode,
            "show_uid_column": self.selected_show_uid_column,
            "show_gid_column": self.selected_show_gid_column,
            "language_mode": self.selected_language_mode,
            "manual_language": self.selected_manual_language,
            "theme": self.selected_theme,
            "insert_selection_text_color": self.selected_insert_selection_text_color,
            "insert_selection_font_bold": self.selected_insert_selection_font_bold,
            "insert_selection_font_italic": self.selected_insert_selection_font_italic
        }
