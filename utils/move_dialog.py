import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QPushButton
from app.translation_manager import translation_manager
from app.background_task_manager import BackgroundTaskManager
from file_operations.file_manager import OperationCancelledError

class MoveDialog(QDialog):
    def __init__(self, parent, source_paths, destination_path, file_manager, background_task_manager: BackgroundTaskManager):
        super().__init__(parent)
        uic.loadUi("ui/file_operation_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("MoveDialog", "Move"))

        # Ensure source_paths is a list
        if isinstance(source_paths, str):
            self.source_paths = [source_paths]
        else:
            self.source_paths = source_paths

        self.destination_path = destination_path
        self.file_manager = file_manager
        self.background_task_manager = background_task_manager
        self.is_paused = False

        self._init_options_ui()

    def _init_options_ui(self):
        self.stackedWidget.setCurrentWidget(self.options_page)
        
        if len(self.source_paths) == 1:
            self.source_path_label.setText(self.source_paths[0])
        else:
            self.source_path_label.setText(translation_manager.translate("MoveDialog", f"{len(self.source_paths)} items selected"))
            
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
        
        # We need a batch move method in FileManager, similar to copy_items_batch
        # For now, we can iterate or add move_items_batch to FileManager.
        # Let's check if FileManager has move_items_batch. It doesn't seem so from previous reads.
        # But we can use a lambda or add it. Adding it to FileManager is cleaner.
        
        # Since I cannot edit FileManager in this turn (I am editing MoveDialog), 
        # I will assume I will add move_items_batch to FileManager in the next step.
        # Or I can implement a simple loop here if I wrap it in a function.
        # But BackgroundTaskManager expects a function.
        
        if len(self.source_paths) == 1:
            signals = self.background_task_manager.run_task(
                self.file_manager.move_item_with_options,
                self.source_paths[0],
                self.destination_path,
                options
            )
        else:
             signals = self.background_task_manager.run_task(
                self.file_manager.move_items_batch, # I will add this method next
                self.source_paths,
                self.destination_path,
                options
            )
        
        signals.progress.connect(self.update_progress)
        signals.finished.connect(self.on_finished)
        signals.error.connect(self.on_error)

    def _init_progress_ui(self):
        self.stackedWidget.setCurrentWidget(self.progress_page)
        if len(self.source_paths) == 1:
            self.progress_label.setText(f"Moving {os.path.basename(self.source_paths[0])}...")
        else:
            self.progress_label.setText(translation_manager.translate("MoveDialog", "Moving selected items..."))

        self.buttonBox.clear()
        
        # Add Pause button
        self.pause_button = QPushButton(translation_manager.translate("Buttons", "Pause"))
        self.pause_button.clicked.connect(self.toggle_pause)
        self.buttonBox.addButton(self.pause_button, QDialogButtonBox.ButtonRole.ActionRole)

        self.cancel_button = self.buttonBox.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.clicked.connect(self.background_task_manager.cancel_current_task)

    def toggle_pause(self):
        if self.is_paused:
            self.background_task_manager.resume_current_task()
            self.pause_button.setText(translation_manager.translate("Buttons", "Pause"))
            self.is_paused = False
        else:
            self.background_task_manager.pause_current_task()
            self.pause_button.setText(translation_manager.translate("Buttons", "Resume"))
            self.is_paused = True

    def update_progress(self, value):
        self.progressBar.setValue(value)

    def on_finished(self):
        self.accept()

    def on_error(self, error_tuple):
        from utils.dialogs import show_error_message
        exctype, value, traceback_str = error_tuple
        
        if issubclass(exctype, OperationCancelledError):
            self.reject()
        else:
            show_error_message(self, "Move Error", str(value))
            self.reject()
