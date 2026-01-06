import locale
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize
from PyQt6.QtGui import QAction, QPainter, QColor, QActionGroup, QPixmap, QIcon
from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QWidget, QComboBox, QLabel, QMessageBox, QSizePolicy, QToolBar, QStackedWidget, \
    QStatusBar

from app.translation_manager import translation_manager


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.get_width(), 0)

    def get_width(self):
        digits = 1
        max_num = max(1, self.editor.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1

        space = 3 + self.editor.fontMetrics().horizontalAdvance('9') * digits
        return space

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(Qt.GlobalColor.lightGray))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top())
        bottom = top + round(self.editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(0, top, self.width(), self.editor.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.editor.blockBoundingRect(block).height())
            block_number += 1


class FileViewerWindow(QMainWindow):
    closed = pyqtSignal()

    IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg', '.ico', '.tiff', '.webp']

    # Type hinting for UI elements loaded dynamically
    text_edit: QPlainTextEdit
    image_label: QLabel
    toolBar: QToolBar
    stackedWidget: QStackedWidget
    text_page: QWidget
    image_page: QWidget
    statusBar: QStatusBar

    def __init__(self, file_path, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), "file_viewer_dialog.ui")
        uic.loadUi(ui_path, self)

        self.setWindowFlags(Qt.WindowType.Window)

        self.file_path = file_path
        self.raw_bytes = b''
        self.current_view_mode = 'text'
        self.current_encoding = 'utf-8'
        self.original_pixmap = None

        self.setWindowTitle(f"{translation_manager.translate('FileViewer', 'File Viewer')} - {self.file_path}")

        self.line_number_area = LineNumberArea(self.text_edit)

        self.text_edit.blockCountChanged.connect(self.update_line_number_area_width)
        self.text_edit.updateRequest.connect(self.update_line_number_area)
        self.text_edit.cursorPositionChanged.connect(self.highlight_current_line)

        # Fix for image resizing issue: allow label to shrink
        self.image_label.setMinimumSize(1, 1)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self._setup_toolbar()
        self._load_file()

        self.update_line_number_area_width(0)

    def _setup_toolbar(self):
        # Properties Action
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "properties.svg")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.properties_action = QAction(icon, translation_manager.translate("FileViewer", "Properties"), self)
        else:
            self.properties_action = QAction(translation_manager.translate("FileViewer", "Properties"), self)

        self.properties_action.triggered.connect(self.open_properties)
        self.toolBar.addAction(self.properties_action)

        self.toolBar.addSeparator()

        # Word Wrap Action
        self.wrap_action = QAction(translation_manager.translate("FileViewer", "Word Wrap"), self)
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(True)
        self.wrap_action.triggered.connect(self.toggle_word_wrap)
        self.toolBar.addAction(self.wrap_action)

        # Line Numbers Action
        self.line_numbers_action = QAction(translation_manager.translate("FileViewer", "Line Numbers"), self)
        self.line_numbers_action.setCheckable(True)
        self.line_numbers_action.setChecked(True)
        self.line_numbers_action.triggered.connect(self.toggle_line_numbers)
        self.toolBar.addAction(self.line_numbers_action)

        self.toolBar.addSeparator()

        # Encoding ComboBox
        self.encoding_combo = QComboBox(self)
        self.encoding_combo.addItems(['UTF-8', 'Windows-1250', 'ISO-8859-2', 'Latin-1'])
        self.encoding_combo.currentTextChanged.connect(self.change_encoding)
        self.toolBar.addWidget(self.encoding_combo)

        self.toolBar.addSeparator()

        # View Mode Actions
        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.setExclusive(True)

        self.text_mode_action = QAction("Text", self)
        self.text_mode_action.setCheckable(True)
        self.text_mode_action.setChecked(True)
        self.text_mode_action.triggered.connect(lambda: self.change_view_mode('text'))
        self.view_mode_group.addAction(self.text_mode_action)
        self.toolBar.addAction(self.text_mode_action)

        self.picture_mode_action = QAction("Picture", self)
        self.picture_mode_action.setCheckable(True)
        self.picture_mode_action.triggered.connect(lambda: self.change_view_mode('picture'))
        self.view_mode_group.addAction(self.picture_mode_action)
        self.toolBar.addAction(self.picture_mode_action)

        self.hex_mode_action = QAction("HEX", self)
        self.hex_mode_action.setCheckable(True)
        self.hex_mode_action.triggered.connect(lambda: self.change_view_mode('hex'))
        self.view_mode_group.addAction(self.hex_mode_action)
        self.toolBar.addAction(self.hex_mode_action)

        self.dec_mode_action = QAction("DEC", self)
        self.dec_mode_action.setCheckable(True)
        self.dec_mode_action.triggered.connect(lambda: self.change_view_mode('dec'))
        self.view_mode_group.addAction(self.dec_mode_action)
        self.toolBar.addAction(self.dec_mode_action)

        self.bin_mode_action = QAction("BIN", self)
        self.bin_mode_action.setCheckable(True)
        self.bin_mode_action.triggered.connect(lambda: self.change_view_mode('bin'))
        self.view_mode_group.addAction(self.bin_mode_action)
        self.toolBar.addAction(self.bin_mode_action)

    def _load_file(self):
        file_extension = os.path.splitext(self.file_path)[1].lower()

        # Read file content first
        try:
            with open(self.file_path, 'rb') as f:
                self.raw_bytes = f.read(1024 * 1024 * 10)  # Read max 10MB
        except Exception as e:
            self.text_edit.setPlainText(f"Could not read file: {e}")
            self.stackedWidget.setCurrentWidget(self.text_page)
            return

        if file_extension in self.IMAGE_EXTENSIONS:
            self.original_pixmap = QPixmap(self.file_path)
            if not self.original_pixmap.isNull():
                self.picture_mode_action.setEnabled(True)
                self.picture_mode_action.setChecked(True)
                self.change_view_mode('picture')
            else:
                self.picture_mode_action.setEnabled(False)
                self.text_mode_action.setChecked(True)
                self.change_view_mode('text')
        else:
            self.picture_mode_action.setEnabled(False)
            self.text_mode_action.setChecked(True)
            self.change_view_mode('text')

    def open_properties(self):
        # Try to access the main window's logic handler
        parent = self.parent()
        if parent and hasattr(parent, 'application_logic_handler'):
            # We need to ensure the correct item is selected in the main window
            # The viewer might be open for a file that is not currently selected
            # But show_properties_dialog works on the selected item.
            # For now, we assume the user wants properties of the selected item in the browser.
            # Ideally, we should pass the file path to show_properties_dialog, but it doesn't accept arguments.
            # So we just call it and hope the selection matches.
            # A better approach would be to select the file in the browser first, but that's complex.
            parent.application_logic_handler.show_properties_dialog(parent=self)
        else:
            QMessageBox.warning(self, "Error", "Could not access application logic.")

    def _auto_detect_encoding(self):
        try:
            self.raw_bytes.decode('utf-8')
            self.current_encoding = 'utf-8'
        except UnicodeDecodeError:
            try:
                system_encoding = locale.getpreferredencoding()
                self.raw_bytes.decode(system_encoding)
                self.current_encoding = system_encoding
            except (UnicodeDecodeError, TypeError):
                self.current_encoding = 'latin-1'  # Fallback

        index = self.encoding_combo.findText(self.current_encoding, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.encoding_combo.blockSignals(True)
            self.encoding_combo.setCurrentIndex(index)
            self.encoding_combo.blockSignals(False)

    def update_display(self):
        content = ""
        status_message = ""

        # Update controls visibility/enabled state
        is_text_mode = self.current_view_mode == 'text'
        self.wrap_action.setEnabled(is_text_mode)
        self.line_numbers_action.setEnabled(is_text_mode)
        self.encoding_combo.setEnabled(is_text_mode)

        if self.current_view_mode == 'picture':
            self.stackedWidget.setCurrentWidget(self.image_page)
            if self.original_pixmap and not self.original_pixmap.isNull():
                self._update_image_scale()
                status_message = f"Image: {self.original_pixmap.width()}x{self.original_pixmap.height()}"
            else:
                self.image_label.setText("Invalid Image")
            self.statusBar.showMessage(status_message, 0)
            return

        # For other modes, switch to text page
        self.stackedWidget.setCurrentWidget(self.text_page)

        if self.current_view_mode == 'text':
            try:
                content = self.raw_bytes.decode(self.current_encoding)
                status_message = f"Encoding: {self.current_encoding}"
            except UnicodeDecodeError:
                content = f"Cannot display file with encoding '{self.current_encoding}'."
                status_message = f"Error: Invalid encoding '{self.current_encoding}'"

        elif self.current_view_mode == 'hex':
            content = ' '.join(f'{byte:02x}' for byte in self.raw_bytes)
            status_message = "View Mode: HEX"

        elif self.current_view_mode == 'dec':
            content = ' '.join(f'{byte}' for byte in self.raw_bytes)
            status_message = "View Mode: DEC"

        elif self.current_view_mode == 'bin':
            content = ' '.join(f'{byte:08b}' for byte in self.raw_bytes)
            status_message = "View Mode: BIN"

        self.text_edit.setPlainText(content)
        self.statusBar.showMessage(status_message, 0)

    def _update_image_scale(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            # Scale the image to fit the label, keeping aspect ratio
            # Use SmoothTransformation for better quality
            scaled_pixmap = self.original_pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def change_encoding(self, encoding_name):
        self.current_encoding = encoding_name.lower()
        self.update_display()

    def change_view_mode(self, mode):
        self.current_view_mode = mode
        self.update_display()

    def toggle_word_wrap(self, checked):
        if checked:
            self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def toggle_line_numbers(self, checked):
        self.line_number_area.setVisible(checked)
        self.update_line_number_area_width(0)

    def update_line_number_area_width(self, _):
        if self.line_numbers_action.isChecked():
            self.text_edit.setViewportMargins(self.line_number_area.get_width(), 0, 0, 0)
        else:
            self.text_edit.setViewportMargins(0, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.text_edit.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.stackedWidget.currentWidget() is self.text_page:
            cr = self.text_edit.contentsRect()
            self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area.get_width(), cr.height()))
        elif self.stackedWidget.currentWidget() is self.image_page:
            self._update_image_scale()

    def highlight_current_line(self):
        pass

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
