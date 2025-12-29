import os
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog
from app.translation_manager import translation_manager
from app.task_queue_manager import Task, TaskType, TaskStatus

class MoveDialog(QDialog):
    def __init__(self, parent, source_paths, destination_path, task_queue_manager, background_task_manager):
        super().__init__(parent)
        uic.loadUi("ui/file_operation_dialog.ui", self)
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
        self._connect_signals()
        self.retranslate_ui()

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

        self.adjustSize()

    def _connect_signals(self):
        self.start_button.clicked.connect(self.start_operation)
        self.queue_button.clicked.connect(self.queue_operation)
        self.cancel_button.clicked.connect(self.cancel_operation)

    def retranslate_ui(self):
        self.source_label_title.setText(translation_manager.translate("MoveDialog", "Source:"))
        self.destination_label_title.setText(translation_manager.translate("MoveDialog", "Destination:"))
        self.overwrite_checkbox.setText(translation_manager.translate("MoveDialog", "Overwrite existing files"))
        
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

        self.task = Task(TaskType.MOVE, self.source_paths, self.destination_path, self.get_options())
        
        self.task_queue_manager.add_task(self.task)
        
        self.task.progress_changed.connect(self.progressBar.setValue)
        self.task.status_changed.connect(self.on_task_status_changed)

    def queue_operation(self):
        self.accept()

    def cancel_operation(self):
        hide_text = translation_manager.translate("Buttons", "Hide")
        
        if self.cancel_button.text() == hide_text:
            self.accept()  # Just close the dialog, don't interrupt the task
            return

        if self.task:
            self.task_queue_manager.cancel_task(self.task.id)
        
        self.reject()

    def on_task_status_changed(self, status):
        if status in [TaskStatus.FINISHED, TaskStatus.CANCELLED, TaskStatus.ERROR]:
            self.accept()
