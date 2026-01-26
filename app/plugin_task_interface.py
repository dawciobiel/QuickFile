import time
from multiprocessing.connection import Connection
from typing import Optional

class SandboxedTaskContext:
    """
    A serializable representation of TaskContext for sandboxed plugins.
    Communicates with the main process via pipe to check cancellation/pause status.
    """
    def __init__(self, pipe: Connection, task_id: str):
        self._pipe = pipe
        self._task_id = task_id
        self._is_cancelled = False
        self._is_paused = False

    @property
    def is_cancelled(self) -> bool:
        # Request status from main process
        self._pipe.send({'type': 'GET_CONTEXT_STATUS', 'task_id': self._task_id})
        response = self._pipe.recv()
        self._is_cancelled = response.get('is_cancelled', False)
        return self._is_cancelled

    @property
    def is_paused(self) -> bool:
        # Request status from main process
        self._pipe.send({'type': 'GET_CONTEXT_STATUS', 'task_id': self._task_id})
        response = self._pipe.recv()
        self._is_paused = response.get('is_paused', False)
        return self._is_paused

    def wait_if_paused(self):
        while self.is_paused:
            time.sleep(0.1) # Poll every 100ms

    def check_cancelled(self):
        if self.is_cancelled:
            raise InterruptedError("Task cancelled by user.")


class SandboxedTask:
    """
    A serializable representation of Task for sandboxed plugins.
    Communicates with the main process via pipe to update task details/progress.
    """
    def __init__(self, pipe: Connection, task_id: str):
        self._pipe = pipe
        self._task_id = task_id

    def set_details(self, details: str):
        self._pipe.send({'type': 'SET_TASK_DETAILS', 'task_id': self._task_id, 'details': details})

    def set_overall_progress(self, progress: int):
        self._pipe.send({'type': 'SET_TASK_OVERALL_PROGRESS', 'task_id': self._task_id, 'progress': progress})

    # Add other necessary methods from Task that plugins might call
    # For example, set_progress if it's different from set_overall_progress
    # For now, we'll assume set_overall_progress is sufficient for sandboxed plugins.
