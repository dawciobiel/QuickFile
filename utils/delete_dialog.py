from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager
from app.background_task_manager import BackgroundTaskManager
from file_operations.file_manager import OperationCancelledError
import os

class DeleteDialog(QDialog):
    def __init__(self, parent, item_paths, file_manager, background_task_manager: BackgroundTaskManager):
        super().__init__(parent)
        uic.loadUi("ui/delete_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("DeleteDialog", "Delete"))
        
        self.item_paths = item_paths
        self.file_manager = file_manager
        self.background_task_manager = background_task_manager

        self._init_options_ui()

    def _init_options_ui(self):
        if len(self.item_paths) == 1:
            self.confirmation_label.setText(translation_manager.translate("DeleteDialog", "Are you sure you want to delete:") + f" <b>{self.item_paths[0]}</b>?")
            self.files_list_text.setVisible(False)
        else:
            self.confirmation_label.setText(translation_manager.translate("DeleteDialog", f"Are you sure you want to delete <b>{len(self.item_paths)}</b> items?"))
            self.files_list_text.setPlainText("\n".join(self.item_paths))
            self.files_list_text.setVisible(True)

        self.move_to_trash_checkbox.setText(translation_manager.translate("DeleteDialog", "Move to Trash (if available)"))
        self.warning_label.setText(translation_manager.translate("DeleteDialog", "This operation cannot be undone if not moved to Trash."))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))
        
        self.buttonBox.accepted.connect(self.start_delete)
        self.buttonBox.rejected.connect(self.reject)

    def start_delete(self):
        # For now, we don't have a progress UI for delete, so we just run it.
        # We can add it later if needed.
        move_to_trash = self.should_move_to_trash()
        
        signals = self.background_task_manager.run_task(
            self.file_manager.delete_items_batch,
            self.item_paths,
            move_to_trash
        )
        
        # Since delete is fast, we might not need a progress bar,
        # but we'll accept the dialog once finished.
        signals.finished.connect(self.accept)
        signals.error.connect(self.on_error)

    def should_move_to_trash(self):
        return self.move_to_trash_checkbox.isChecked()

    def on_error(self, error_tuple):
        from utils.dialogs import show_error_message
        exctype, value, traceback_str = error_tuple
        
        if issubclass(exctype, OperationCancelledError):
            self.reject()
        else:
            show_error_message(self, "Delete Error", str(value))
            self.reject()
