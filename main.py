#!/usr/bin/env python3

import sys
import logging
import traceback
import os

from PyQt6.QtWidgets import QMainWindow, QLineEdit, QVBoxLayout, QWidget, QCompleter
from PyQt6.QtCore import Qt

from __version__ import __version__

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale

from ui.main_window import MainWindow
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
    
    # --- Translation Loading Logic with Debugging ---
    system_locale = QLocale.system().name() # e.g., 'en_US', 'pl_PL'
    logging.debug(f"TRANSLATION: Detected system locale: '{system_locale}'")
    
    translations_path = os.path.join(os.path.dirname(__file__), "translations")
    logging.debug(f"TRANSLATION: Translations directory path: '{translations_path}'")

    translation_loaded = False
    active_translation_file = "None"

    # 1. Try to load for the full locale (e.g., 'app_pl_PL.qm')
    full_locale_filename = f"app_{system_locale}"
    logging.debug(f"TRANSLATION: Attempting to load full locale file: '{full_locale_filename}.qm'")
    if app_translator.load(full_locale_filename, translations_path):
        active_translation_file = f"{full_locale_filename}.qm"
        logging.info(f"TRANSLATION SUCCESS: Loaded full locale: {active_translation_file}")
        translation_loaded = True
    else:
        logging.warning(f"TRANSLATION: Failed to load '{full_locale_filename}.qm'. Falling back to language-only.")
        
        # 2. Fallback to language only (e.g., 'app_pl.qm')
        language_code = system_locale.split('_')[0]
        lang_code_filename = f"app_{language_code}"
        logging.debug(f"TRANSLATION: Attempting to load language-only file: '{lang_code_filename}.qm'")
        if app_translator.load(lang_code_filename, translations_path):
            active_translation_file = f"{lang_code_filename}.qm"
            logging.info(f"TRANSLATION SUCCESS: Loaded language-only: {active_translation_file}")
            translation_loaded = True
        else:
            logging.warning(f"TRANSLATION: Failed to load '{lang_code_filename}.qm'. Defaulting to English.")
            # 3. Fallback to English as a last resort
            if app_translator.load("app_en", translations_path):
                active_translation_file = "app_en.qm"
                logging.info("TRANSLATION: Loaded fallback English 'app_en.qm'.")
                translation_loaded = True # Assuming app_en.qm is always present
            else:
                logging.error("TRANSLATION: CRITICAL - Could not load any translation files, not even English.")

    if translation_loaded:
        app.installTranslator(app_translator)
        logging.info(f"TRANSLATION: Translator installed. Active file: {active_translation_file}")
    else:
        logging.warning("TRANSLATION: No translator installed. Application will run in default (source) language.")

    window = MainWindow()
    app.installEventFilter(window.keyboard_event_handler) # Install the KeyboardEventHandler as the event filter
    window.show()
    app.exec()
