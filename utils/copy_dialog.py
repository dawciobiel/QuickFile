from PyQt6 import uic
from PyQt6.QtWidgets import QDialog

from app.action_logger import action_logger
from app.task_queue_manager import Task, TaskType, TaskStatus
from app.translation_manager import translation_manager
from ui.dual_progress_bar import DualProgressBar
from utils.resource_path import get_resource_path


class CopyDialog(QDialog):
    def __init__(self, parent, source_paths, destination_path, task_queue_manager, background_task_manager):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/file_operation_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("CopyDialog", "Copy"))
        
        self.task_queue_manager = task_queue_manager
        self.background_task_manager = background_task_manager
        self.task = None
        
        self.setMinimumWidth(600)
        
        if isinstance(source_paths, str):
            self.source_paths = [source_paths]
        else:
            self.source_paths = source_paths
            
        self.destination_path = destination_path
        
        self._replace_progress_bar()
        self._init_ui()
        self._connect_signals()
        self.retranslate_ui()

    def _replace_progress_bar(self):
        # Replace the standard QProgressBar from UI with DualProgressBar
        layout = self.progress_page.layout()
        index = layout.indexOf(self.progressBar)
        layout.removeWidget(self.progressBar)
        self.progressBar.deleteLater()
        
        self.progressBar = DualProgressBar()
        layout.insertWidget(index, self.progressBar)

    def _init_ui(self):
        self.stackedWidget.setCurrentWidget(self.options_page)
        
        if len(self.source_paths) == 1:
            self.source_path_label.setText(self.source_paths[0])
        else:
            self.source_path_label.setText(translation_manager.translate("CopyDialog", "{count} items selected").format(count=len(self.source_paths)))
            
        self.destination_path_label.setText(self.destination_path)

        self.source_path_label.setWordWrap(True)
        self.destination_path_label.setWordWrap(True)

        self.preserve_timestamp_checkbox.setChecked(True)
        self.preserve_timestamp_checkbox.setVisible(True)
        
        self.adjustSize()

    def _connect_signals(self):
        self.start_button.clicked.connect(self.start_operation)
        self.queue_button.clicked.connect(self.queue_operation)
        self.cancel_button.clicked.connect(self.cancel_operation)

    def retranslate_ui(self):
        self.source_label_title.setText(translation_manager.translate("CopyDialog", "Source:"))
        self.destination_label_title.setText(translation_manager.translate("CopyDialog", "Destination:"))
        self.overwrite_checkbox.setText(translation_manager.translate("CopyDialog", "Overwrite existing files"))
        self.preserve_timestamp_checkbox.setText(translation_manager.translate("CopyDialog", "Preserve original modification date"))
        
        self.start_button.setText(translation_manager.translate("Buttons", "Start"))
        self.queue_button.setText(translation_manager.translate("Buttons", "Queue"))
        self.cancel_button.setText(translation_manager.translate("Buttons", "Cancel"))

    def get_options(self):
        return {
            "overwrite": self.overwrite_checkbox.isChecked(),
            "preserve_timestamp": self.preserve_timestamp_checkbox.isChecked(),
        }

    def start_operation(self):
        self.stackedWidget.setCurrentWidget(self.progress_page)
        self.start_button.setVisible(False)
        self.queue_button.setVisible(False)
        self.cancel_button.setText(translation_manager.translate("Buttons", "Hide"))

        options = self.get_options()
        action_logger.log_action("copy", sources=self.source_paths, destination=self.destination_path, options=options)
        
        self.task = Task(TaskType.COPY, self.source_paths, self.destination_path, options)
        self.task_queue_manager.add_task(self.task)

        self.task.progress_changed.connect(self.update_progress)
        self.task.status_changed.connect(self.on_task_status_changed)

    def update_progress(self, value):
        if isinstance(value, tuple):
            read_val, write_val = value
            self.progressBar.setReadValue(read_val)
            self.progressBar.setValue(write_val)
        else:
            self.progressBar.setValue(value)

    def queue_operation(self):
        options = self.get_options()
        action_logger.log_action("copy", sources=self.source_paths, destination=self.destination_path, options=options)
        self.task = Task(TaskType.COPY, self.source_paths, self.destination_path, options)
        self.task_queue_manager.add_task(self.task)
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
