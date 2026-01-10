# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import uuid
from enum import Enum, auto
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    PAUSED = auto()
    FINISHED = auto()
    CANCELLED = auto()
    ERROR = auto()

class TaskType(Enum):
    COPY = auto()
    MOVE = auto()
    DELETE = auto()
    SYNC = auto()
    SEARCH = auto()
    CHECKSUM = auto()
    CREATE_ARCHIVE = auto()
    EXTRACT_ARCHIVE = auto()
    CALCULATE_SIZE = auto()

class Task(QObject):
    status_changed = pyqtSignal(TaskStatus)
    progress_changed = pyqtSignal(object)  # Can be int or tuple
    overall_progress_changed = pyqtSignal(int)
    details_changed = pyqtSignal(str)
    directory_changed = pyqtSignal(str)
    speed_changed = pyqtSignal(float)
    finished = pyqtSignal()

    def __init__(self, task_type, source_paths, destination_path=None, options=None):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options or {}
        self.result = None
        self.context = None  # To hold the TaskContext from BackgroundTaskManager
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
        # If progress is a tuple (read, write, speed), extract speed
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

class WorkerSignaller(QObject):
    progress = pyqtSignal(object)
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)

class TaskWorker(QRunnable):
    def __init__(self, task, file_manager, directory_synchronizer, plugin_manager):
        super().__init__()
        self.task = task
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.plugin_manager = plugin_manager
        self.signals = WorkerSignaller()
        self.signals.progress.connect(self.task.set_progress)

    def run(self):
        try:
            self.task.set_status(TaskStatus.IN_PROGRESS)
            
            # The task context is now set by BackgroundTaskManager on the task object
            task_context = self.task.context
            
            if self.task.type in [TaskType.COPY, TaskType.MOVE, TaskType.DELETE]:
                plugin = self.plugin_manager.get_standard_operations_plugin()
                if not plugin:
                    raise RuntimeError("No standard operations plugin found.")
                
                if self.task.type == TaskType.COPY:
                    plugin.copy_items(self.task.source_paths, self.task.destination_path, self.task.options, progress_callback=self.signals.progress, task_context=task_context, task=self.task)
                elif self.task.type == TaskType.MOVE:
                    plugin.move_items(self.task.source_paths, self.task.destination_path, self.task.options, progress_callback=self.signals.progress, task_context=task_context, task=self.task)
                elif self.task.type == TaskType.DELETE:
                    plugin.delete_items(self.task.source_paths, self.task.options, progress_callback=self.signals.progress, task_context=task_context, task=self.task)

            elif self.task.type == TaskType.SYNC:
                self.directory_synchronizer.synchronize(self.task.source_paths[0], self.task.destination_path, self.task.options, task_context=task_context, task=self.task)
            elif self.task.type == TaskType.CREATE_ARCHIVE:
                plugin = self.task.options.get("plugin")
                if plugin:
                    plugin.create_archive(self.task.source_paths, self.task.destination_path, self.task.options, progress_callback=self.signals.progress, task_context=task_context, task=self.task)
            elif self.task.type == TaskType.EXTRACT_ARCHIVE:
                plugin = self.task.options.get("plugin")
                if plugin:
                    plugin.extract_archive(self.task.source_paths[0], self.task.destination_path, self.task.options, progress_callback=self.signals.progress, task_context=task_context, task=self.task)
            elif self.task.type == TaskType.CHECKSUM:
                plugin = self.task.options.get("plugin")
                algorithm = self.task.options.get("algorithm")
                if plugin and algorithm:
                    checksum = plugin.calculate_checksum(self.task.source_paths[0], algorithm, progress_callback=self.signals.progress, task_context=task_context, task=self.task)
                    self.task.result = checksum
            elif self.task.type == TaskType.SEARCH:
                plugin = self.task.options.get("plugin")
                if plugin:
                    results = plugin.search(self.task.source_paths[0], self.task.options.get("query"), self.task.options, progress_callback=self.signals.progress, task_context=task_context, task=self.task)
                    self.task.result = results
            elif self.task.type == TaskType.CALCULATE_SIZE:
                size = self.file_manager.calculate_directory_size(self.task.source_paths[0], task_context=task_context, task=self.task)
                self.task.result = size

            if self.task.status != TaskStatus.CANCELLED:
                self.task.set_status(TaskStatus.FINISHED)

        except Exception as e:
            # Check if task was cancelled (either via context flag or specific exception message)
            if (self.task.context and self.task.context.is_cancelled) or "cancelled" in str(e).lower():
                logging.info(f"Task {self.task.id} cancelled by user.")
                self.task.set_status(TaskStatus.CANCELLED)
            # Handle FileNotFoundError specifically for DELETE tasks (treat as success/warning)
            elif self.task.type == TaskType.DELETE and isinstance(e, FileNotFoundError):
                logging.warning(f"Task {self.task.id}: File not found during deletion (ignored): {e}")
                self.task.set_details(f"File already gone: {e}")
                self.task.set_status(TaskStatus.FINISHED)
            else:
                logging.error(f"Error executing task {self.task.id}: {e}", exc_info=True)
                self.task.set_details(str(e))
                self.task.set_status(TaskStatus.ERROR)
        finally:
            self.signals.finished.emit()


class TaskQueueManager(QObject):
    task_added = pyqtSignal(Task)
    task_completed = pyqtSignal(Task) # Emitted on success
    task_finished = pyqtSignal(Task)  # Emitted on success, error, or cancel
    queue_cleared = pyqtSignal()

    def __init__(self, file_manager, directory_synchronizer, plugin_manager, background_task_manager):
        super().__init__()
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.plugin_manager = plugin_manager
        self.background_task_manager = background_task_manager
        self.queue = []
        self.active_tasks = {}
        self.all_tasks = [] # Keep track of all tasks, including finished ones

    def add_task(self, task: Task):
        self.queue.append(task)
        self.all_tasks.append(task)
        self.task_added.emit(task)
        self.process_queue()

    def process_queue(self):
        # Check if we can start a new task
        if len(self.active_tasks) < self.background_task_manager.thread_pool.maxThreadCount():
            if self.queue:
                task = self.queue.pop(0)
                self.active_tasks[task.id] = task
                
                worker = TaskWorker(task, self.file_manager, self.directory_synchronizer, self.plugin_manager)
                
                # Use BackgroundTaskManager to run the worker
                signals = self.background_task_manager.run_task(task, worker)
                
                # Connect the finished signal from the background manager
                if signals:
                    signals.finished.connect(lambda: self._on_task_finished(task))
                
    def _on_task_finished(self, task):
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        
        if task.status == TaskStatus.FINISHED:
            self.task_completed.emit(task)
            
        self.task_finished.emit(task)
        self.process_queue()

    def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            self.background_task_manager.cancel_task(task_id)
            # No need to set status here, the worker will handle it via task_context

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
        self.all_tasks = [task for task in self.all_tasks if task.status not in [TaskStatus.FINISHED, TaskStatus.ERROR]]
        self.queue_cleared.emit()
