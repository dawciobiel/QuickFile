# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import sys
import time
import traceback
import threading
from multiprocessing.connection import Connection
from typing import Dict, Optional, Type

from .api import PluginBase, AbstractTask, TaskContext

class WorkerTaskContext(TaskContext):
    """
    Concrete implementation of TaskContext used within the worker process.
    Thread-safe.
    """
    def __init__(self):
        self._is_cancelled = False
        self._is_paused = False
        self._lock = threading.Lock()
        self._pause_condition = threading.Condition(self._lock)

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._is_cancelled

    def is_paused(self) -> bool:
        with self._lock:
            return self._is_paused

    def wait_if_paused(self):
        with self._lock:
            while self._is_paused:
                self._pause_condition.wait()

    def set_cancelled(self, value: bool):
        with self._lock:
            self._is_cancelled = value
            # If cancelled, we should also wake up if paused
            if value and self._is_paused:
                self._is_paused = False
                self._pause_condition.notify_all()

    def set_paused(self, value: bool):
        with self._lock:
            self._is_paused = value
            if not value:
                self._pause_condition.notify_all()


class PluginWorker:
    """
    Manages the lifecycle of the plugin process.
    Handles IPC messages and executes tasks in separate threads.
    """
    def __init__(self, pipe: Connection, plugin_instance: PluginBase):
        self.pipe = pipe
        self.plugin = plugin_instance
        self.active_tasks: Dict[str, WorkerTaskContext] = {}
        self.running = True

    def run(self):
        """Main loop of the plugin process."""
        self._send_trace("PluginWorker started.")
        
        while self.running:
            if not self.pipe.poll(0.01):
                continue

            try:
                msg = self.pipe.recv()
                self._handle_message(msg)
            except (EOFError, BrokenPipeError):
                self._send_trace("Pipe closed. Terminating worker.")
                self.running = False
            except Exception as e:
                self._send_error("CRITICAL_ERROR", str(e), traceback.format_exc())
                self.running = False

    def _handle_message(self, msg: dict):
        msg_type = msg.get('type')
        
        if msg_type == 'TERMINATE':
            self.running = False
            
        elif msg_type == 'EXECUTE_TASK':
            self._start_task(msg)
            
        elif msg_type == 'CANCEL_TASK':
            task_id = msg.get('task_id')
            if task_id in self.active_tasks:
                self.active_tasks[task_id].set_cancelled(True)
                self._send_trace(f"Task {task_id} marked for cancellation.")
                
        elif msg_type == 'PAUSE_TASK':
            task_id = msg.get('task_id')
            if task_id in self.active_tasks:
                self.active_tasks[task_id].set_paused(True)
                
        elif msg_type == 'RESUME_TASK':
            task_id = msg.get('task_id')
            if task_id in self.active_tasks:
                self.active_tasks[task_id].set_paused(False)

    def _start_task(self, msg: dict):
        task_id = msg.get('task_id')
        action_id = msg.get('action_id')
        kwargs = msg.get('kwargs', {})

        self._send_trace(f"Starting task {task_id} (action: {action_id})")

        try:
            # Create task instance using the plugin factory
            task = self.plugin.create_task(action_id, **kwargs)
            
            # Create context
            context = WorkerTaskContext()
            self.active_tasks[task_id] = context

            # Prepare callbacks
            def progress_callback(value):
                self._send_message('TASK_PROGRESS', task_id=task_id, value=value)

            def event_callback(name, payload):
                self._send_message('DATA_EVENT', task_id=task_id, event_name=name, payload=payload)

            def input_request_callback(name, payload):
                # TODO: Implement synchronous input request (blocking wait for response)
                return {}

            # Initialize task
            task._initialize(context, progress_callback, event_callback, input_request_callback)

            # Start task in a new thread
            thread = threading.Thread(target=self._task_runner, args=(task_id, task))
            thread.daemon = True
            thread.start()

        except Exception as e:
            self._send_message('TASK_FAILED', task_id=task_id, error=str(e), traceback=traceback.format_exc())

    def _task_runner(self, task_id: str, task: AbstractTask):
        """Wrapper to run the task and handle results/errors."""
        try:
            result = task.run()
            self._send_message('TASK_FINISHED', task_id=task_id, result=result)
        except Exception as e:
            # Check if it was a cancellation exception (some tasks might raise it)
            # Or if the context is marked as cancelled
            if self.active_tasks[task_id].is_cancelled():
                 self._send_message('TASK_CANCELLED', task_id=task_id)
            else:
                self._send_message('TASK_FAILED', task_id=task_id, error=str(e), traceback=traceback.format_exc())
        finally:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def _send_message(self, type_name, **kwargs):
        try:
            msg = {'type': type_name, **kwargs}
            self.pipe.send(msg)
        except (BrokenPipeError, EOFError):
            pass

    def _send_trace(self, msg):
        self._send_message('TRACE', msg=msg)

    def _send_error(self, type_name, error, tb):
        self._send_message(type_name, error=error, traceback=tb)
