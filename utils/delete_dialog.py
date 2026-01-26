# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from app.action_logger import action_logger
from app.translation_manager import translation_manager
from app.task_queue_manager import Task, TaskType, TaskStatus
from panels.task_queue_panel import TaskActionsWidget
from utils.resource_path import get_resource_path

class DeleteDialog(QDialog):
    def __init__(self, parent, item_paths, task_queue_manager, background_task_manager, theme_manager):
        super().__init__(parent)
        uic.loadUi(get_resource_path("ui/delete_dialog.ui"), self)
        self.setWindowTitle(translation_manager.translate("DeleteDialog", "Delete"))
        
        self.task_queue_manager = task_queue_manager
        self.background_task_manager = background_task_manager
        self.task = None
        self.theme_manager = theme_manager
        
        self.item_paths = item_paths
        self._init_ui()
        self._connect_signals()
        self.retranslate_ui()

    def _init_ui(self):
        self.stackedWidget.setCurrentWidget(self.options_page)

        if len(self.item_paths) == 1:
            full_path = self.item_paths[0]
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            
            if directory != os.path.sep:
                directory += os.path.sep

            question = translation_manager.translate("DeleteDialog", "Are you sure you want to delete:")
            rich_text = f"{question}<br><br>{directory}<b>{filename}</b>?"
            
            self.confirmation_label.setText(rich_text)
            self.files_list_text.setVisible(False)
        else:
            question = translation_manager.translate("DeleteDialog", "Are you sure you want to delete <b>{count}</b> items?").format(count=len(self.item_paths))
            self.confirmation_label.setText(question)
            self.files_list_text.setHtml("<br>".join(self.item_paths))
            self.files_list_text.setVisible(True)

    def _connect_signals(self):
        self.start_button.clicked.connect(self.start_operation)
        self.queue_button.clicked.connect(self.queue_operation)
        self.cancel_button.clicked.connect(self.cancel_operation)

    def retranslate_ui(self):
        self.move_to_trash_checkbox.setText(translation_manager.translate("DeleteDialog", "Move to Trash (if available)"))
        self.warning_label.setText(translation_manager.translate("DeleteDialog", "This operation cannot be undone if not moved to Trash."))
        
        self.start_button.setText(translation_manager.translate("Buttons", "Delete"))
        self.queue_button.setText(translation_manager.translate("Buttons", "Queue"))
        self.cancel_button.setText(translation_manager.translate("Buttons", "Cancel"))
        
        self.progress_label.setText(translation_manager.translate("DeleteDialog", "Deleting..."))

    def get_options(self):
        return {
            "move_to_trash": self.move_to_trash_checkbox.isChecked(),
            "plugin_id": "org.quickfile.standard_operations" # Added plugin_id
        }

    def start_operation(self):
        self.stackedWidget.setCurrentWidget(self.progress_page)
        self.start_button.setVisible(False)
        self.queue_button.setVisible(False)
        self.cancel_button.setText(translation_manager.translate("Buttons", "Hide"))

        options = self.get_options()
        action_logger.log_action("delete", paths=self.item_paths, options=options)

        self.task = Task(TaskType.DELETE, self.item_paths, options=options)
        self.task_queue_manager.add_task(self.task)
        
        self.task.progress_changed.connect(self.progressBar.setValue)
        self.task.status_changed.connect(self.on_task_status_changed)

        # Add action buttons (Pause, Cancel, More)
        self.actions_widget = TaskActionsWidget(self.task, self.task_queue_manager, self.theme_manager)
        self.progress_page.layout().addWidget(self.actions_widget)

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
