# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QMessageBox

def show_error_message(notification_manager, title, message):
    """
    Displays a critical error message box using the NotificationManager.
    """
    notification_manager.show_blocking_error(title, message)

def show_info_message(parent, title, message):
    """
    Displays an informational message box.
    """
    QMessageBox.information(parent, title, message)
