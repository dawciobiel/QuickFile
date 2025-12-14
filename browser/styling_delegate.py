from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt
from browser.flat_file_system_model import FileStyleRole

class FileStyleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        
        style_data = index.data(FileStyleRole)
        
        if style_data:
            # Apply foreground color
            if "foreground_color" in style_data:
                option.palette.setColor(QPalette.ColorRole.Text, QColor(style_data["foreground_color"]))
            
            # Apply font weight
            if style_data.get("font_weight") == "bold":
                option.font.setBold(True)
            
            # Apply font style
            if style_data.get("font_italic"):
                option.font.setItalic(True)
                
            # Apply strikethrough
            if style_data.get("font_strikethrough"):
                option.font.setStrikeOut(True)
