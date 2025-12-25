import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class DeleteDialog(QDialog):
    def __init__(self, parent, item_paths):
        super().__init__(parent)
        uic.loadUi("ui/delete_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("DeleteDialog", "Delete"))
        
        self.item_paths = item_paths
        self._init_options_ui()

    def _init_options_ui(self):
        if len(self.item_paths) == 1:
            full_path = self.item_paths[0]
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            
            if directory != os.path.sep:
                directory += os.sep

            question = translation_manager.translate("DeleteDialog", "Are you sure you want to delete:")
            rich_text = f"{question}<br><br>{directory}<b>{filename}</b>?"
            
            self.confirmation_label.setText(rich_text)
            self.files_list_text.setVisible(False)
        else:
            question = translation_manager.translate("DeleteDialog", "Are you sure you want to delete <b>{count}</b> items?").format(count=len(self.item_paths))
            self.confirmation_label.setText(question)
            # Use HTML to ensure newlines are rendered
            self.files_list_text.setHtml("<br>".join(self.item_paths))
            self.files_list_text.setVisible(True)

        self.move_to_trash_checkbox.setText(translation_manager.translate("DeleteDialog", "Move to Trash (if available)"))
        self.warning_label.setText(translation_manager.translate("DeleteDialog", "This operation cannot be undone if not moved to Trash."))

        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText(translation_manager.translate("Buttons", "OK"))
            
        cancel_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setText(translation_manager.translate("Buttons", "Cancel"))
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def get_options(self):
        return {
            "move_to_trash": self.move_to_trash_checkbox.isChecked()
        }
