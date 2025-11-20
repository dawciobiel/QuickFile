import os
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt5.QtGui import QPainter, QColor, QTextFormat, QTextBlock, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtCore import Qt, QRect, QSize, QRegExp


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class PlainHighlighter(QSyntaxHighlighter):
    """Prosty podświetlacz, który nie podświetla niczego."""
    def __init__(self, document):
        super().__init__(document)

    def highlightBlock(self, text):
        pass


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        # Formaty dla różnych typów składni
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(200, 120, 50))
        keyword_format.setFontWeight(QTextCharFormat.Bold)

        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor(150, 150, 0))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(20, 110, 100))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)

        numbers_format = QTextCharFormat()
        numbers_format.setForeground(QColor(100, 150, 200))

        self.highlighting_rules = []

        # Słowa kluczowe Pythona
        keywords = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
                    'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
                    'except', 'finally', 'for', 'from', 'global', 'if', 'import',
                    'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
                    'return', 'try', 'while', 'with', 'yield']
        for word in keywords:
            pattern = QRegExp(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, keyword_format))

        # Operatory
        operators = [r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=', r'\\+', r'-', r'\\*', r'/', r'//',
                     r'\\%', r'\\*\\*', r'\\+=', r'-=', r'\\*=', r'/=', r'\\%=', r'\\&=', r'\\|=', r'\\^=',
                     r'<<=', r'>>=', r'\\*\\*=', r'//=', 'and', 'or', 'not']
        for operator in operators:
            pattern = QRegExp(operator)
            self.highlighting_rules.append((pattern, operator_format))

        # Stringi (pojedyncze i podwójne cudzysłowy)
        self.highlighting_rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Komentarze
        self.highlighting_rules.append((QRegExp(r'#[^\n]*'), comment_format))

        # Liczby
        self.highlighting_rules.append((QRegExp(r'\b[0-9]+\b'), numbers_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        header_format = QTextCharFormat()
        header_format.setForeground(QColor(50, 50, 200))
        header_format.setFontWeight(QTextCharFormat.Bold)

        bold_format = QTextCharFormat()
        bold_format.setForeground(QColor(0, 0, 0))
        bold_format.setFontWeight(QTextCharFormat.Bold)

        italic_format = QTextCharFormat()
        italic_format.setForeground(QColor(0, 0, 0))
        italic_format.setFontItalic(True)

        code_format = QTextCharFormat()
        code_format.setForeground(QColor(150, 50, 50))
        code_format.setFontFamily("monospace")

        link_format = QTextCharFormat()
        link_format.setForeground(QColor(0, 100, 0))
        link_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)

        self.highlighting_rules = []

        # Headers
        self.highlighting_rules.append((QRegExp(r'^#.*'), header_format))
        self.highlighting_rules.append((QRegExp(r'^##.*'), header_format))
        self.highlighting_rules.append((QRegExp(r'^###.*'), header_format))
        self.highlighting_rules.append((QRegExp(r'^####.*'), header_format))
        self.highlighting_rules.append((QRegExp(r'^#####.*'), header_format))
        self.highlighting_rules.append((QRegExp(r'^######.*'), header_format))

        # Bold
        self.highlighting_rules.append((QRegExp(r'\*\*[^<>]+\*\*'), bold_format))
        self.highlighting_rules.append((QRegExp(r'__[^<>]+__'), bold_format))

        # Italic
        self.highlighting_rules.append((QRegExp(r'\*[^*]+\*'), italic_format))
        self.highlighting_rules.append((QRegExp(r'_[^_]+_'), italic_format))

        # Code
        self.highlighting_rules.append((QRegExp(r'`[^`]+`'), code_format))

        # Links (basic)
        self.highlighting_rules.append((QRegExp(r'\[[^\]]+\]\([^\)]+\)'), link_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)


class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        key_format = QTextCharFormat()
        key_format.setForeground(QColor(170, 0, 0))
        key_format.setFontWeight(QTextCharFormat.Bold)

        value_string_format = QTextCharFormat()
        value_string_format.setForeground(QColor(0, 128, 0))

        value_number_format = QTextCharFormat()
        value_number_format.setForeground(QColor(0, 0, 170))

        boolean_null_format = QTextCharFormat()
        boolean_null_format.setForeground(QColor(170, 0, 170))
        boolean_null_format.setFontWeight(QTextCharFormat.Bold)

        self.highlighting_rules = []

        # Keys
        self.highlighting_rules.append((QRegExp(r'"[a-zA-Z0-9_]+"\s*:'), key_format))

        # String values
        self.highlighting_rules.append((QRegExp(r':\s*"[^"\\]*(\\.[^"\\]*)*"'), value_string_format))

        # Number values
        self.highlighting_rules.append((QRegExp(r':\s*\b[0-9]+\b'), value_number_format))
        self.highlighting_rules.append((QRegExp(r':\s*\b[0-9]*\.[0-9]+\b'), value_number_format))

        # Boolean and null values
        self.highlighting_rules.append((QRegExp(r':\s*\b(true|false|null)\b'), boolean_null_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                # Adjust for key format to not include colon
                if format == self.highlighting_rules[0][1]: # If it's a key
                    self.setFormat(index, length - 1, format)
                else:
                    # Adjust for value formats to not include colon and space
                    if text[index:index+2] == ": ":
                        self.setFormat(index + 2, length - 2, format)
                    else:
                        self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)


class FileEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.current_file_path = None
        self.setPlaceholderText("Zaznacz plik tekstowy, aby zobaczyć jego zawartość...")

        self.lineNumberArea = LineNumberArea(self)
        self.highlighter = None  # Inicjalizacja na None

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, newBlockCount):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(230, 230, 230))  # Kolor tła dla numerów linii

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Loop over all visible text blocks in the document.
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor(120, 120, 120))  # Kolor tekstu numerów linii
                painter.drawText(0, int(top), self.lineNumberArea.width(), self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.yellow).lighter(160)  # Kolor podświetlenia linii

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def set_highlighter_by_file_extension(self, file_path):
        """Ustawia podświetlacz składni na podstawie rozszerzenia pliku."""
        if self.highlighter:
            self.highlighter.setDocument(None)  # Odłącz poprzedni podświetlacz

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext == '.py':
            self.highlighter = PythonHighlighter(self.document())
        elif ext == '.md':
            self.highlighter = MarkdownHighlighter(self.document())
        elif ext == '.json':
            self.highlighter = JsonHighlighter(self.document())
        else:
            self.highlighter = PlainHighlighter(self.document())  # Domyślny podświetlacz

    def display_file_content(self, file_path):
        """Wyświetla zawartość pliku lub komunikat, jeśli nie można go odczytać."""
        self.current_file_path = file_path
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.setPlainText(content)
            self.setReadOnly(False)  # Umożliwienie edycji po otwarciu pliku
            self.set_highlighter_by_file_extension(file_path)  # Ustaw podświetlacz
        except Exception as e:
            self.setPlainText(f"Nie można otworzyć pliku: {file_path}\n\nBłąd: {e}")
            self.current_file_path = None
            self.setReadOnly(True)  # Blokowanie edycji, jeśli plik nie mógł być otwarty
            self.set_highlighter_by_file_extension("")  # Ustaw domyślny podświetlacz

    def save_file(self):
        """Zapisuje bieżącą zawartość do pliku."""
        if self.current_file_path:
            try:
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(self.toPlainText())
                return True, None
            except Exception as e:
                return False, str(e)
        return False, "Brak otwartego pliku do zapisania."
