# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QFileDialog, QLabel, QPushButton, QLineEdit, QRadioButton, QComboBox, QSpinBox, \
    QCheckBox


class SplitDialog(QDialog):
    # --- Declare UI attributes for linter ---
    sourceFileLabel: QLabel
    browseButton: QPushButton
    destinationEdit: QLineEdit
    predefinedRadio: QRadioButton
    predefinedCombo: QComboBox
    customRadio: QRadioButton
    customSizeSpinBox: QSpinBox
    unitCombo: QComboBox
    checksumCheckBox: QCheckBox

    # -----------------------------------------

    def __init__(self, parent=None, source_file=None):
        super().__init__(parent)
        # This path needs to be adjusted to where the .ui file is moved
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "split_dialog.ui")
        try:
            uic.loadUi(ui_path, self)
        except Exception as e:
            logging.error(f"Failed to load UI for SplitDialog: {e}")
            raise

        self.source_file = source_file
        self.sourceFileLabel.setText(os.path.basename(source_file) if source_file else "None")

        self.browseButton.clicked.connect(self.browse_destination)

        if source_file:
            self.destinationEdit.setText(os.path.dirname(source_file))

    def browse_destination(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Destination Directory", self.destinationEdit.text())
        if dir_path:
            self.destinationEdit.setText(dir_path)

    def get_data(self):
        chunk_size = 0
        if self.predefinedRadio.isChecked():
            chunk_size = self.predefinedCombo.currentData()
        else:
            val = self.customSizeSpinBox.value()
            unit = self.unitCombo.currentText()
            multipliers = {"B": 1, "KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}
            chunk_size = val * multipliers.get(unit, 1)

        return {
            "destination_path": self.destinationEdit.text(),
            "chunk_size": chunk_size,
            "generate_checksum": self.checksumCheckBox.isChecked()
        }


class JoinDialog(QDialog):
    # --- Declare UI attributes for linter ---
    sourceFileLabel: QLabel
    browseButton: QPushButton
    destinationEdit: QLineEdit
    outputFilenameEdit: QLineEdit

    # -----------------------------------------

    def __init__(self, parent=None, source_file=None):
        super().__init__(parent)
        # This path needs to be adjusted
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "join_dialog.ui")
        try:
            uic.loadUi(ui_path, self)
        except Exception as e:
            logging.error(f"Failed to load UI for JoinDialog: {e}")
            raise

        self.source_file = source_file
        self.sourceFileLabel.setText(os.path.basename(source_file) if source_file else "None")

        self.browseButton.clicked.connect(self.browse_destination)

        if source_file:
            self.destinationEdit.setText(os.path.dirname(source_file))

            base_name = os.path.basename(source_file)
            suggested_name = None

            crc_file_to_read = None

            if base_name.endswith(".crc32"):
                crc_file_to_read = source_file
            elif base_name.endswith(".001"):
                potential_crc = source_file[:-4] + ".crc32"
                # noinspection PyTypeChecker
                if os.path.exists(potential_crc):
                    crc_file_to_read = potential_crc

            if crc_file_to_read:
                try:
                    with open(crc_file_to_read, 'r', encoding='utf-8-sig') as f:
                        for line in f:
                            line = line.rstrip('\n')
                            if line.startswith("filenameutf8="):
                                suggested_name = line.split("=", 1)[1]
                            elif line.startswith("filename=") and suggested_name is None:
                                suggested_name = line.split("=", 1)[1]
                except Exception as e:
                    logging.warning(f"Failed to read .crc32 file for filename suggestion: {e}")

            if suggested_name:
                self.outputFilenameEdit.setText(suggested_name)
            elif base_name.endswith(".crc32"):
                self.outputFilenameEdit.setText(base_name[:-6])
            elif base_name.endswith(".001"):
                self.outputFilenameEdit.setText(base_name[:-4])
            else:
                self.outputFilenameEdit.setText(base_name + ".joined")

    def browse_destination(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Destination Directory", self.destinationEdit.text())
        if dir_path:
            self.destinationEdit.setText(dir_path)

    def get_data(self):
        return {
            "destination_path": self.destinationEdit.text(),
            "output_filename": self.outputFilenameEdit.text()
        }
