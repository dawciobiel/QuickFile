import logging
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager

try:
    from __version__ import __version__
except ImportError:
    __version__ = "Unknown Version"
    logging.warning("Could not import __version__. Using 'Unknown Version'.")

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/about_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("AboutDialog", "About"))
        
        self._init_ui()

    def _init_ui(self):
        self.textBrowser.setOpenExternalLinks(True)

        # Determine the current locale
        current_locale = translation_manager.current_locale

        # Extract the language code (e.g., 'pl' from 'pl_PL')
        lang_code = current_locale.split('_')[0].lower()

        # Construct the path to the HTML file
        base_path = os.path.dirname(os.path.abspath(__file__))
        docs_path = os.path.join(base_path, '..', 'docs', 'about')

        # Use the extracted language code to select the correct HTML file
        html_file_name = f'about_{lang_code}.html' if lang_code == 'pl' else 'about.html'
        html_file_path = os.path.join(docs_path, html_file_name)

        html_content = ""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            html_content = html_content.replace('{VERSION}', __version__)
        except FileNotFoundError:
            logging.error(f"About dialog HTML file not found: {html_file_path}")
            html_content = f"<h1>Error</h1><p>Could not load about information. Version: {__version__}</p>"
        except Exception as e:
            logging.error(f"Error loading about dialog HTML: {e}")
            html_content = f"<h1>Error</h1><p>Could not load about information. Version: {__version__}</p>"

        self.textBrowser.setHtml(html_content)
        
        # Configure button text if needed (standard buttons are usually localized)
        # self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
