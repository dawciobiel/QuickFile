# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QHBoxLayout, QSizePolicy, QWidget

from app.action_logger import action_logger
from app.task_queue_manager import Task, TaskType, TaskStatus
from app.translation_manager import translation_manager
from ui.dual_progress_bar import DualProgressBar
from utils.resource_path import get_resource_path
from utils.formatters import format_speed


class MoveDialog(QDialog):
    def __init__(self, parent, source_paths, destination_path, task_queue_manager, background_task_manager):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/file_operation_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("MoveDialog", "Move"))

        self.task_queue_manager = task_queue_manager
        self.background_task_manager = background_task_manager
        self.task = None

        self.setMinimumWidth(600)

        if isinstance(source_paths, str):
            self.source_paths = [source_paths]
        else:
            self.source_paths = source_paths

        self.destination_path = destination_path

        self._init_ui()
        self._replace_progress_bar()
        self._connect_signals()
        self.retranslate_ui()

    def _replace_progress_bar(self):
        # Replace the standard QProgressBar from UI with DualProgressBar
        layout = self.progress_page.layout()
        index = layout.indexOf(self.progressBar)
        
        # Hide the original progress bar instead of removing it
        self.progressBar.setVisible(False)
        
        # Copy properties from the original progress bar
        min_size = self.progressBar.minimumSize()
        
        self.fileProgressBar = DualProgressBar()
        self.fileProgressBar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.fileProgressBar.setMinimumSize(min_size)
        
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0) # Removed right margin
        wrapper_layout.addWidget(self.fileProgressBar)
        
        layout.insertWidget(index, wrapper)
        
        # Insert speed label right after the file progress bar wrapper
        layout.insertWidget(index + 1, self.speed_label)

    def _init_ui(self):
        self.stackedWidget.setCurrentWidget(self.options_page)
        
        if len(self.source_paths) == 1:
            self.source_path_label.setText(self.source_paths[0])
        else:
            self.source_path_label.setText(translation_manager.translate("MoveDialog", "{count} items selected").format(count=len(self.source_paths)))
            
        self.destination_path_label.setText(self.destination_path)

        self.source_path_label.setWordWrap(True)
        self.destination_path_label.setWordWrap(True)

        self.preserve_timestamp_checkbox.setVisible(False)

        # Create speed label
        self.speed_label = QLabel("")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.adjustSize()

    def _connect_signals(self):
        self.start_button.clicked.connect(self.start_operation)
        self.queue_button.clicked.connect(self.queue_operation)
        self.cancel_button.clicked.connect(self.cancel_operation)

    def retranslate_ui(self):
        self.source_label_title.setText(translation_manager.translate("MoveDialog", "Source:"))
        self.destination_label_title.setText(translation_manager.translate("MoveDialog", "Destination:"))
        self.overwrite_checkbox.setText(translation_manager.translate("MoveDialog", "Overwrite existing files"))
        self.overall_progress_label.setText(translation_manager.translate("MoveDialog", "Overall Progress:"))
        
        self.start_button.setText(translation_manager.translate("Buttons", "Start"))
        self.queue_button.setText(translation_manager.translate("Buttons", "Queue"))
        self.cancel_button.setText(translation_manager.translate("Buttons", "Cancel"))

    def get_options(self):
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
        }

    def start_operation(self):
        self.stackedWidget.setCurrentWidget(self.progress_page)
        self.start_button.setVisible(False)
        self.queue_button.setVisible(False)
        self.cancel_button.setText(translation_manager.translate("Buttons", "Hide"))
        
        # Force layout update
        self.progress_page.layout().activate()
        self.adjustSize()

        options = self.get_options()
        action_logger.log_action("move", sources=self.source_paths, destination=self.destination_path, options=options)

        self.task = Task(TaskType.MOVE, self.source_paths, self.destination_path, options)
        self.task_queue_manager.add_task(self.task)

        self.task.progress_changed.connect(self.update_file_progress)
        self.task.overall_progress_changed.connect(self.overallProgressBar.setValue)
        self.task.status_changed.connect(self.on_task_status_changed)
        self.task.speed_changed.connect(self.update_speed)

    def update_file_progress(self, value):
        if isinstance(value, tuple):
            if len(value) >= 2:
                read_val, write_val = value[0], value[1]
                self.fileProgressBar.setReadValue(read_val)
                self.fileProgressBar.setValue(write_val)
        else:
            self.fileProgressBar.setValue(value)

    def update_speed(self, speed):
        self.speed_label.setText(format_speed(speed))

    def queue_operation(self):
        self.accept()

    def cancel_operation(self):
        hide_text = translation_manager.translate("Buttons", "Hide")
        
        if self.cancel_button.text() == hide_text:
            self.accept()
            return

        if self.task:
            self.task_queue_manager.cancel_task(self.task.id)
        
        self.reject()

    def on_task_status_changed(self, status):
        if status in [TaskStatus.FINISHED, TaskStatus.CANCELLED, TaskStatus.ERROR]:
            self.accept()
