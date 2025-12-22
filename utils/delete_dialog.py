from PyQt6 import uic
from PyQt6.QtWidgets import QDialog

from app.translation_manager import translation_manager


class DeleteDialog(QDialog):
    def __init__(self, parent, item_paths):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/delete_dialog.ui", self)
        
        self.setWindowTitle(translation_manager.translate("DeleteDialog", "Delete"))

        if len(item_paths) == 1:
            # Single item view
            self.confirmation_label.setText(
                translation_manager.translate("DeleteDialog", "Are you sure you want to delete:") + f" <b>{item_paths[0]}</b>?")
            self.files_list_text.hide()
            self.resize(400, 200)  # Adjust size for single item
        else:
            # Multiple items view
            self.confirmation_label.setText(
                translation_manager.translate("DeleteDialog", f"Are you sure you want to delete <b>{len(item_paths)}</b> items?"))
            self.files_list_text.setPlainText("\n".join(item_paths))
            self.files_list_text.show()

        # Translate other widgets
        self.move_to_trash_checkbox.setText(translation_manager.translate("DeleteDialog", "Move to Trash (if available)"))
        self.warning_label.setText(translation_manager.translate("DeleteDialog", "This operation cannot be undone if not moved to Trash."))

    def should_move_to_trash(self):
        """Returns True if the 'Move to Trash' checkbox is checked, False otherwise."""
        return self.move_to_trash_checkbox.isChecked()
