# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import logging
import zlib
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox, QApplication
from PyQt6 import uic
from plugins.base import MenuActionPlugin
from app.task_queue_manager import Task, TaskType
from app.translation_manager import translation_manager

class SplitDialog(QDialog):
    def __init__(self, parent=None, source_file=None):
        super().__init__(parent)
        # Load UI from the same directory as this script
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "split_dialog.ui")
        try:
            uic.loadUi(ui_path, self)
        except Exception as e:
            logging.error(f"Failed to load UI for SplitDialog: {e}")
            raise
        
        self.source_file = source_file
        self.sourceFileLabel.setText(os.path.basename(source_file) if source_file else "None")
        
        # Init UI state
        self.browseButton.clicked.connect(self.browse_destination)
        
        # Set default destination to source directory
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
            multipliers = {"B": 1, "KB": 1024, "MB": 1024*1024, "GB": 1024*1024*1024}
            chunk_size = val * multipliers.get(unit, 1)
            
        return {
            "destination_path": self.destinationEdit.text(),
            "chunk_size": chunk_size,
            "generate_checksum": self.checksumCheckBox.isChecked()
        }

class FileSplitterPlugin(MenuActionPlugin):
    @property
    def name(self):
        return "File Splitter"

    @property
    def description(self):
        return "Splits large files into smaller parts."

    def get_menu_actions(self):
        return [{
            "text": translation_manager.translate("FileSplitter", "Split File..."),
            "menu": "file",
            "callback": self.show_split_dialog
        }]

    def show_split_dialog(self):
        main_window = QApplication.activeWindow()
        if not main_window:
            logging.warning("FileSplitter: No active window found.")
            return

        selected_path = main_window.ui_state_provider.get_current_selected_path()
        if not selected_path or not os.path.isfile(selected_path):
            QMessageBox.warning(main_window, "Split File", "Please select a file to split.")
            return

        dialog = SplitDialog(main_window, selected_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            dest_path = data["destination_path"]
            chunk_size = data["chunk_size"]
            
            if chunk_size <= 0:
                 QMessageBox.warning(main_window, "Error", "Invalid chunk size.")
                 return

            options = {
                "chunk_size": chunk_size,
                "generate_checksum": data["generate_checksum"],
                "plugin": self
            }
            
            task = Task(TaskType.SPLIT_FILE, source_paths=[selected_path], destination_path=dest_path, options=options)
            main_window.task_queue_manager.add_task(task)
            main_window.statusBar().showMessage("Added split task to queue.")

    def split_file(self, source_path, dest_dir, options, progress_callback, task_context, task):
        chunk_size = options.get("chunk_size")
        generate_checksum = options.get("generate_checksum", False)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        file_size = os.path.getsize(source_path)
        base_name = os.path.basename(source_path)
        
        task.set_details(f"Splitting {base_name}...")
        
        bytes_read = 0
        part_num = 1
        crc32 = 0
        
        with open(source_path, 'rb') as f_in:
            while True:
                if task_context.is_cancelled: return
                task_context.wait_if_paused()
                
                part_ext = f".{part_num:03d}"
                part_path = os.path.join(dest_dir, base_name + part_ext)
                
                with open(part_path, 'wb') as f_out:
                    chunk_written = 0
                    while chunk_written < chunk_size:
                        if task_context.is_cancelled: return
                        task_context.wait_if_paused()
                        
                        read_size = min(64 * 1024, chunk_size - chunk_written)
                        data = f_in.read(read_size)
                        if not data: break
                        
                        f_out.write(data)
                        if generate_checksum: crc32 = zlib.crc32(data, crc32)
                        chunk_written += len(data)
                        bytes_read += len(data)
                        if file_size > 0: progress_callback.emit(int(bytes_read * 100 / file_size))
                    if chunk_written == 0: os.remove(part_path); break
                part_num += 1
                if bytes_read >= file_size: break
        if generate_checksum:
            crc32_hex = f"{crc32 & 0xFFFFFFFF:08X}"
            content = (
                f"filename={base_name}\n"
                f"filenameutf8={base_name}\n"
                f"size={file_size}\n"
                f"crc32={crc32_hex}\n"
            )
            with open(os.path.join(dest_dir, base_name + ".crc32"), 'w', encoding='utf-8') as f:
                f.write(content)