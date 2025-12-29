import uuid
import time
import os
import logging
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
    CHECKSUM = "Checksum"
    SEARCH = "Search"
    CALCULATE_SIZE = "Calculate Size"

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
        self.result = None
        
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
    task_completed = pyqtSignal(Task)
    
    def __init__(self, background_task_manager, file_manager, directory_synchronizer, plugin_manager):
        super().__init__()
        self.background_task_manager = background_task_manager
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.plugin_manager = plugin_manager
        self.tasks = []
        self.current_task = None

    def add_task(self, task: Task):
        logging.debug(f"Adding task {task.id} of type {task.type} to queue.")
        self.tasks.append(task)
        self.task_added.emit(task)
        self._process_queue()

    def clear_all_completed_tasks(self):
        """Clears all tasks that are in a final state (FINISHED, CANCELLED, ERROR)."""
        self.tasks = [task for task in self.tasks if task.status not in [TaskStatus.FINISHED, TaskStatus.CANCELLED, TaskStatus.ERROR]]
        self.queue_cleared.emit()

    def clear_finished_tasks(self):
        """Clears only tasks that completed successfully (FINISHED)."""
        self.tasks = [task for task in self.tasks if task.status != TaskStatus.FINISHED]
        self.queue_cleared.emit()

    def clear_error_tasks(self):
        """Clears only tasks that ended with an error (ERROR)."""
        self.tasks = [task for task in self.tasks if task.status != TaskStatus.ERROR]
        self.queue_cleared.emit()

    def _process_queue(self):
        logging.debug("Processing queue...")
        if self.current_task and self.current_task.status == TaskStatus.RUNNING:
            logging.debug(f"Queue is blocked by running task {self.current_task.id}.")
            return
        
        next_task = next((t for t in self.tasks if t.status == TaskStatus.PENDING), None)
        if next_task:
            logging.debug(f"Found pending task {next_task.id}. Starting...")
            self._start_task(next_task)
        else:
            logging.debug("No pending tasks found.")

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
        signals.result.connect(self._on_task_result)

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
            ext = os.path.splitext(task.destination_path)[1]
            plugin = self.plugin_manager.get_archiver_for_extension(ext)
            if plugin:
                return plugin.create_archive, (task.source_paths, task.destination_path, task.options), kwargs
        elif task.type == TaskType.EXTRACT:
            ext = os.path.splitext(task.source_paths[0])[1]
            plugin = self.plugin_manager.get_archiver_for_extension(ext)
            if plugin:
                return plugin.extract_archive, (task.source_paths[0], task.destination_path, task.options), kwargs
        elif task.type == TaskType.CHECKSUM:
            algorithm = task.options.get("algorithm")
            save_to_file = task.options.get("save_to_file", False)
            for plugin in self.plugin_manager.get_checksum_plugins():
                if algorithm in plugin.get_supported_algorithms():
                    return self._calculate_checksums_batch, (task.source_paths, algorithm, plugin, save_to_file), kwargs
        elif task.type == TaskType.SEARCH:
            plugins = self.plugin_manager.get_search_plugins()
            if plugins:
                plugin = plugins[0]
                query = task.options.get("query")
                return plugin.search, (task.source_paths[0], query, task.options), kwargs
        elif task.type == TaskType.CALCULATE_SIZE:
             return self._calculate_directory_size_task, (task.source_paths[0],), kwargs
        
        return None, None, None

    def _calculate_directory_size_task(self, path, progress_callback=None, task_context=None, task=None):
        logging.debug(f"Starting size calculation for {path}")
        total_size = 0
        file_count = 0
        
        if task: task.set_details("Calculating size...")

        try:
            for dirpath, dirnames, filenames in os.walk(path):
                if task_context and task_context.is_cancelled: break
                if task_context: task_context.wait_if_paused()
                
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        if not os.path.islink(fp):
                            total_size += os.path.getsize(fp)
                            file_count += 1
                    except OSError:
                        pass
                
                if task:
                    task.set_details(f"Scanned {file_count} files...")
                    
        except OSError as e:
            logging.error(f"Error calculating size: {e}")
            
        logging.debug(f"Size calculation finished: {total_size} bytes")
        if task: task.set_details(f"Finished: {total_size} bytes")
        return total_size

    def _calculate_checksums_batch(self, file_paths, algorithm, plugin, save_to_file, progress_callback=None, task_context=None, task=None):
        logging.debug(f"Starting checksum batch for {len(file_paths)} files with algorithm {algorithm}.")
        results = []
        total_files = len(file_paths)
        for i, file_path in enumerate(file_paths):
            if task_context and task_context.is_cancelled: break
            if task_context: task_context.wait_if_paused()
            
            if task: task.set_details(f"Calculating {algorithm}: {os.path.basename(file_path)}")
            
            try:
                logging.debug(f"Checksum batch: Calculating for file {i+1}/{total_files}: {file_path}")
                checksum = plugin.calculate_checksum(file_path, algorithm, task_context=task_context)
                result_str = f"{os.path.basename(file_path)}: {checksum}"
                results.append(result_str)
                logging.debug(f"Checksum for {file_path} is {checksum}")
                
                if save_to_file:
                    checksum_file_path = f"{file_path}.checksum"
                    with open(checksum_file_path, 'w') as f:
                        f.write(f"{checksum}  {os.path.basename(file_path)}\n")
                    if task:
                        task.directory_changed.emit(os.path.dirname(file_path))

            except Exception as e:
                logging.error(f"Checksum calculation failed for {file_path}: {e}")
                results.append(f"{os.path.basename(file_path)}: Error ({e})")
            
            if progress_callback:
                progress_callback.emit(int((i + 1) / total_files * 100))
        
        logging.debug("Checksum batch finished.")
        if task:
            task.set_details("Finished")
        return "\n".join(results)

    def _on_task_progress(self, progress_value):
        if self.current_task:
            self.current_task.progress = progress_value

    def _on_task_result(self, result):
        if self.current_task:
            self.current_task.result = result

    def _on_task_finished(self):
        try:
            logging.debug("_on_task_finished called.")
            if not self.current_task:
                logging.warning("_on_task_finished called but current_task is None.")
                return
            
            logging.debug(f"Task {self.current_task.id} finished.")
            if self.current_task.status == TaskStatus.RUNNING:
                self.current_task.status = TaskStatus.FINISHED
                logging.debug(f"Emitting task_completed for task {self.current_task.id}.")
                self.task_completed.emit(self.current_task)
                
        except Exception as e:
            logging.exception(f"Error in _on_task_finished: {e}")
        finally:
            self.current_task = None
            self._process_queue()

    def _on_task_error(self, error_tuple):
        try:
            exctype, value, traceback_str = error_tuple
            
            logging.error(f"Task {self.current_task.id} failed with error: {value}")
            if issubclass(exctype, OperationCancelledError):
                self.current_task.status = TaskStatus.CANCELLED
            else:
                self.current_task.status = TaskStatus.ERROR
                self.current_task.error_message = str(value)
        except Exception as e:
            logging.exception(f"Error in _on_task_error: {e}")
        finally:
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
