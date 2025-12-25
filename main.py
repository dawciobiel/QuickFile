#!/usr/bin/env python3

import sys
import logging
import traceback
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from __version__ import __version__

from app.background_task_manager import BackgroundTaskManager
from app.task_queue_manager import TaskQueueManager
from app.plugin_manager import PluginManager
from file_operations.directory_synchronizer import DirectorySynchronizer
from file_operations.file_manager import FileManager
from ui.main_window import MainWindow
from utils.dialogs import show_error_message
from utils.logger import setup_logging
from app.translation_manager import translation_manager
from app.keyboard_event_handler import KeyboardEventManager


def global_exception_hook(exc_type, exc_value, exc_traceback):
    logger = logging.getLogger(__name__)
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Unhandled exception:\n{tb_str}")

    show_error_message(None, translation_manager.translate("Global", "Critical Error Occurred"),
                       translation_manager.translate("Global", "The application encountered an unexpected error.\nDetails have been written to the log file."))

    QApplication.quit()


if __name__ == "__main__":
    setup_logging()
    logging.info("Application started.")

    sys.excepthook = global_exception_hook

    app = QApplication([])

    background_task_manager = BackgroundTaskManager()
    file_manager = FileManager()
    directory_synchronizer = DirectorySynchronizer()
    plugin_manager = PluginManager()
    
    task_queue_manager = TaskQueueManager(background_task_manager, file_manager, directory_synchronizer, plugin_manager)
    
    window = MainWindow(
        background_task_manager=background_task_manager, 
        task_queue_manager=task_queue_manager,
        file_manager=file_manager,
        directory_synchronizer=directory_synchronizer
    )
    app.installEventFilter(window.keyboard_event_manager)

    window.show()

    if window.settings_manager.get_setting("bringToFrontOnStartup"):
        window.raise_()
        window.activateWindow()

    app.exec()
