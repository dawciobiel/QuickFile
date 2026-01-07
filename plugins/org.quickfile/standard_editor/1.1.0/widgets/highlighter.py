import logging
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pygments.formatter import Formatter
from pygments.token import Token

class PygmentsFormatter(Formatter):
    def __init__(self):
        super().__init__()
        self.data = []

    def format(self, tokensource, outfile):
        self.data = []
        for token, value in tokensource:
            self.data.append((token, value))

class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, file_path, file_content, theme_manager):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.formatter = PygmentsFormatter()
        try:
            self.lexer = guess_lexer_for_filename(file_path, file_content)
            logging.debug(f"PygmentsHighlighter: Using lexer: {self.lexer.name}")
        except Exception as e:
            logging.warning(f"PygmentsHighlighter: Could not guess lexer for {file_path}, falling back to text. Error: {e}")
            self.lexer = get_lexer_by_name("text")

        self.update_styles()

    def update_styles(self, styles=None):
        if styles is None and self.theme_manager:
            theme_data = self.theme_manager.get_current_theme_data()
            styles = theme_data.get("code_highlighting", {})

        self.styles = {
            Token.Keyword: self.create_format(styles.get("keyword")),
            Token.Name.Function: self.create_format(styles.get("function_name")),
            Token.Name.Class: self.create_format(styles.get("class_name")),
            Token.String: self.create_format(styles.get("string")),
            Token.Comment: self.create_format(styles.get("comment"), italic=True),
            Token.Operator: self.create_format(styles.get("operator")),
            Token.Number: self.create_format(styles.get("number")),
            Token.Text: self.create_format(styles.get("text")),
        }

    def create_format(self, color_hex, bold=False, italic=False):
        char_format = QTextCharFormat()
        if color_hex:
            char_format.setForeground(QColor(color_hex))
        if bold:
            char_format.setFontWeight(QFont.Weight.Bold)
        if italic:
            char_format.setFontItalic(italic)
        return char_format

    def highlightBlock(self, text):
        if not text:
            return

        highlight(text, self.lexer, self.formatter)
        
        if not self.formatter.data:
            return

        start = 0
        for token, value in self.formatter.data:
            length = len(value)
            style = self.styles.get(token)
            
            if style is None:
                parent_token = token.parent
                while parent_token is not None:
                    style = self.styles.get(parent_token)
                    if style:
                        break
                    parent_token = parent_token.parent

            if style:
                self.setFormat(start, length, style)
            
            start += length
