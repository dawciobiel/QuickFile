from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtWidgets import QDialog, QPushButton, QColorDialog, QDialogButtonBox

from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager


class SettingsDialog(QDialog):
    def __init__(self, parent, settings_manager: SettingsManager, theme_manager: ThemeManager):
        super().__init__(parent)
        uic.loadUi("ui/settings_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("SettingsDialog", "Application Settings"))
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager

        self.current_show_dot_files = self.settings_manager.get_setting("showDotFiles")
        self.current_file_permissions_display_mode = self.settings_manager.get_setting("file_permissions_display_mode")
        self.current_show_uid_column = self.settings_manager.get_setting("show_uid_column")
        self.current_show_gid_column = self.settings_manager.get_setting("show_gid_column")
        self.current_language_mode = self.settings_manager.get_setting("language_mode")
        self.current_manual_language = self.settings_manager.get_setting("manual_language")
        self.current_theme = self.settings_manager.get_setting("theme", "dark")
        self.current_viewer_command = self.settings_manager.get_setting("viewer_command")
        self.current_editor_command = self.settings_manager.get_setting("editor_command")

        self.current_insert_selection_text_color = self.settings_manager.get_setting("insert_selection_text_color")
        self.current_insert_selection_font_bold = self.settings_manager.get_setting("insert_selection_font_bold")
        self.current_insert_selection_font_italic = self.settings_manager.get_setting("insert_selection_font_italic")
        
        self.selected_insert_selection_text_color = self.current_insert_selection_text_color

        self._init_ui()

    def _init_ui(self):
        self.language_combo.addItem("English (en_US)", "en_US")
        self.language_combo.addItem("Polski (pl_PL)", "pl_PL")
        index = self.language_combo.findData(self.current_manual_language)
        if index != -1:
            self.language_combo.setCurrentIndex(index)
        if self.current_language_mode == "auto":
            self.auto_language_radio.setChecked(True)
        else:
            self.manual_language_radio.setChecked(True)
        
        available_themes = self.theme_manager.get_available_themes()
        for theme_name in available_themes:
            self.theme_combo.addItem(theme_name.capitalize(), theme_name)
        index = self.theme_combo.findData(self.current_theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)

        self.viewer_command_edit.setText(self.current_viewer_command)
        self.editor_command_edit.setText(self.current_editor_command)

        self.show_dot_files_checkbox.setChecked(self.current_show_dot_files)
        if self.current_file_permissions_display_mode == "symbolic":
            self.symbolic_permissions_radio.setChecked(True)
        else:
            self.numeric_permissions_radio.setChecked(True)
        self.show_uid_checkbox.setChecked(self.current_show_uid_column)
        self.show_gid_checkbox.setChecked(self.current_show_gid_column)

        self.insert_text_color_button.setFixedSize(QSize(30, 20))
        self._update_color_button_icon(self.insert_text_color_button, self.selected_insert_selection_text_color)
        self.insert_text_color_button.clicked.connect(self._pick_insert_text_color)
        self.insert_font_bold_checkbox.setChecked(self.current_insert_selection_font_bold)
        self.insert_font_italic_checkbox.setChecked(self.current_insert_selection_font_italic)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText(translation_manager.translate("SettingsDialog", "Save"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("SettingsDialog", "Cancel"))

    def _update_color_button_icon(self, button: QPushButton, color_hex: str):
        pixmap = QPixmap(button.size())
        pixmap.fill(QColor(color_hex))
        button.setIcon(QIcon(pixmap))

    def _pick_insert_text_color(self):
        color = QColorDialog.getColor(QColor(self.selected_insert_selection_text_color), self)
        if color.isValid():
            self.selected_insert_selection_text_color = color.name()
            self._update_color_button_icon(self.insert_text_color_button, self.selected_insert_selection_text_color)

    def get_settings(self):
        return {
            "showDotFiles": self.show_dot_files_checkbox.isChecked(),
            "file_permissions_display_mode": "symbolic" if self.symbolic_permissions_radio.isChecked() else "numeric",
            "show_uid_column": self.show_uid_checkbox.isChecked(),
            "show_gid_column": self.show_gid_checkbox.isChecked(),
            "language_mode": "auto" if self.auto_language_radio.isChecked() else "manual",
            "manual_language": self.language_combo.currentData(),
            "theme": self.theme_combo.currentData(),
            "viewer_command": self.viewer_command_edit.text(),
            "editor_command": self.editor_command_edit.text(),
            "insert_selection_text_color": self.selected_insert_selection_text_color,
            "insert_selection_font_bold": self.insert_font_bold_checkbox.isChecked(),
            "insert_selection_font_italic": self.insert_font_italic_checkbox.isChecked()
        }
