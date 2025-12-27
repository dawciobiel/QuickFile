from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from app.translation_manager import translation_manager

class ModifyLinkDialog(QDialog):
    def __init__(self, parent=None, link_path=None, target_path=None):
        super().__init__(parent)
        uic.loadUi("ui/modify_link_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("ModifyLinkDialog", "Modify Symbolic Link"))
        self.retranslate_ui()

        if link_path:
            self.link_path_edit.setText(link_path)
        if target_path:
            self.current_target_edit.setText(target_path)

        self.browse_button.clicked.connect(self.browse_target)

    def retranslate_ui(self):
        self.link_path_label.setText(translation_manager.translate("ModifyLinkDialog", "Link Path:"))
        self.current_target_label.setText(translation_manager.translate("ModifyLinkDialog", "Current Target:"))
        self.new_target_label.setText(translation_manager.translate("ModifyLinkDialog", "New Target:"))
        self.browse_button.setText(translation_manager.translate("ModifyLinkDialog", "Browse..."))

        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText(translation_manager.translate("Buttons", "OK"))
        cancel_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText(translation_manager.translate("Buttons", "Cancel"))

    def browse_target(self):
        dialog = QFileDialog(self, translation_manager.translate("ModifyLinkDialog", "Select New Target"))
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        if dialog.exec():
            path = dialog.selectedFiles()[0]
            self.new_target_edit.setText(path)

    def get_new_target(self):
        return self.new_target_edit.text()
