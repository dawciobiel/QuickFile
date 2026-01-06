from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QDialog, QPushButton, QColorDialog, QDialogButtonBox

from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager
from utils.resource_path import get_resource_path


class SettingsDialog(QDialog):
    def __init__(self, parent, settings_manager: SettingsManager, theme_manager: ThemeManager):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/settings_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("SettingsDialog", "Application Settings"))
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager

        self.pages = {}
        self.items = {}

        self._setup_tree_model()
        self._load_current_settings()
        self._init_ui()
        self._connect_signals()

    def _setup_tree_model(self):
        self.tree_model = QStandardItemModel()
        self.category_tree.setModel(self.tree_model)
        self.category_tree.setHeaderHidden(True)

        general_item = QStandardItem(translation_manager.translate("SettingsDialog", "General"))
        self.items[general_item.text()] = general_item
        self.pages[general_item.text()] = self.general_page
        self.tree_model.appendRow(general_item)

        view_item = QStandardItem(translation_manager.translate("SettingsDialog", "View"))
        self.items[view_item.text()] = view_item
        self.pages[view_item.text()] = self.view_page
        self.tree_model.appendRow(view_item)

        appearance_item = QStandardItem(translation_manager.translate("SettingsDialog", "Appearance"))
        self.items[appearance_item.text()] = appearance_item
        self.pages[appearance_item.text()] = self.appearance_page
        self.tree_model.appendRow(appearance_item)

    def _load_current_settings(self):
        self.current_show_dot_files = self.settings_manager.get_setting("showDotFiles")
        self.current_file_permissions_display_mode = self.settings_manager.get_setting("file_permissions_display_mode")
        self.current_show_uid_column = self.settings_manager.get_setting("show_uid_column")
        self.current_show_gid_column = self.settings_manager.get_setting("show_gid_column")
        self.current_language_mode = self.settings_manager.get_setting("language_mode")
        self.current_manual_language = self.settings_manager.get_setting("manual_language")
        self.current_theme = self.settings_manager.get_setting("theme", "dark")
        self.current_use_internal_viewer = self.settings_manager.get_setting("use_internal_viewer", True)
        self.current_use_internal_editor = self.settings_manager.get_setting("use_internal_editor", True)
        self.current_viewer_command = self.settings_manager.get_setting("viewer_command")
        self.current_editor_command = self.settings_manager.get_setting("editor_command")
        self.current_bring_to_front = self.settings_manager.get_setting("bringToFrontOnStartup")
        self.current_insert_selection_text_color = self.settings_manager.get_setting("insert_selection_text_color")
        self.current_insert_selection_font_bold = self.settings_manager.get_setting("insert_selection_font_bold")
        self.current_insert_selection_font_italic = self.settings_manager.get_setting("insert_selection_font_italic")
        self.current_dynamic_refresh_interval = self.settings_manager.get_setting("dynamic_refresh_interval", 2000)
        self.selected_insert_selection_text_color = self.current_insert_selection_text_color

    def _init_ui(self):
        self.language_group.setTitle(translation_manager.translate("SettingsDialog", "Language Settings"))
        self.auto_language_radio.setText(translation_manager.translate("SettingsDialog", "Auto-detect language"))
        self.manual_language_radio.setText(translation_manager.translate("SettingsDialog", "Manual language selection"))
        self.language_combo.addItem("English (en_US)", "en_US")
        self.language_combo.addItem("Polski (pl_PL)", "pl_PL")
        index = self.language_combo.findData(self.current_manual_language)
        if index != -1:
            self.language_combo.setCurrentIndex(index)
        if self.current_language_mode == "auto":
            self.auto_language_radio.setChecked(True)
        else:
            self.manual_language_radio.setChecked(True)
        
        self.theme_group.setTitle(translation_manager.translate("SettingsDialog", "Theme"))
        available_themes = self.theme_manager.get_themes()
        for theme_name in available_themes:
            self.theme_combo.addItem(theme_name.capitalize(), theme_name)
        index = self.theme_combo.findData(self.current_theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)

        self.external_editors_group.setTitle(translation_manager.translate("SettingsDialog", "External Editors"))
        self.use_internal_viewer_checkbox.setText(translation_manager.translate("SettingsDialog", "Use built-in viewer (F3)"))
        self.use_internal_editor_checkbox.setText(translation_manager.translate("SettingsDialog", "Use built-in editor (F4)"))
        self.viewer_label.setText(translation_manager.translate("SettingsDialog", "External Viewer (F3):"))
        self.editor_label.setText(translation_manager.translate("SettingsDialog", "Editor (F4):"))
        self.use_internal_viewer_checkbox.setChecked(self.current_use_internal_viewer)
        self.use_internal_editor_checkbox.setChecked(self.current_use_internal_editor)
        self.viewer_command_edit.setText(self.current_viewer_command)
        self.editor_command_edit.setText(self.current_editor_command)
        self.viewer_command_edit.setEnabled(not self.current_use_internal_viewer)
        self.editor_command_edit.setEnabled(not self.current_use_internal_editor)

        self.startup_group.setTitle(translation_manager.translate("SettingsDialog", "Startup"))
        self.bring_to_front_checkbox.setText(translation_manager.translate("SettingsDialog", "Bring window to front on startup"))
        self.bring_to_front_checkbox.setChecked(self.current_bring_to_front)

        self.dot_files_group.setTitle(translation_manager.translate("SettingsDialog", "Hidden Files (Dot Files)"))
        self.show_dot_files_checkbox.setText(translation_manager.translate("SettingsDialog", "Show files and folders starting with '.'"))
        self.show_dot_files_checkbox.setChecked(self.current_show_dot_files)
        
        self.permissions_group.setTitle(translation_manager.translate("SettingsDialog", "File Permissions Display"))
        self.symbolic_permissions_radio.setText(translation_manager.translate("SettingsDialog", "Symbolic (rwx)"))
        self.numeric_permissions_radio.setText(translation_manager.translate("SettingsDialog", "Numeric (755)"))
        if self.current_file_permissions_display_mode == "symbolic":
            self.symbolic_permissions_radio.setChecked(True)
        else:
            self.numeric_permissions_radio.setChecked(True)

        self.columns_group.setTitle(translation_manager.translate("SettingsDialog", "Column Visibility"))
        self.show_uid_checkbox.setText(translation_manager.translate("SettingsDialog", "Show UID Column"))
        self.show_gid_checkbox.setText(translation_manager.translate("SettingsDialog", "Show GID Column"))
        self.show_uid_checkbox.setChecked(self.current_show_uid_column)
        self.show_gid_checkbox.setChecked(self.current_show_gid_column)

        self.dynamic_refresh_group.setTitle(translation_manager.translate("SettingsDialog", "Dynamic Refresh"))
        self.refresh_interval_label.setText(translation_manager.translate("SettingsDialog", "Refresh interval (ms):"))
        self.refresh_interval_spinbox.setValue(self.current_dynamic_refresh_interval)

        self.insert_selection_group.setTitle(translation_manager.translate("SettingsDialog", "Insert Selection Style"))
        self.label.setText(translation_manager.translate("SettingsDialog", "Text Color:"))
        self.insert_font_bold_checkbox.setText(translation_manager.translate("SettingsDialog", "Bold"))
        self.insert_font_italic_checkbox.setText(translation_manager.translate("SettingsDialog", "Italic"))
        self.insert_text_color_button.setFixedSize(QSize(30, 20))
        self._update_color_button_icon(self.insert_text_color_button, self.selected_insert_selection_text_color)
        self.insert_font_bold_checkbox.setChecked(self.current_insert_selection_font_bold)
        self.insert_font_italic_checkbox.setChecked(self.current_insert_selection_font_italic)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText(translation_manager.translate("SettingsDialog", "Save"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("SettingsDialog", "Cancel"))

        self.category_tree.setCurrentIndex(self.tree_model.index(0, 0))

    def _connect_signals(self):
        self.category_tree.selectionModel().currentRowChanged.connect(self.change_page)
        self.use_internal_viewer_checkbox.stateChanged.connect(
            lambda state: self.viewer_command_edit.setEnabled(state == Qt.CheckState.Unchecked.value))
        self.use_internal_editor_checkbox.stateChanged.connect(
            lambda state: self.editor_command_edit.setEnabled(state == Qt.CheckState.Unchecked.value))
        self.insert_text_color_button.clicked.connect(self._pick_insert_text_color)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def change_page(self, current, previous):
        item = self.tree_model.itemFromIndex(current)
        if item.text() in self.pages:
            self.stackedWidget.setCurrentWidget(self.pages[item.text()])

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
            "use_internal_viewer": self.use_internal_viewer_checkbox.isChecked(),
            "use_internal_editor": self.use_internal_editor_checkbox.isChecked(),
            "viewer_command": self.viewer_command_edit.text(),
            "editor_command": self.editor_command_edit.text(),
            "bringToFrontOnStartup": self.bring_to_front_checkbox.isChecked(),
            "insert_selection_text_color": self.selected_insert_selection_text_color,
            "insert_selection_font_bold": self.insert_font_bold_checkbox.isChecked(),
            "insert_selection_font_italic": self.insert_font_italic_checkbox.isChecked(),
            "dynamic_refresh_interval": self.refresh_interval_spinbox.value()
        }
