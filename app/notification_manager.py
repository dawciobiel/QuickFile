# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.notification_popup import NotificationPopup
from utils.resource_path import get_resource_path

class NotificationManager(QObject):
    def __init__(self, parent_window, settings_manager):
        super().__init__()
        self.parent_window = parent_window
        self.settings_manager = settings_manager
        self.notifications = []
        self.padding = 10

        icon_base_path = os.path.join("resources", "icons", "fonts.google.com")
        self.icon_success = get_resource_path(os.path.join(icon_base_path, "library_add_check.svg"))
        self.icon_error = get_resource_path(os.path.join(icon_base_path, "close_tab.svg"))
        self.icon_info = get_resource_path(os.path.join(icon_base_path, "share.svg"))

        sound_base_path = os.path.join("resources", "sounds")
        self.sound_success = self._create_sound_effect(os.path.join(sound_base_path, "success.wav"))
        self.sound_error = self._create_sound_effect(os.path.join(sound_base_path, "error.wav"))
        self.sound_info = self._create_sound_effect(os.path.join(sound_base_path, "info.wav"))

    def _create_sound_effect(self, path):
        sound_effect = QSoundEffect()
        sound_effect.setSource(QUrl.fromLocalFile(get_resource_path(path)))
        return sound_effect

    def show_notification(self, message, icon_path, sound_effect):
        if self.settings_manager.get_setting("sound_notifications_enabled", True):
            sound_effect.play()

        popup = NotificationPopup(message, icon_path, self.parent_window)
        popup.finished.connect(lambda p=popup: self._remove_notification(p))
        
        self.notifications.append(popup)
        self._reposition_notifications()
        
        popup.show_and_fade()

    def show_success(self, message):
        self.show_notification(message, self.icon_success, self.sound_success)

    def show_error(self, message):
        self.show_notification(message, self.icon_error, self.sound_error)

    def show_info(self, message):
        self.show_notification(message, self.icon_info, self.sound_info)

    def show_blocking_error(self, title, message):
        if self.settings_manager.get_setting("sound_notifications_enabled", True):
            self.sound_error.play()
        QMessageBox.critical(self.parent_window, title, message)

    def _remove_notification(self, popup):
        try:
            self.notifications.remove(popup)
        except ValueError:
            pass
        popup.deleteLater()
        self._reposition_notifications()

    def _reposition_notifications(self):
        parent_rect = self.parent_window.geometry()
        screen_rect = QApplication.primaryScreen().availableGeometry()

        base_x = min(parent_rect.right(), screen_rect.right()) - self.padding
        base_y = min(parent_rect.bottom(), screen_rect.bottom()) - self.padding

        y_pos = base_y
        for popup in reversed(self.notifications):
            popup_width = popup.sizeHint().width()
            popup_height = popup.sizeHint().height()
            
            x = base_x - popup_width
            y = y_pos - popup_height
            
            popup.move(x, y)
            
            y_pos -= (popup_height + self.padding)
