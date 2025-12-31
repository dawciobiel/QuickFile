import logging
import os
import uuid
from enum import Enum, auto

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, QMutex, QWaitCondition

from app.plugin_manager import PluginManager


class TaskType(Enum):
    COPY = auto()
    MOVE = auto()
    DELETE = auto()
    ARCHIVE = auto()
    EXTRACT = auto()
    CHECKSUM = auto()
    SEARCH = auto()
    SYNC = auto()
    CALCULATE_SIZE = auto()


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()
    ERROR = auto()
    CANCELLED = auto()

class Task(QObject):
    status_changed = pyqtSignal(TaskStatus)
    progress_changed = pyqtSignal(object)  # Can be int or tuple (read, write)
    details_changed = pyqtSignal(str)
    directory_changed = pyqtSignal(str)

    def __init__(self, task_type: TaskType, source_paths: list[str], destination_path: str = None, options: dict = None):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options or {}
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.details = ""
        self.result = None
        self.error_message = None

    def set_status(self, status: TaskStatus):
        self.status = status
        self.status_changed.emit(status)

    def set_progress(self, progress):
        self.progress = progress
        self.progress_changed.emit(progress)

    def set_details(self, details: str):
        self.details = details
        self.details_changed.emit(details)


class TaskContext:
    def __init__(self):
        self.is_cancelled = False
        self.is_paused = False
        self._pause_mutex = QMutex()
        self._pause_condition = QWaitCondition()

    def cancel(self):
        self.is_cancelled = True
        self.resume()  # Resume if paused to allow cancellation

    def pause(self):
        self._pause_mutex.lock()
        self.is_paused = True
        self._pause_mutex.unlock()

    def resume(self):
        self._pause_mutex.lock()
        self.is_paused = False
        self._pause_condition.wakeAll()
        self._pause_mutex.unlock()

    def wait_if_paused(self):
        self._pause_mutex.lock()
        while self.is_paused:
            self._pause_condition.wait(self._pause_mutex)
        self._pause_mutex.unlock()


class Worker(QRunnable):
    def __init__(self, task: Task, task_context: TaskContext, process_func):
        super().__init__()
        self.task = task
        self.task_context = task_context
        self.process_func = process_func
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.task_context.is_cancelled:
                self.signals.cancelled.emit(self.task)
                return

            result = self.process_func(self.task, self.task_context)

            if self.task_context.is_cancelled:
                self.signals.cancelled.emit(self.task)
            else:
                self.task.result = result
                self.signals.finished.emit(self.task)
        except Exception as e:
            logging.exception(f"Task {self.task.id} failed: {e}")
            self.task.error_message = str(e)
            self.signals.error.emit(self.task, str(e))


class WorkerSignals(QObject):
    finished = pyqtSignal(Task)
    error = pyqtSignal(Task, str)
    cancelled = pyqtSignal(Task)

class TaskQueueManager(QObject):
    task_added = pyqtSignal(Task)
    task_started = pyqtSignal(Task)
    task_completed = pyqtSignal(Task)
    task_failed = pyqtSignal(Task, str)
    task_cancelled = pyqtSignal(Task)
    task_finished = pyqtSignal(Task)  # Emitted for any finish state (success, error, cancel)
    queue_cleared = pyqtSignal()

    def __init__(self, file_manager, directory_synchronizer, plugin_manager: PluginManager):
        super().__init__()
        self.file_manager = file_manager
        self.directory_synchronizer = directory_synchronizer
        self.plugin_manager = plugin_manager
        self.tasks = []  # List of all tasks (history + pending)
        self.active_tasks = {}  # task.id -> (Task, TaskContext)
        self.thread_pool = QThreadPool()
        self.max_concurrent_tasks = 2
        self.thread_pool.setMaxThreadCount(self.max_concurrent_tasks)

    def add_task(self, task: Task):
        logging.debug(f"Adding task {task.id} of type {task.type} to queue.")
        self.tasks.append(task)
        self.task_added.emit(task)
        self.process_queue()

    def process_queue(self):
        logging.debug("Processing queue...")
        # Find pending tasks
        pending_tasks = [t for t in self.tasks if t.status == TaskStatus.PENDING]

        while len(self.active_tasks) < self.max_concurrent_tasks and pending_tasks:
            task = pending_tasks.pop(0)
            self.start_task(task)

        if not pending_tasks and not self.active_tasks:
            logging.debug("No pending tasks found.")

    def start_task(self, task: Task):
        logging.debug(f"Found pending task {task.id}. Starting...")
        task.set_status(TaskStatus.RUNNING)
        self.task_started.emit(task)

        task_context = TaskContext()
        self.active_tasks[task.id] = (task, task_context)

        worker = Worker(task, task_context, self._process_task)
        worker.signals.finished.connect(self._on_task_finished)
        worker.signals.error.connect(self._on_task_error)
        worker.signals.cancelled.connect(self._on_task_cancelled)

        self.thread_pool.start(worker)

    def _process_task(self, task: Task, task_context: TaskContext):
        if task.type == TaskType.COPY:
            plugin = self.plugin_manager.get_standard_operations_plugin()
            if plugin:
                return plugin.copy_items(task.source_paths, task.destination_path, task.options, task.progress_changed, task_context, task)
            else:
                raise Exception("No standard operations plugin found.")
        elif task.type == TaskType.MOVE:
            plugin = self.plugin_manager.get_standard_operations_plugin()
            if plugin:
                return plugin.move_items(task.source_paths, task.destination_path, task.options, task.progress_changed, task_context, task)
            else:
                raise Exception("No standard operations plugin found.")
        elif task.type == TaskType.DELETE:
            plugin = self.plugin_manager.get_standard_operations_plugin()
            if plugin:
                return plugin.delete_items(task.source_paths, task.options, task.progress_changed, task_context, task)
            else:
                raise Exception("No standard operations plugin found.")
        elif task.type == TaskType.ARCHIVE:
            # Determine which plugin to use based on extension or options
            ext = os.path.splitext(task.destination_path)[1].lower()
            plugin = self.plugin_manager.get_archiver_for_extension(ext)
            if not plugin:
                raise ValueError(f"No plugin found for extension {ext}")
            return plugin.create_archive(task.source_paths, task.destination_path, task.options, task.progress_changed, task_context, task)
        elif task.type == TaskType.EXTRACT:
            ext = os.path.splitext(task.source_paths[0])[1].lower()
            plugin = self.plugin_manager.get_archiver_for_extension(ext)
            if not plugin:
                raise ValueError(f"No plugin found for extension {ext}")
            return plugin.extract_archive(task.source_paths[0], task.destination_path, task.options, task.progress_changed, task_context,
                                          task)
        elif task.type == TaskType.CHECKSUM:
            # For checksum, we might have multiple files.
            # We can use the first file to determine the plugin if needed, or iterate.
            # Currently ChecksumPlugin calculates for one file.
            # We need to handle batch processing here or in the plugin.
            # Let's assume we use the first available checksum plugin for now.
            plugins = self.plugin_manager.get_checksum_plugins()
            if not plugins:
                raise ValueError("No checksum plugin available.")
            plugin = plugins[0]

            results = {}
            total_files = len(task.source_paths)
            for i, file_path in enumerate(task.source_paths):
                if task_context.is_cancelled: break
                task.set_details(f"({i + 1}/{total_files}) {os.path.basename(file_path)}")

                # Check if algorithm is supported
                algo = task.options.get("algorithm", "md5")
                if algo not in plugin.get_supported_algorithms():
                    raise ValueError(f"Algorithm {algo} not supported by plugin {plugin.name}")

                checksum = plugin.calculate_checksum(file_path, algo, task.progress_changed, task_context)
                results[file_path] = checksum
            return results

        elif task.type == TaskType.SEARCH:
            # Use the first available search plugin
            plugins = self.plugin_manager.get_search_plugins()
            if not plugins:
                raise ValueError("No search plugin available.")
            plugin = plugins[0]
            return plugin.search(task.source_paths[0], task.options.get("query"), task.options, task.progress_changed, task_context, task)
        elif task.type == TaskType.SYNC:
            return self.directory_synchronizer.synchronize_directories(task.source_paths[0], task.destination_path, task.options,
                                                                       task.progress_changed, task_context, task)
        elif task.type == TaskType.CALCULATE_SIZE:
            # This is a simple task, maybe keep it here or move to a plugin?
            # For now, let's keep it simple using os.walk
            total_size = 0
            path = task.source_paths[0]
            for dirpath, _, filenames in os.walk(path):
                if task_context.is_cancelled: break
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
            return total_size
        else:
            raise ValueError(f"Unknown task type: {task.type}")

    def _on_task_finished(self, task: Task):
        logging.debug(f"Worker: Emitting finished signal.")
        logging.debug(f"_on_task_finished called.")
        logging.debug(f"Task {task.id} finished.")
        task.set_status(TaskStatus.FINISHED)
        self._cleanup_task(task.id)
        logging.debug(f"Emitting task_completed for task {task.id}.")
        self.task_completed.emit(task)
        self.task_finished.emit(task)
        self.process_queue()

    def _on_task_error(self, task: Task, error_message: str):
        logging.error(f"Task {task.id} failed with error: {error_message}")
        task.set_status(TaskStatus.ERROR)
        self._cleanup_task(task.id)
        self.task_failed.emit(task, error_message)
        self.task_finished.emit(task)
        self.process_queue()

    def _on_task_cancelled(self, task: Task):
        logging.info(f"Task {task.id} cancelled.")
        task.set_status(TaskStatus.CANCELLED)
        self._cleanup_task(task.id)
        self.task_cancelled.emit(task)
        self.task_finished.emit(task)
        self.process_queue()

    def _cleanup_task(self, task_id):
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    def cancel_task(self, task_id):
        if task_id in self.active_tasks:
            task, context = self.active_tasks[task_id]
            logging.info(f"Cancelling task {task_id}...")
            context.cancel()
        else:
            # Check if it's in the pending queue
            for task in self.tasks:
                if task.id == task_id and task.status == TaskStatus.PENDING:
                    task.set_status(TaskStatus.CANCELLED)
                    self.task_cancelled.emit(task)
                    self.task_finished.emit(task)
                    logging.info(f"Cancelled pending task {task_id}.")
                    return

    def pause_task(self, task_id):
        if task_id in self.active_tasks:
            task, context = self.active_tasks[task_id]
            if not context.is_paused:
                logging.info(f"Pausing task {task_id}...")
                context.pause()
                task.set_status(TaskStatus.PAUSED)

    def resume_task(self, task_id):
        if task_id in self.active_tasks:
            task, context = self.active_tasks[task_id]
            if context.is_paused:
                logging.info(f"Resuming task {task_id}...")
                context.resume()
                task.set_status(TaskStatus.RUNNING)

    def clear_completed_tasks(self):
        self.tasks = [t for t in self.tasks if t.status not in [TaskStatus.FINISHED, TaskStatus.CANCELLED]]
        self.queue_cleared.emit()

    def clear_error_tasks(self):
        self.tasks = [t for t in self.tasks if t.status != TaskStatus.ERROR]
        self.queue_cleared.emit()

    def clear_all_tasks(self):
        for task in self.tasks:
            if task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
                self.cancel_task(task.id)
        self.tasks = []
        self.queue_cleared.emit()
