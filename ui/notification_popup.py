# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtGui import QPixmap

class NotificationPopup(QWidget):
    finished = pyqtSignal()

    def __init__(self, message, icon_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)

        self.icon_label = QLabel()
        if icon_path:
            pixmap = QPixmap(icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
            self.layout.addWidget(self.icon_label)

        self.message_label = QLabel(message)
        self.layout.addWidget(self.message_label)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.show()

    def fade_in(self):
        self.animation.stop()
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def fade_out(self):
        self.animation.stop()
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        # Disconnect any previous connection to avoid multiple calls
        try:
            self.animation.finished.disconnect()
        except TypeError:
            pass # No connection existed
        self.animation.finished.connect(self._on_fade_out_finished)
        self.animation.start()

    def _on_fade_out_finished(self):
        self.close()
        self.finished.emit()

    def show_and_fade(self, duration=3000):
        self.fade_in()
        QTimer.singleShot(duration, self.fade_out)
