import logging
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager # Import our new manager

# We need to import __version__ here as well to display it.
# Assuming __version__.py is accessible in the project root.
try:
    from __version__ import __version__
except ImportError:
    __version__ = "Unknown Version"
    logging.warning("Could not import __version__. Using 'Unknown Version'.")

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("AboutDialog", "About"))
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()

        # Application Name
        app_name_label = QLabel(translation_manager.translate("AboutDialog", "QuickFile"))
        app_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(app_name_label)

        # Version
        version_text = translation_manager.translate("AboutDialog", "Version: ") + __version__
        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(version_label)

        # Author
        author_label = QLabel(translation_manager.translate("AboutDialog", "Author: Dawid Bielecki"))
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(author_label)

        # URL
        url_label = QLabel("URL: <a href='https://github.com/dawciobiel/QuickFile'>https://github.com/dawciobiel/QuickFile</a>")
        url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        url_label.setOpenExternalLinks(True)
        url_label.setStyleSheet("font-size: 12px; color: blue;")
        layout.addWidget(url_label)

        # Description (placeholder)
        description_label = QLabel(translation_manager.translate("AboutDialog", "A powerful and efficient file manager with modern features."))
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(description_label)

        # OK Button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)
