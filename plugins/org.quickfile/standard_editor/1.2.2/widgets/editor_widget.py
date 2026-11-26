import codecs
import locale
import os
from PyQt6.QtWidgets import (
    QComboBox,
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QWidget,
    QHBoxLayout,
    QTextEdit,
    QVBoxLayout,
    QToolBar,
)
from PyQt6.QtGui import QColor, QPainter, QTextFormat
from PyQt6.QtCore import Qt, QRect

from .highlighter import PygmentsHighlighter
from .line_number_area import LineNumberArea
from utils.icon_manager import get_colorized_icon
from app.translation_manager import translation_manager

DEFAULT_ENCODING = "utf-8"
COMMON_ENCODINGS = (
    "utf-8",
    "utf-8-sig",
    "utf-16",
    "windows-1250",
    "windows-1252",
    "iso-8859-2",
    "latin-1",
)
OTHER_ENCODING = "Other..."


class EditorWidget(QWidget):
    def __init__(self, file_path: str, theme_manager, parent: QWidget = None):
        super().__init__(parent)
        self.file_path = file_path
        self.theme_manager = theme_manager
        self.last_search_query = ""
        self.encoding = DEFAULT_ENCODING
        self.load_failed = False
        self.icon_color = self.theme_manager.get_current_theme_data().get("foreground", "#000000")
        
        self.editor = QPlainTextEdit()
        self.line_number_area = LineNumberArea(self)

        file_content = self.load_file_content()

        self.highlighter = PygmentsHighlighter(self.editor.document(), self.file_path, file_content, self.theme_manager)

        self.init_ui()
        self.connect_signals()
        
        self.update_line_number_area_width(0)
        
        self.editor.setPlainText(file_content)
        if self.load_failed:
            self.editor.setReadOnly(True)
        self.editor.document().setModified(False)
        self.apply_theme()
        self.highlight_current_line()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar()
        main_layout.addWidget(self.toolbar)
        self._setup_toolbar()

        editor_layout = QHBoxLayout()
        editor_layout.setSpacing(0)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self.line_number_area)
        editor_layout.addWidget(self.editor)
        
        main_layout.addLayout(editor_layout)
        self.setLayout(main_layout)

    def _setup_toolbar(self):
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        icons_path = os.path.join(plugin_dir, "icons")

        def create_action(icon_name, text, slot):
            icon_path = os.path.join(icons_path, icon_name)
            action = self.toolbar.addAction(get_colorized_icon(icon_path, self.icon_color), text)
            action.triggered.connect(slot)
            return action

        create_action(
            "save.svg",
            translation_manager.translate("StandardEditor", "Save"),
            self.save_file,
        )
        self.toolbar.addSeparator()
        create_action(
            "undo.svg",
            translation_manager.translate("StandardEditor", "Undo"),
            self.editor.undo,
        )
        create_action(
            "redo.svg",
            translation_manager.translate("StandardEditor", "Redo"),
            self.editor.redo,
        )
        self.toolbar.addSeparator()
        create_action(
            "cut.svg",
            translation_manager.translate("StandardEditor", "Cut"),
            self.editor.cut,
        )
        create_action(
            "copy.svg",
            translation_manager.translate("StandardEditor", "Copy"),
            self.editor.copy,
        )
        create_action(
            "paste.svg",
            translation_manager.translate("StandardEditor", "Paste"),
            self.editor.paste,
        )

        self.toolbar.addSeparator()

        self.encoding_combo = QComboBox(self)
        for encoding in COMMON_ENCODINGS:
            self.encoding_combo.addItem(encoding, encoding)
        self.encoding_combo.addItem(
            translation_manager.translate("StandardEditor", "Other..."),
            OTHER_ENCODING,
        )
        self.encoding_combo.setToolTip(
            translation_manager.translate("StandardEditor", "File encoding")
        )
        self.encoding_combo.activated.connect(self._on_encoding_selected)
        self.toolbar.addWidget(self.encoding_combo)

        self.convert_action = self.toolbar.addAction(
            translation_manager.translate("StandardEditor", "Convert Encoding...")
        )
        self.convert_action.triggered.connect(self.choose_conversion_encoding)

        self._sync_encoding_combo()

    def find_text(self):
        query, ok = QInputDialog.getText(
            self,
            translation_manager.translate("StandardEditor", "Find Text"),
            translation_manager.translate("StandardEditor", "Enter text to find:"),
        )
        if ok and query:
            self.last_search_query = query
            self.find_next()

    def find_next(self):
        if self.last_search_query:
            self.editor.find(self.last_search_query)

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

    @staticmethod
    def detect_encoding(data: bytes) -> str:
        """Return the most likely encoding of ``data``.

        A BOM wins. Otherwise UTF-8 is tried first, then the system encoding,
        then the common single-byte encodings used for Polish and Western
        European text. Latin-1 accepts every byte, so it is the last resort.
        """
        if data.startswith(codecs.BOM_UTF8):
            return "utf-8-sig"
        if data.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
            return "utf-32"
        if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            return "utf-16"

        candidates = (
            "utf-8",
            locale.getpreferredencoding(False),
            "windows-1250",
            "windows-1252",
            "iso-8859-2",
            "latin-1",
        )
        seen = set()
        for candidate in candidates:
            if not candidate or candidate.lower() in seen:
                continue
            seen.add(candidate.lower())
            try:
                data.decode(candidate)
            except (UnicodeDecodeError, LookupError):
                continue
            return candidate
        return "latin-1"

    def load_file_content(self):
        try:
            with open(self.file_path, "rb") as handle:
                data = handle.read()
        except OSError as error:
            self.load_failed = True
            self.encoding = DEFAULT_ENCODING
            return translation_manager.translate(
                "StandardEditor", "Error loading file: {error}"
            ).format(error=error)

        self.encoding = self.detect_encoding(data)
        try:
            return data.decode(self.encoding)
        except UnicodeDecodeError as error:
            self.load_failed = True
            self.encoding = DEFAULT_ENCODING
            return translation_manager.translate(
                "StandardEditor", "Error loading file: {error}"
            ).format(error=error)

    @staticmethod
    def _is_valid_encoding(encoding: str) -> bool:
        try:
            codecs.lookup(encoding)
        except LookupError:
            return False
        return True

    def _sync_encoding_combo(self):
        if not hasattr(self, "encoding_combo"):
            return
        self.encoding_combo.blockSignals(True)
        index = self.encoding_combo.findData(self.encoding)
        if index < 0:
            other_index = self.encoding_combo.findData(OTHER_ENCODING)
            insert_at = (
                other_index if other_index >= 0 else self.encoding_combo.count()
            )
            self.encoding_combo.insertItem(insert_at, self.encoding, self.encoding)
            index = self.encoding_combo.findData(self.encoding)
        self.encoding_combo.setCurrentIndex(index)
        self.encoding_combo.blockSignals(False)

    def _read_file(self, encoding: str) -> str:
        with open(self.file_path, "rb") as handle:
            return handle.read().decode(encoding)

    def set_display_encoding(self, encoding: str) -> bool:
        """Reload the file with ``encoding`` without converting it."""
        if not self._is_valid_encoding(encoding):
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Unknown Encoding"),
                translation_manager.translate(
                    "StandardEditor", "Unknown encoding: {encoding}."
                ).format(encoding=encoding),
            )
            return False

        if encoding == self.encoding:
            return True

        if self.has_unsaved_changes():
            choice = QMessageBox.question(
                self,
                translation_manager.translate("StandardEditor", "Unsaved Changes"),
                translation_manager.translate(
                    "StandardEditor",
                    "Reload {name} with {encoding}? Unsaved changes can be saved first.",
                ).format(
                    name=os.path.basename(self.file_path), encoding=encoding
                ),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if choice == QMessageBox.StandardButton.Cancel:
                return False
            if (
                choice == QMessageBox.StandardButton.Save
                and not self.save_file()
            ):
                return False

        try:
            content = self._read_file(encoding)
        except (OSError, UnicodeDecodeError, LookupError):
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Cannot Reload"),
                translation_manager.translate(
                    "StandardEditor", "Could not decode {name} as {encoding}."
                ).format(
                    name=os.path.basename(self.file_path), encoding=encoding
                ),
            )
            return False

        self.encoding = encoding
        self.editor.setPlainText(content)
        self.editor.document().setModified(False)
        self._sync_encoding_combo()
        return True

    def convert_encoding(self, encoding: str) -> bool:
        """Use ``encoding`` for the next save of the current text.

        The file is not written here. The document is marked modified so the
        usual Save/close prompt writes the new encoding; characters the target
        cannot represent abort the conversion.
        """
        if not self._is_valid_encoding(encoding):
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Unknown Encoding"),
                translation_manager.translate(
                    "StandardEditor", "Unknown encoding: {encoding}."
                ).format(encoding=encoding),
            )
            return False

        if encoding == self.encoding:
            return True
        if self.load_failed:
            return False

        text = self.editor.toPlainText()
        try:
            text.encode(encoding)
        except UnicodeEncodeError as error:
            character = text[error.start:error.end]
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Cannot Convert"),
                translation_manager.translate(
                    "StandardEditor",
                    "Could not convert {name} to {encoding}: {character!r} "
                    "at position {position} cannot be represented.",
                ).format(
                    name=os.path.basename(self.file_path),
                    encoding=encoding,
                    character=character,
                    position=error.start,
                ),
            )
            return False

        self.encoding = encoding
        self.editor.document().setModified(True)
        self._sync_encoding_combo()
        return True

    def _ask_for_encoding(self):
        name, ok = QInputDialog.getText(
            self,
            translation_manager.translate("StandardEditor", "Custom Encoding"),
            translation_manager.translate(
                "StandardEditor",
                "Enter a Python codec name (for example windows-1251):",
            ),
        )
        if not ok or not name.strip():
            return None
        return name.strip()

    def _on_encoding_selected(self, index: int):
        selected = self.encoding_combo.itemData(index)
        if selected == OTHER_ENCODING:
            encoding = self._ask_for_encoding()
            if encoding is None:
                self._sync_encoding_combo()
                return
        else:
            encoding = selected

        if not self.set_display_encoding(encoding):
            self._sync_encoding_combo()

    def choose_conversion_encoding(self):
        other_label = translation_manager.translate("StandardEditor", "Other...")
        items = [*COMMON_ENCODINGS, other_label]
        choice, ok = QInputDialog.getItem(
            self,
            translation_manager.translate("StandardEditor", "Convert Encoding"),
            translation_manager.translate(
                "StandardEditor", "Convert {name} to:"
            ).format(name=os.path.basename(self.file_path)),
            items,
            0,
            False,
        )
        if not ok:
            return
        if choice == other_label:
            choice = self._ask_for_encoding()
            if choice is None:
                return
        self.convert_encoding(choice)

    def has_unsaved_changes(self):
        return self.editor.document().isModified()

    def save_file(self):
        if self.load_failed:
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Save Failed"),
                translation_manager.translate(
                    "StandardEditor",
                    "Could not save {name}: the file was not loaded.",
                ).format(name=os.path.basename(self.file_path)),
            )
            return False

        text = self.editor.toPlainText()
        try:
            text.encode(self.encoding)
        except UnicodeEncodeError as error:
            character = text[error.start:error.end]
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Save Failed"),
                translation_manager.translate(
                    "StandardEditor",
                    "Could not save {name} as {encoding}: {character!r} "
                    "at position {position} cannot be represented.",
                ).format(
                    name=os.path.basename(self.file_path),
                    encoding=self.encoding,
                    character=character,
                    position=error.start,
                ),
            )
            return False

        try:
            with open(self.file_path, "w", encoding=self.encoding) as handle:
                handle.write(text)
        except OSError as error:
            QMessageBox.warning(
                self,
                translation_manager.translate("StandardEditor", "Save Failed"),
                translation_manager.translate(
                    "StandardEditor", "Could not save {name}: {error}"
                ).format(
                    name=os.path.basename(self.file_path), error=error
                ),
            )
            return False

        self.editor.document().setModified(False)
        return True
