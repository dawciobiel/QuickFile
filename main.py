#!/usr/bin/env python3

import sys
import logging
import traceback
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from __version__ import __version__

from ui.main_window import MainWindow
from utils.dialogs import show_error_message
from utils.logger import setup_logging
from app.translation_manager import translation_manager # Import our new manager
from app.keyboard_event_handler import KeyboardEventManager # Import our new manager


def global_exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception hook to catch unhandled exceptions.
    """
    # Log the exception
    logger = logging.getLogger(__name__)
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Unhandled exception:\n{tb_str}")

    # Show a dialog to the user
    show_error_message(None, translation_manager.translate("Global", "Critical Error Occurred"),
                       translation_manager.translate("Global", "The application encountered an unexpected error.\nDetails have been written to the log file."))

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

    # Initialize our custom TranslationManager
    # It will automatically detect locale and load translations
    # The translation_manager instance is already created globally

    window = MainWindow()
    # Install the KeyboardEventManager as the global event filter
    # window.keyboard_event_manager = KeyboardEventManager(window) # This is already done in MainWindow's __init__
    app.installEventFilter(window.keyboard_event_manager) # Install the event filter

    window.show()
    app.exec()
