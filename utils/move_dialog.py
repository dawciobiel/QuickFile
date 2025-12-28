import os
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class MoveDialog(QDialog):
    def __init__(self, parent, source_paths, destination_path):
        super().__init__(parent)
        uic.loadUi("ui/file_operation_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("MoveDialog", "Move"))

        self.setMinimumWidth(600)

        if isinstance(source_paths, str):
            self.source_paths = [source_paths]
        else:
            self.source_paths = source_paths

        self.destination_path = destination_path

        self._init_options_ui()
        self.retranslate_ui()

    def _init_options_ui(self):
        self.stackedWidget.setCurrentWidget(self.options_page)
        
        if len(self.source_paths) == 1:
            self.source_path_label.setText(self.source_paths[0])
        else:
            self.source_path_label.setText(translation_manager.translate("MoveDialog", "{count} items selected").format(count=len(self.source_paths)))
            
        self.destination_path_label.setText(self.destination_path)

        self.source_path_label.setWordWrap(True)
        self.destination_path_label.setWordWrap(True)

        self.preserve_timestamp_checkbox.setVisible(False)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.adjustSize()

    def retranslate_ui(self):
        self.source_label_title.setText(translation_manager.translate("MoveDialog", "Source:"))
        self.destination_label_title.setText(translation_manager.translate("MoveDialog", "Destination:"))
        self.overwrite_checkbox.setText(translation_manager.translate("MoveDialog", "Overwrite existing files"))
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))

    def get_options(self):
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
        }
