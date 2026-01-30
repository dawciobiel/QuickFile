# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import uuid
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal, Qt

from app.enums import TaskStatus, TaskType
from app.plugin_sandbox import SandboxedPluginWrapper


class Task(QObject):
    status_changed = pyqtSignal(TaskStatus)
    progress_changed = pyqtSignal(object)
    overall_progress_changed = pyqtSignal(int)
    details_changed = pyqtSignal(str)
    speed_changed = pyqtSignal(float)
    directory_changed = pyqtSignal(str)  # Restored signal
    finished = pyqtSignal()

    def __init__(self, task_type: TaskType, source_paths, destination_path=None, options=None):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options or {}
        self.result = None
        self.context = None
        self._status = TaskStatus.PENDING
        self._progress = 0
        self._overall_progress = 0
        self._details = ""
        self._speed = 0.0

    @property
    def status(self):
        return self._status

    def set_status(self, status):
        if self._status != status:
            self._status = status
            if status == TaskStatus.FINISHED:
                self.set_progress(100)
            self.status_changed.emit(status)

    @property
    def progress(self):
        return self._progress

    def set_progress(self, progress):
        if isinstance(progress, tuple) and len(progress) == 3:
            self._progress = (progress[0], progress[1])
            self.set_speed(progress[2])
            self.progress_changed.emit(self._progress)
        else:
            self._progress = progress
            self.progress_changed.emit(progress)

    @property
    def overall_progress(self):
        return self._overall_progress

    def set_overall_progress(self, progress):
        self._overall_progress = progress
        self.overall_progress_changed.emit(progress)

    @property
    def details(self):
        return self._details

    def set_details(self, details):
        if self._details != details:
            self._details = details
            self.details_changed.emit(details)

    @property
    def speed(self):
        return self._speed

    def set_speed(self, speed):
        self._speed = speed
        self.speed_changed.emit(speed)


class TaskQueueManager(QObject):
    task_added = pyqtSignal(Task)
    task_completed = pyqtSignal(Task)
    task_finished = pyqtSignal(Task)
    queue_cleared = pyqtSignal()

    def __init__(self, file_manager, directory_synchronizer, plugin_manager, background_task_manager):
        super().__init__()
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.plugin_manager = plugin_manager
        self.background_task_manager = background_task_manager
        self.active_tasks = {}
        self.all_tasks = []

        # Connect to signals from BackgroundTaskManager
        self.background_task_manager.task_progress_updated.connect(self._on_task_progress)
        self.background_task_manager.task_succeeded.connect(self._on_task_succeeded)
        self.background_task_manager.task_failed.connect(self._on_task_failed)
        self.background_task_manager.task_finished.connect(self._on_task_finished_cleanup)

    def add_task(self, task: Task):
        self.all_tasks.append(task)
        self.task_added.emit(task)
        self.active_tasks[task.id] = task
        self.process_task(task)

    def process_task(self, task: Task):
        task.set_status(TaskStatus.IN_PROGRESS)

        if task.type == TaskType.SYNC:
            self.background_task_manager.run_task(
                task,
                target=self.directory_synchronizer.synchronize,
                dir1=task.source_paths[0],
                dir2=task.destination_path,
                options=task.options
            )
            return

        plugin_id = task.options.get("plugin_id")
        if not plugin_id:
            task.set_status(TaskStatus.ERROR)
            task.set_details(f"Task type '{task.type.name}' requires a 'plugin_id' in options.")
            logging.error(f"Task {task.id} failed: Missing plugin_id.")
            self._on_task_finished_cleanup(task.id)
            return

        plugin = self.plugin_manager.get_plugin_by_id(plugin_id)
        if not plugin:
            task.set_status(TaskStatus.ERROR)
            task.set_details(f"Plugin '{plugin_id}' not found.")
            logging.error(f"Task {task.id} failed: Plugin not found.")
            self._on_task_finished_cleanup(task.id)
            return

        # Connect signals if this is the first time we see this wrapper
        if plugin not in self.background_task_manager.plugin_wrappers:
            plugin.progress_updated.connect(self.background_task_manager._on_plugin_progress, Qt.ConnectionType.QueuedConnection)
            plugin.method_finished.connect(self.background_task_manager._on_plugin_success, Qt.ConnectionType.QueuedConnection)
            plugin.method_failed.connect(self.background_task_manager._on_plugin_failure, Qt.ConnectionType.QueuedConnection)
            self.background_task_manager.plugin_wrappers[plugin] = True
            logging.debug(f"Connected signals for plugin wrapper: {plugin.metadata['id']}")

        # Register the task with BackgroundTaskManager to track its context
        self.background_task_manager.register_plugin_task(task, plugin)

        # Prepare serializable kwargs for the plugin
        plugin_kwargs = {"options": task.options}
        if task.source_paths:
            if len(task.source_paths) == 1:
                plugin_kwargs["source_path"] = task.source_paths[0]
            else:
                plugin_kwargs["source_paths"] = task.source_paths
        if task.destination_path:
            plugin_kwargs["destination_path"] = task.destination_path
        
        # Specific keys for certain tasks
        if task.type == TaskType.DELETE:
            plugin_kwargs["item_paths"] = task.source_paths
        elif task.type == TaskType.SEARCH:
            plugin_kwargs["start_path"] = task.source_paths[0]
        elif task.type == TaskType.CHECKSUM:
            plugin_kwargs["file_path"] = task.source_paths[0]
            plugin_kwargs["algorithms"] = task.options.get("algorithms", [])

        # Execute task using the new architecture
        plugin.execute_task(
            task_id=task.id,
            action_id=task.type.value,
            **plugin_kwargs
        )

    def _on_task_progress(self, task_id, percentage):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.set_progress(percentage)

    def _on_task_succeeded(self, task_id, result):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.result = result
            task.set_status(TaskStatus.FINISHED)
            self.task_completed.emit(task)
            if task.destination_path:
                task.directory_changed.emit(task.destination_path)

    def _on_task_failed(self, task_id, error_message):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if task.context and task.context.is_cancelled:
                task.set_status(TaskStatus.CANCELLED)
                task.set_details("Operation cancelled by user.")
            else:
                task.set_status(TaskStatus.ERROR)
                task.set_details(error_message)

    def _on_task_finished_cleanup(self, task_id):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.finished.emit()
            self.task_finished.emit(task)
            del self.active_tasks[task_id]

    def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            self.background_task_manager.cancel_task(task_id)

    def pause_task(self, task_id):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            self.background_task_manager.pause_task(task_id)
            task.set_status(TaskStatus.PAUSED)

    def resume_task(self, task_id):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            self.background_task_manager.resume_task(task_id)
            task.set_status(TaskStatus.IN_PROGRESS)

    def clear_completed_tasks(self):
        self.all_tasks = [task for task in self.all_tasks if task.status != TaskStatus.FINISHED]
        self.queue_cleared.emit()

    def clear_error_tasks(self):
        self.all_tasks = [task for task in self.all_tasks if task.status != TaskStatus.ERROR]
        self.queue_cleared.emit()

    def clear_all_tasks(self):
        self.all_tasks = [task for task in self.all_tasks if task.status not in [TaskStatus.FINISHED, TaskStatus.ERROR, TaskStatus.CANCELLED]]
        self.queue_cleared.emit()
