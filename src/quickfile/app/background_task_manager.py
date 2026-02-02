# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import sys
import traceback
from typing import Callable

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool, QMutex, QWaitCondition, QThread

from quickfile.app.plugin_sandbox import SandboxedPluginWrapper


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(object)


class TaskContext:
    """
    Manages the state of a background task: cancellation and pausing.
    """
    def __init__(self):
        self._is_cancelled = False
        self._is_paused = False
        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()
        self.plugin_wrapper = None # Add a reference to the plugin wrapper
        self.task_id = None # Add task_id

    @property
    def is_cancelled(self):
        return self._is_cancelled

    def cancel(self):
        self._is_cancelled = True
        if self.plugin_wrapper:
            # Nowa architektura: używamy cancel_task z task_id
            self.plugin_wrapper.cancel_task(self.task_id)
        self.resume()

    def pause(self):
        self._mutex.lock()
        self._is_paused = True
        if self.plugin_wrapper:
            # Nowa architektura: używamy pause_task z task_id
            self.plugin_wrapper.pause_task(self.task_id)
        self._mutex.unlock()

    def resume(self):
        self._mutex.lock()
        if self._is_paused:
            self._is_paused = False
            if self.plugin_wrapper:
                # Nowa architektura: używamy resume_task z task_id
                self.plugin_wrapper.resume_task(self.task_id)
            self._pause_condition.wakeAll()
        self._mutex.unlock()

    def is_paused(self):
        return self._is_paused

    def wait_if_paused(self):
        self._mutex.lock()
        while self._is_paused:
            self._pause_condition.wait(self._mutex)
        self._mutex.unlock()


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        if 'progress_callback' not in self.kwargs:
            self.kwargs['progress_callback'] = self.signals.progress

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            QThread.msleep(10)
            self.signals.finished.emit()


class BackgroundTaskManager(QObject):
    task_progress_updated = pyqtSignal(str, int)
    task_succeeded = pyqtSignal(str, object)
    task_failed = pyqtSignal(str, str)
    task_finished = pyqtSignal(str) # Emitted on success, failure, or cancellation

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.contexts = {}
        self.plugin_wrappers = {} # To keep track of connected wrappers
        logging.info(f"Multithreading with maximum {self.thread_pool.maxThreadCount()} threads.")

    def shutdown(self):
        logging.info("Shutting down BackgroundTaskManager thread pool.")
        self.thread_pool.clear()
        self.thread_pool.waitForDone()

    def register_plugin_task(self, task, plugin_wrapper):
        """Registers a plugin task context without starting a worker."""
        context = TaskContext()
        context.plugin_wrapper = plugin_wrapper
        context.task_id = task.id
        self.contexts[task.id] = context
        task.context = context
        logging.debug(f"Registered plugin task {task.id}")

    def run_task(self, task, target: Callable, **kwargs):
        context = TaskContext()
        self.contexts[task.id] = context
        task.context = context

        worker = Worker(target, task=task, **kwargs)
        worker.signals.progress.connect(lambda p: self.task_progress_updated.emit(task.id, p))
        worker.signals.result.connect(lambda r: self._on_worker_success(task.id, r))
        worker.signals.error.connect(lambda e: self._on_worker_error(task.id, e))
        worker.signals.finished.connect(lambda: self._on_task_finished(task.id))
        
        self.thread_pool.start(worker)

    def _on_worker_success(self, task_id, result):
        self.task_succeeded.emit(task_id, result)

    def _on_worker_error(self, task_id, error_tuple):
        exctype, value, tb = error_tuple
        logging.error(f"Task {task_id} failed: {value}\n{tb}")
        self.task_failed.emit(task_id, str(value))

    def _on_plugin_progress(self, task_id, percentage):
        if task_id in self.contexts:
            self.task_progress_updated.emit(task_id, percentage)

    def _on_plugin_success(self, task_id, result):
        if task_id in self.contexts:
            logging.info(f"Plugin task {task_id} succeeded.")
            self.task_succeeded.emit(task_id, result)
            self._on_task_finished(task_id)
        else:
            logging.warning(f"Received success for unknown task {task_id}")

    def _on_plugin_failure(self, task_id, error, traceback_str):
        if task_id in self.contexts:
            logging.error(f"Plugin task {task_id} failed: {error}\n{traceback_str}")
            self.task_failed.emit(task_id, error)
            self._on_task_finished(task_id)
        else:
            logging.warning(f"Received failure for unknown task {task_id}")

    def _on_task_finished(self, task_id):
        if task_id in self.contexts:
            logging.debug(f"Finishing task {task_id}.")
            self.task_finished.emit(task_id)
            del self.contexts[task_id]

    def cancel_task(self, task_id):
        if task_id in self.contexts:
            logging.info(f"Cancelling task {task_id}...")
            self.contexts[task_id].cancel()

    def pause_task(self, task_id):
        if task_id in self.contexts:
            logging.info(f"Pausing task {task_id}...")
            self.contexts[task_id].pause()

    def resume_task(self, task_id):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            self.background_task_manager.resume_task(task_id)
            task.set_status(TaskStatus.IN_PROGRESS)
