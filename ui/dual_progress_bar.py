from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QProgressBar, QStyleOptionProgressBar, QStyle, QStylePainter


class DualProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._read_value = 0
        # Define colors for read progress (e.g., a lighter shade or distinct color)
        # We can make this customizable via properties or themes later
        self._read_color = QColor(100, 200, 255, 150)  # Light blue, semi-transparent

    def setReadValue(self, value):
        """Sets the progress of the read operation (0-maximum)."""
        if self._read_value != value:
            self._read_value = value
            self.update()

    def readValue(self):
        return self._read_value

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionProgressBar()
        self.initStyleOption(opt)
        
        # Draw the groove (background)
        painter.drawControl(QStyle.ControlElement.CE_ProgressBarGroove, opt)

        # Calculate geometry for the read progress
        if self.maximum() > self.minimum():
            total_steps = self.maximum() - self.minimum()

            # Draw Read Progress
            read_ratio = (self._read_value - self.minimum()) / total_steps
            read_ratio = max(0.0, min(1.0, read_ratio))

            if read_ratio > 0:
                # Use SE_ProgressBarContents to draw inside the groove (border)
                contents_rect = self.style().subElementRect(QStyle.SubElement.SE_ProgressBarContents, opt, self)
                
                read_width = int(contents_rect.width() * read_ratio)
                
                # Adjust rect to avoid painting over the border
                # We shrink it slightly to be safe
                read_rect = QRect(contents_rect.x(), contents_rect.y(), read_width, contents_rect.height())
                
                # Ensure we don't draw outside the contents rect on the right side
                if read_rect.right() > contents_rect.right():
                    read_rect.setRight(contents_rect.right())

                # Draw the read chunk
                painter.save()
                painter.setBrush(self._read_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(read_rect)
                painter.restore()

        # Draw the Write Progress (standard value) using native style
        # This will draw the "chunk" for the main value (write)
        painter.drawControl(QStyle.ControlElement.CE_ProgressBarContents, opt)

        # Draw the text (percentage) on top
        painter.drawControl(QStyle.ControlElement.CE_ProgressBarLabel, opt)
