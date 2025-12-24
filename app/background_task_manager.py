import logging
import sys
import traceback
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

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
            self.signals.finished.emit()

class BackgroundTaskManager(QObject):
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.current_worker = None
        logging.info(f"Multithreading with maximum {self.thread_pool.maxThreadCount()} threads.")

    def run_task(self, fn, *args, **kwargs):
        worker = Worker(fn, *args, **kwargs)
        self.thread_pool.start(worker)
        self.current_worker = worker
        return worker.signals

    def cancel_current_task(self):
        # This is a simplified cancellation.
        if self.current_worker:
            logging.info("Attempting to cancel the current task.")
            # A more robust implementation would involve a flag.
            # For now, we just clear the queue.
            self.thread_pool.clear()
