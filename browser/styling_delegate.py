from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle  # Import QStyle

from browser.flat_file_system_model import FileStyleRole


class FileStyleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        # Flag to check if any custom "Insert" style was applied
        insert_style_applied = False

        # 1. Apply theme-based file styles (from file_styles.json)
        style_data = index.data(FileStyleRole)
        if style_data:
            if "foreground_color" in style_data:
                option.palette.setColor(QPalette.ColorRole.Text, QColor(style_data["foreground_color"]))
            if "background_color" in style_data:
                option.palette.setColor(QPalette.ColorRole.Base, QColor(style_data["background_color"]))
                option.palette.setColor(QPalette.ColorRole.AlternateBase, QColor(style_data["background_color"]))
            if style_data.get("font_weight") == "bold":
                option.font.setBold(True)
            if style_data.get("font_italic"):
                option.font.setItalic(True)
            if style_data.get("font_strikethrough"):
                option.font.setStrikeOut(True)

        # 2. Apply "Insert" selection styles (these should override theme styles)
        insert_fg_color = index.data(Qt.ItemDataRole.ForegroundRole)
        # insert_bg_color = index.data(Qt.ItemDataRole.BackgroundRole) # Removed
        insert_font = index.data(Qt.ItemDataRole.FontRole)

        if insert_fg_color is not None:
            option.palette.setColor(QPalette.ColorRole.Text, insert_fg_color)
            insert_style_applied = True

        # Removed BackgroundRole handling
        # if insert_bg_color is not None:
        #     option.palette.setColor(QPalette.ColorRole.Base, insert_bg_color)
        #     option.palette.setColor(QPalette.ColorRole.AlternateBase, insert_bg_color)
        #     insert_style_applied = True

        if insert_font is not None:
            option.font = insert_font
            insert_style_applied = True

        # If any "Insert" style was applied, remove the default selection state
        # to prevent it from being drawn over our custom background.
        if insert_style_applied:
            option.state &= ~QStyle.StateFlag.State_Selected
