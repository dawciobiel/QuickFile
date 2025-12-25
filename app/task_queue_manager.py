import uuid
import time
import os
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

from file_operations.file_manager import OperationCancelledError


class TaskStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    PAUSED = "Paused"
    FINISHED = "Finished"
    CANCELLED = "Cancelled"
    ERROR = "Error"

class TaskType(Enum):
    COPY = "Copy"
    MOVE = "Move"
    DELETE = "Delete"
    ARCHIVE = "Archive"
    EXTRACT = "Extract"
    SYNC = "Sync"

class Task(QObject):
    status_changed = pyqtSignal(object)
    progress_changed = pyqtSignal(int)
    details_changed = pyqtSignal(str)
    directory_changed = pyqtSignal(str)

    def __init__(self, task_type: TaskType, source_paths, destination_path=None, options=None):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options or {}
        
        self._status = TaskStatus.PENDING
        self._progress = 0
        self._current_details = ""
        
        self.start_time = None
        self.end_time = None
        self.error_message = None
        
        self.task_context = None

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, new_status):
        if self._status != new_status:
            self._status = new_status
            self.status_changed.emit(new_status)
            if new_status == TaskStatus.RUNNING and self.start_time is None:
                self.start_time = time.time()
            elif new_status in [TaskStatus.FINISHED, TaskStatus.CANCELLED, TaskStatus.ERROR]:
                self.end_time = time.time()

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        if self._progress != value:
            self._progress = value
            self.progress_changed.emit(value)

    def set_details(self, details):
        if self._current_details != details:
            self._current_details = details
            self.details_changed.emit(details)

class TaskQueueManager(QObject):
    task_added = pyqtSignal(Task)
    task_removed = pyqtSignal(str)
    queue_cleared = pyqtSignal()
    
    def __init__(self, background_task_manager, file_manager, directory_synchronizer, plugin_manager):
        super().__init__()
        self.background_task_manager = background_task_manager
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.plugin_manager = plugin_manager
        self.tasks = []
        self.current_task = None

    def add_task(self, task: Task):
        self.tasks.append(task)
        self.task_added.emit(task)
        self._process_queue()

    def clear_finished_tasks(self):
        self.tasks = [task for task in self.tasks if task.status not in [TaskStatus.FINISHED, TaskStatus.CANCELLED, TaskStatus.ERROR]]
        self.queue_cleared.emit()

    def _process_queue(self):
        if self.current_task and self.current_task.status == TaskStatus.RUNNING:
            return
        
        next_task = next((t for t in self.tasks if t.status == TaskStatus.PENDING), None)
        if next_task:
            self._start_task(next_task)

    def _start_task(self, task: Task):
        self.current_task = task
        task.status = TaskStatus.RUNNING
        
        func, args, kwargs = self._get_task_function_and_args(task)
        if not func:
            task.status = TaskStatus.ERROR
            task.error_message = f"Unsupported task type or missing plugin: {task.type}"
            self._on_task_finished()
            return

        signals = self.background_task_manager.run_task(func, *args, **kwargs)
        task.task_context = self.background_task_manager.current_context
        
        signals.progress.connect(self._on_task_progress)
        signals.finished.connect(self._on_task_finished)
        signals.error.connect(self._on_task_error)

    def _get_task_function_and_args(self, task: Task):
        kwargs = {'task': task}
        if task.type == TaskType.COPY:
            if len(task.source_paths) == 1:
                return self.file_manager.copy_item_with_options, (task.source_paths[0], task.destination_path, task.options), kwargs
            else:
                return self.file_manager.copy_items_batch, (task.source_paths, task.destination_path, task.options), kwargs
        elif task.type == TaskType.MOVE:
            if len(task.source_paths) == 1:
                return self.file_manager.move_item_with_options, (task.source_paths[0], task.destination_path, task.options), kwargs
            else:
                return self.file_manager.move_items_batch, (task.source_paths, task.destination_path, task.options), kwargs
        elif task.type == TaskType.DELETE:
            return self.file_manager.delete_items_batch, (task.source_paths, task.options.get("move_to_trash", True)), kwargs
        elif task.type == TaskType.SYNC:
            return self.directory_synchronizer.synchronize, (task.source_paths[0], task.destination_path, task.options), kwargs
        elif task.type == TaskType.ARCHIVE:
            # For now, default to ZIP or use extension from destination path
            ext = os.path.splitext(task.destination_path)[1]
            plugin = self.plugin_manager.get_archiver_for_extension(ext)
            if plugin:
                return plugin.create_archive, (task.source_paths, task.destination_path, task.options), kwargs
        elif task.type == TaskType.EXTRACT:
            ext = os.path.splitext(task.source_paths[0])[1]
            plugin = self.plugin_manager.get_archiver_for_extension(ext)
            if plugin:
                return plugin.extract_archive, (task.source_paths[0], task.destination_path, task.options), kwargs

        return None, None, None

    def _on_task_progress(self, progress_value):
        if self.current_task:
            self.current_task.progress = progress_value

    def _on_task_finished(self):
        if not self.current_task:
            return
        
        if self.current_task.status == TaskStatus.RUNNING:
            self.current_task.status = TaskStatus.FINISHED
        self.current_task = None
        self._process_queue()

    def _on_task_error(self, error_tuple):
        exctype, value, traceback_str = error_tuple
        
        if issubclass(exctype, OperationCancelledError):
            self.current_task.status = TaskStatus.CANCELLED
        else:
            self.current_task.status = TaskStatus.ERROR
            self.current_task.error_message = str(value)
            
        self.current_task = None
        self._process_queue()

    def pause_task(self, task_id):
        task = self._get_task_by_id(task_id)
        if task and task.status == TaskStatus.RUNNING and task.task_context:
            task.task_context.pause()
            task.status = TaskStatus.PAUSED

    def resume_task(self, task_id):
        task = self._get_task_by_id(task_id)
        if task and task.status == TaskStatus.PAUSED and task.task_context:
            task.task_context.resume()
            task.status = TaskStatus.RUNNING

    def cancel_task(self, task_id):
        task = self._get_task_by_id(task_id)
        if task:
            if task.status == TaskStatus.RUNNING or task.status == TaskStatus.PAUSED:
                if task.task_context:
                    task.task_context.cancel()
            elif task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED

    def _get_task_by_id(self, task_id):
        return next((t for t in self.tasks if t.id == task_id), None)
