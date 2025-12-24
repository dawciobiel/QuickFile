import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager
from app.background_task_manager import BackgroundTaskManager

class MoveDialog(QDialog):
    def __init__(self, parent, source_path, destination_path, file_manager, background_task_manager: BackgroundTaskManager):
        super().__init__(parent)
        uic.loadUi("ui/file_operation_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("MoveDialog", "Move"))

        self.source_path = source_path
        self.destination_path = destination_path
        self.file_manager = file_manager
        self.background_task_manager = background_task_manager

        self._init_options_ui()

    def _init_options_ui(self):
        self.stackedWidget.setCurrentWidget(self.options_page)
        self.source_path_label.setText(self.source_path)
        self.destination_path_label.setText(self.destination_path)

        self.overwrite_checkbox.setText(translation_manager.translate("MoveDialog", "Overwrite existing files"))
        self.preserve_timestamp_checkbox.setVisible(False)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))
        
        self.buttonBox.accepted.connect(self.start_move)
        self.buttonBox.rejected.connect(self.reject)

    def start_move(self):
        self._init_progress_ui()
        
        options = {
            "overwrite": self.overwrite_checkbox.isChecked(),
        }
        
        signals = self.background_task_manager.run_task(
            self.file_manager.move_item_with_options,
            self.source_path,
            self.destination_path,
            options
        )
        
        signals.progress.connect(self.update_progress)
        signals.finished.connect(self.on_finished)
        signals.error.connect(self.on_error)

    def _init_progress_ui(self):
        self.stackedWidget.setCurrentWidget(self.progress_page)
        self.progress_label.setText(f"Moving {os.path.basename(self.source_path)}...")
        self.buttonBox.clear()
        self.cancel_button = self.buttonBox.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.clicked.connect(self.background_task_manager.cancel_current_task)

    def update_progress(self, value):
        self.progressBar.setValue(value)

    def on_finished(self):
        self.accept()

    def on_error(self, error_tuple):
        from utils.dialogs import show_error_message
        exctype, value, traceback_str = error_tuple
        show_error_message(self, "Move Error", str(value))
        self.reject()
