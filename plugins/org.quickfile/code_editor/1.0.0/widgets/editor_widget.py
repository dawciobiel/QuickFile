from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QHBoxLayout, QTextEdit
from PyQt6.QtGui import QColor, QPainter, QTextFormat
from PyQt6.QtCore import Qt, QRect, QSize

from .highlighter import PygmentsHighlighter
from .line_number_area import LineNumberArea

class EditorWidget(QWidget):
    def __init__(self, file_path: str, theme_manager, parent: QWidget = None):
        super().__init__(parent)
        self.file_path = file_path
        self.theme_manager = theme_manager
        
        self.editor = QPlainTextEdit()
        self.line_number_area = LineNumberArea(self)

        file_content = self.load_file_content()

        self.highlighter = PygmentsHighlighter(self.editor.document(), self.file_path, file_content, self.theme_manager)

        self.init_ui()
        self.connect_signals()
        
        self.update_line_number_area_width(0)
        
        self.editor.setPlainText(file_content)
        self.apply_theme()
        self.highlight_current_line()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_number_area)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def connect_signals(self):
        self.editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor.updateRequest.connect(self.update_line_number_area)
        self.editor.cursorPositionChanged.connect(self.highlight_current_line)
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self.apply_theme)

    def apply_theme(self):
        if not self.theme_manager:
            return
            
        theme_data = self.theme_manager.get_current_theme_data()
        if theme_data and "code_highlighting" in theme_data:
            styles = theme_data["code_highlighting"]
            
            self.editor.setStyleSheet(f"background-color: {styles.get('background', '#ffffff')}; color: {styles.get('text', '#000000')};")
            
            self.highlighter.update_styles(styles)
            self.highlighter.rehighlight()
            
            self.highlight_current_line()
            self.line_number_area.update()

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        
        styles = {}
        if self.theme_manager:
            theme_data = self.theme_manager.get_current_theme_data()
            styles = theme_data.get("code_highlighting", {})
        
        painter.fillRect(event.rect(), QColor(styles.get("line_number_background", "#f0f0f0")))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(styles.get("line_number_foreground", "#a0a0a0")))
                painter.drawText(0, int(top), self.line_number_area.width(), self.editor.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_number += 1

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.editor.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        space = 3 + self.editor.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.editor.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.editor.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.editor.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.editor.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            styles = {}
            if self.theme_manager:
                theme_data = self.theme_manager.get_current_theme_data()
                styles = theme_data.get("code_highlighting", {})

            line_color = QColor(styles.get("current_line_background", "#e8f0fe"))
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.editor.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.editor.setExtraSelections(extra_selections)

    def load_file_content(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error loading file: {e}"

    def save_file(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
