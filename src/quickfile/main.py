# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
import sys

from PyQt6.QtWidgets import QApplication

from quickfile.app.background_task_manager import BackgroundTaskManager
from quickfile.app.plugin_manager import PluginManager
from quickfile.app.task_queue_manager import TaskQueueManager
from quickfile.app.notification_manager import NotificationManager
from quickfile.app.file_association_manager import FileAssociationManager
from quickfile.app.settings_manager import SettingsManager
from quickfile.file_operations.directory_synchronizer import DirectorySynchronizer
from quickfile.file_operations.file_manager import FileManager
from quickfile.ui.main_window import MainWindow


def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure root logger
    # force=True ensures that we overwrite any existing configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "main.log"), mode='w'),
            logging.StreamHandler()
        ],
        force=True
    )

    # Suppress overly verbose logs from PyQt6.uic
    logging.getLogger("PyQt6.uic.uiparser").setLevel(logging.WARNING)
    logging.getLogger("PyQt6.uic.properties").setLevel(logging.WARNING)

    logging.info("Logging configured successfully.")  # Test log


def main():
    setup_logging()
    logging.info("Application started.")

    try:
        app = QApplication(sys.argv)

        # Initialize core components
        background_task_manager = BackgroundTaskManager()
        logging.info(f"Multithreading with maximum {background_task_manager.thread_pool.maxThreadCount()} threads.")

        file_manager = FileManager()
        directory_synchronizer = DirectorySynchronizer()
        plugin_manager = PluginManager()
        settings_manager = SettingsManager()
        
        # We need to create a dummy parent for NotificationManager first,
        # because MainWindow needs it, but it needs MainWindow as a parent.
        # We'll assign the real parent after MainWindow is created.
        notification_manager = NotificationManager(None, settings_manager)
        
        file_association_manager = FileAssociationManager()

        # Connect shutdown signals
        app.aboutToQuit.connect(plugin_manager.shutdown)

        task_queue_manager = TaskQueueManager(
            file_manager=file_manager,
            directory_synchronizer=directory_synchronizer,
            plugin_manager=plugin_manager,
            background_task_manager=background_task_manager
        )

        window = MainWindow(
            background_task_manager=background_task_manager,
            task_queue_manager=task_queue_manager,
            file_manager=file_manager,
            directory_synchronizer=directory_synchronizer,
            notification_manager=notification_manager,
            file_association_manager=file_association_manager
        )
        
        # Now set the real parent for the notification manager
        notification_manager.parent_window = window

        window.show()
        window.raise_()
        window.activateWindow()
        
        # Apply theme after the window is shown and the event loop is running
        theme_name = window.settings_manager.get_setting("theme", "dark")
        window.theme_manager.apply_theme(theme_name)

        sys.exit(app.exec())

    except Exception as e:
        logging.critical("Unhandled exception:", exc_info=True)
        # Optionally, show a critical error dialog to the user
        # from PyQt6.QtWidgets import QMessageBox
        # QMessageBox.critical(None, "Critical Error", f"An unhandled exception occurred: {e}\n\nPlease check the logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
