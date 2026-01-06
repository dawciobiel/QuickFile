from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import QRegularExpression

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keyword format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = ["def", "class", "import", "from", "return", "if", "else", "elif", "while", "for", "in", "try", "except", "finally", "with", "as", "self"]
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            rule = (pattern, keyword_format)
            self.highlighting_rules.append(rule)

        # Comment format
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("green"))
        self.highlighting_rules.append((QRegularExpression("#[^\n]*"), comment_format))

        # String format
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("red"))
        self.highlighting_rules.append((QRegularExpression("\".*\""), string_format))
        self.highlighting_rules.append((QRegularExpression("'.*'"), string_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            it = expression.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
