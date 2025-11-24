import sys
import logging
import traceback

from PyQt6.QtWidgets import QApplication

from core.main_window import MainWindow
from utils.dialogs import show_error_message
from utils.logger import setup_logging


def global_exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception hook to catch unhandled exceptions.
    """
    # Log the exception
    logger = logging.getLogger(__name__)
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Unhandled exception:\n{tb_str}")

    # Show a dialog to the user
    show_error_message(None, "Wystąpił krytyczny błąd",
                       "Aplikacja napotkała nieoczekiwany błąd.\n"
                       "Szczegóły zostały zapisane w pliku logu.")

    # It's generally a good idea to exit the application after an unhandled exception.
    # Depending on the error, the application state might be corrupted.
    QApplication.quit()


if __name__ == "__main__":
    # Setup logging
    setup_logging()

    # Set the global exception hook
    sys.excepthook = global_exception_hook

    app = QApplication([])

    window = MainWindow()
    app.installEventFilter(window)
    window.show()
    app.exec()
