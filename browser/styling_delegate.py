from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle

FileStyleRole = Qt.ItemDataRole.UserRole + 1

class FileStyleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        # Create a copy of the option to modify it without affecting other delegates
        opt = option
        self.initStyleOption(opt, index)

        # Retrieve style data from the model
        style_data = index.data(FileStyleRole)

        if style_data:
            # Apply foreground color
            if "foreground_color" in style_data:
                color = QColor(style_data["foreground_color"])
                if color.isValid():
                    # Only apply custom color if the item is NOT selected
                    # Otherwise, use the system's selection text color for better contrast
                    if not (opt.state & QStyle.StateFlag.State_Selected):
                        opt.palette.setColor(QPalette.ColorRole.Text, color)

            # Apply font styles
            if "font_weight" in style_data and style_data["font_weight"] == "bold":
                opt.font.setBold(True)
            if "font_italic" in style_data and style_data["font_italic"]:
                opt.font.setItalic(True)
            if "font_strikethrough" in style_data and style_data["font_strikethrough"]:
                opt.font.setStrikeOut(True)

        # Let the base class handle the painting with our modified options
        super().paint(painter, opt, index)

        # Custom styling for insert-selected items (overlay)
        # We need to access the model directly here as this is specific logic
        # Ideally, this should also be exposed via data() role, but for now:
        if hasattr(index.model(), '_insert_selected_items'):
            file_path = index.model().filePath(index)
            if file_path and file_path in index.model()._insert_selected_items:
                if not (opt.state & QStyle.StateFlag.State_Selected):
                    painter.save()
                    rect = opt.rect
                    overlay_color = QColor(255, 255, 0, 40)  # Semi-transparent yellow
                    painter.fillRect(rect, overlay_color)
                    painter.restore()
