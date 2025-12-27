import logging
import sys
import traceback
import time
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool, QMutex, QWaitCondition, QThread

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

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
        self.current_worker = None
        self.current_context = None
        logging.info(f"Multithreading with maximum {self.thread_pool.maxThreadCount()} threads.")

    def run_task(self, fn, *args, **kwargs):
        # Create a task context (handles cancellation and pause)
        self.current_context = TaskContext()
        
        # Pass the context to the function via 'task_context' argument
        kwargs['task_context'] = self.current_context
        
        worker = Worker(fn, *args, **kwargs)
        self.thread_pool.start(worker)
        self.current_worker = worker
        return worker.signals

    def cancel_current_task(self):
        if self.current_context:
            logging.info("Cancelling current task...")
            self.current_context.cancel()
        self.thread_pool.clear()

    def pause_current_task(self):
        if self.current_context:
            logging.info("Pausing current task...")
            self.current_context.pause()

    def resume_current_task(self):
        if self.current_context:
            logging.info("Resuming current task...")
            self.current_context.resume()
