# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import sys
import traceback

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool, QMutex, QWaitCondition, QThread


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(object)  # Changed from int to object to support tuples (read, write)

class TaskContext:
    """
    Manages the state of a background task: cancellation and pausing.
    Replaces the simple CancellationToken.
    """
    def __init__(self):
        self._is_cancelled = False
        self._is_paused = False
        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()

    @property
    def is_cancelled(self):
        return self._is_cancelled

    def cancel(self):
        self._is_cancelled = True
        # If paused, we need to wake up to handle cancellation
        self.resume()

    def pause(self):
        self._mutex.lock()
        self._is_paused = True
        self._mutex.unlock()

    def resume(self):
        self._mutex.lock()
        self._is_paused = False
        self._pause_condition.wakeAll()
        self._mutex.unlock()

    def is_paused(self):
        return self._is_paused

    def wait_if_paused(self):
        """
        Blocks execution if the task is paused until it is resumed.
        """
        self._mutex.lock()
        if self._is_paused:
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
            # Small delay to ensure previous signals (like result) are processed
            # before the thread potentially terminates and cleans up.
            QThread.msleep(10)
            logging.debug("Worker: Emitting finished signal.")
            self.signals.finished.emit()

class BackgroundTaskManager(QObject):
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.contexts = {}
        logging.info(f"Multithreading with maximum {self.thread_pool.maxThreadCount()} threads.")

    def run_task(self, task, runnable: QRunnable):
        # Create a task context
        context = TaskContext()
        self.contexts[task.id] = context
        
        # Assign context to the task object
        task.context = context
        
        # The runnable (e.g., TaskWorker) should have a 'task' attribute
        # and should use the context from it.
        if hasattr(runnable, 'task'):
            runnable.task.context = context
        
        # The runnable should also have a 'signals' attribute
        if hasattr(runnable, 'signals'):
            # Remove worker and context when finished
            runnable.signals.finished.connect(lambda: self._on_task_finished(task.id))
        
        self.thread_pool.start(runnable)
        
        return getattr(runnable, 'signals', None)

    def _on_task_finished(self, task_id):
        if task_id in self.contexts:
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
        if task_id in self.contexts:
            logging.info(f"Resuming task {task_id}...")
            self.contexts[task_id].resume()
