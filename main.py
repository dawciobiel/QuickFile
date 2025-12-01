import sys
import logging
import traceback
import os

from __version__ import __version__

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale

from core.main_window import MainWindow
from utils.dialogs import show_error_message
from utils.logger import setup_logging

# Globals for translator (to keep a reference and prevent garbage collection)
app_translator = None


def global_exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception hook to catch unhandled exceptions.
    """
    # Log the exception
    logger = logging.getLogger(__name__)
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Unhandled exception:\n{tb_str}")

    # Show a dialog to the user
    show_error_message(None, "Critical Error Occurred",
                       "The application encountered an unexpected error.\n"
                       "Details have been written to the log file.")

    # It's generally a good idea to exit the application after an unhandled exception.
    # Depending on the error, the application state might be corrupted.
    QApplication.quit()


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    logging.info("Application started.")

    # Set the global exception hook
    sys.excepthook = global_exception_hook

    app = QApplication([])


    app_translator = QTranslator()
    
    # Try to load system locale
    system_locale = QLocale().system().name() # e.g., 'en_US', 'pl_PL'
    translations_path = os.path.join(os.path.dirname(__file__), "translations")
    
    # Try loading for the full locale (e.g., 'app_en_US.qm')
    if not app_translator.load(f"app_{system_locale}", translations_path):
        # Fallback to language only (e.g., 'app_en.qm')
        language_code = system_locale.split('_')[0]
        if not app_translator.load(f"app_{language_code}", translations_path):
            # Fallback to Polish if nothing else works
            logging.warning(f"Could not load translations for system locale '{system_locale}' or language '{language_code}'. Defaulting to Polish.")
            app_translator.load("app_pl", translations_path)
            
    app.installTranslator(app_translator)

    window = MainWindow()
    app.installEventFilter(window)
    window.show()
    app.exec()
