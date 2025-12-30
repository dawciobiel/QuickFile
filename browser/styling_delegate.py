from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle

FileStyleRole = Qt.ItemDataRole.UserRole + 1

class FileStyleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_font = QFont()
        self.bold_font = QFont()
        self.bold_font.setBold(True)

    def paint(self, painter, option, index):
        # Let the base class handle the painting first
        super().paint(painter, option, index)

        # Custom styling for insert-selected items
        if index.model().filePath(index) in index.model()._insert_selected_items:
            if option.state & QStyle.StateFlag.State_Selected:
                # If the item is also selected by the view, we might not need to do anything extra
                # or we could blend colors, but for now, let's just let the selection style dominate.
                pass
            else:
                # Apply custom style for insert-selection only when not normally selected
                painter.save()
                
                # Example: draw a colored rectangle over the row
                # You can get colors/fonts from settings manager if needed
                rect = option.rect
                # A subtle overlay color
                overlay_color = QColor(255, 255, 0, 20) # Semi-transparent yellow
                painter.fillRect(rect, overlay_color)
                
                painter.restore()

        # You can add more custom painting logic here if needed
