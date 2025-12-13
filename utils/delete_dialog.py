from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QTextEdit
from app.translation_manager import translation_manager

class DeleteDialog(QDialog):
    def __init__(self, parent, item_paths):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("DeleteDialog", "Delete"))

        self.layout = QVBoxLayout(self)

        if len(item_paths) == 1:
            # Single item view
            self.layout.addWidget(QLabel(translation_manager.translate("DeleteDialog", "Are you sure you want to delete:") + f" <b>{item_paths[0]}</b>?"))
        else:
            # Multiple items view
            self.layout.addWidget(QLabel(translation_manager.translate("DeleteDialog", f"Are you sure you want to delete <b>{len(item_paths)}</b> items?")))
            
            # Add a scrollable text area with the list of files
            files_to_delete_text = QTextEdit()
            files_to_delete_text.setPlainText("\n".join(item_paths))
            files_to_delete_text.setReadOnly(True)
            self.layout.addWidget(files_to_delete_text)

        self.layout.addWidget(QLabel(translation_manager.translate("DeleteDialog", "This operation cannot be undone.")))

        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "OK"))
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(translation_manager.translate("Buttons", "Cancel"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
