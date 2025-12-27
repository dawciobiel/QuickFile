import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class CreateLinkDialog(QDialog):
    def __init__(self, parent=None, source_path=None, link_dir=None):
        super().__init__(parent)
        uic.loadUi("ui/create_link_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("CreateLinkDialog", "Create Link"))
        self.retranslate_ui()

        if source_path:
            self.source_path_edit.setText(source_path)
            self.link_name_edit.setText(os.path.basename(source_path))
        if link_dir:
            self.destination_path_edit.setText(link_dir)

        self.browse_button.clicked.connect(self.browse_destination)
        
        self.hardlink_radio.toggled.connect(self.on_link_type_changed)
        
        if source_path and os.path.isdir(source_path):
            self.hardlink_radio.setEnabled(False)
            self.hardlink_radio.setToolTip(translation_manager.translate("CreateLinkDialog", "Hard links for directories are not supported."))

    def retranslate_ui(self):
        self.source_label.setText(translation_manager.translate("CreateLinkDialog", "Source:"))
        self.link_name_label.setText(translation_manager.translate("CreateLinkDialog", "Link Name:"))
        self.destination_label.setText(translation_manager.translate("CreateLinkDialog", "Destination:"))
        self.browse_button.setText(translation_manager.translate("CreateLinkDialog", "Browse..."))
        self.link_type_group.setTitle(translation_manager.translate("CreateLinkDialog", "Link Type"))
        self.symlink_radio.setText(translation_manager.translate("CreateLinkDialog", "Symbolic Link"))
        self.hardlink_radio.setText(translation_manager.translate("CreateLinkDialog", "Hard Link"))
        
        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText(translation_manager.translate("Buttons", "OK"))
        cancel_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText(translation_manager.translate("Buttons", "Cancel"))

    def on_link_type_changed(self, is_hardlink):
        pass

    def browse_destination(self):
        path = QFileDialog.getExistingDirectory(self, translation_manager.translate("CreateLinkDialog", "Select Link Location"))
        if path:
            self.destination_path_edit.setText(path)

    def get_link_details(self):
        source_path = self.source_path_edit.text()
        destination_dir = self.destination_path_edit.text()
        link_name = self.link_name_edit.text()
        
        if not all([source_path, destination_dir, link_name]):
            return None

        link_path = os.path.join(destination_dir, link_name)
        is_hardlink = self.hardlink_radio.isChecked()
        
        return source_path, link_path, is_hardlink
