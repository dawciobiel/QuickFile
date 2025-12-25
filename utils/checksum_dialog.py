from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox, QTextEdit, QGroupBox, QCheckBox
from PyQt6.QtCore import Qt
from app.translation_manager import translation_manager

class ChecksumDialog(QDialog):
    def __init__(self, parent, file_paths, available_algorithms):
        super().__init__(parent)
        self.setWindowTitle(translation_manager.translate("ChecksumDialog", "Calculate Checksum"))
        self.resize(400, 300)
        
        self.file_paths = file_paths
        self.available_algorithms = available_algorithms
        
        self.layout = QVBoxLayout(self)
        
        # Files list
        self.files_group = QGroupBox(translation_manager.translate("ChecksumDialog", "Selected Files"))
        self.files_layout = QVBoxLayout(self.files_group)
        self.files_list = QTextEdit()
        self.files_list.setReadOnly(True)
        self.files_list.setPlainText("\n".join(self.file_paths))
        self.files_layout.addWidget(self.files_list)
        self.layout.addWidget(self.files_group)
        
        # Algorithm selection
        self.algo_group = QGroupBox(translation_manager.translate("ChecksumDialog", "Algorithm"))
        self.algo_layout = QVBoxLayout(self.algo_group)
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(self.available_algorithms)
        self.algo_layout.addWidget(self.algo_combo)
        self.layout.addWidget(self.algo_group)
        
        # Output options
        self.output_group = QGroupBox(translation_manager.translate("ChecksumDialog", "Output Options"))
        self.output_layout = QVBoxLayout(self.output_group)
        self.show_in_dialog_checkbox = QCheckBox(translation_manager.translate("ChecksumDialog", "Show result in a dialog"))
        self.show_in_dialog_checkbox.setChecked(True)
        self.save_to_file_checkbox = QCheckBox(translation_manager.translate("ChecksumDialog", "Save result to .checksum file"))
        self.output_layout.addWidget(self.show_in_dialog_checkbox)
        self.output_layout.addWidget(self.save_to_file_checkbox)
        self.layout.addWidget(self.output_group)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_options(self):
        return {
            "algorithm": self.algo_combo.currentText(),
            "show_in_dialog": self.show_in_dialog_checkbox.isChecked(),
            "save_to_file": self.save_to_file_checkbox.isChecked()
        }
