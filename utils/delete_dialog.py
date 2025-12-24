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
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def get_options(self):
        return {
            "move_to_trash": self.move_to_trash_checkbox.isChecked()
        }
