import importlib.util
import logging
import multiprocessing
import os
import sys
import traceback
from multiprocessing.connection import Connection
from threading import Thread, Event, Lock
from queue import Queue, Empty
import time
import inspect
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from quickfile.app.plugin_system.api import PluginBase, AbstractTask, TaskContext

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
            
        elif msg_type == 'EXECUTE_ASYNC_TASK':
            self._start_async_task(msg)
            
        elif msg_type == 'EXECUTE_SYNC_METHOD':
            self._execute_sync_method(msg)
            
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

    def _start_async_task(self, msg: dict):
        task_id = msg.get('task_id')
        action_id = msg.get('action_id')
        kwargs = msg.get('kwargs', {})

        self._send_trace(f"Starting async task {task_id} (action: {action_id})")

        try:
            task = self.plugin.create_task(action_id, **kwargs)
            context = WorkerTaskContext()
            self.active_tasks[task_id] = context

            def progress_callback(value):
                self._send_message('TASK_PROGRESS', task_id=task_id, value=value)
            def event_callback(name, payload):
                self._send_message('DATA_EVENT', task_id=task_id, event_name=name, payload=payload)
            def input_request_callback(name, payload):
                return {}

            task._initialize(context, progress_callback, event_callback, input_request_callback)

            thread = threading.Thread(target=self._task_runner, args=(task_id, task))
            thread.daemon = True
            thread.start()

        except Exception as e:
            self._send_message('TASK_FAILED', task_id=task_id, error=str(e), traceback=traceback.format_exc())

    def _execute_sync_method(self, msg: dict):
        task_id = msg.get('task_id')
        method_name = msg.get('method_name')
        args = msg.get('args', [])
        kwargs = msg.get('kwargs', {})

        self._send_trace(f"Executing sync method {method_name}")

        try:
            method = getattr(self.plugin, method_name)
            result = method(*args, **kwargs)
            self._send_message('SYNC_RESPONSE', task_id=task_id, status='success', result=result)
        except Exception as e:
            self._send_message('SYNC_RESPONSE', task_id=task_id, status='error', error=str(e), traceback=traceback.format_exc())

    def _task_runner(self, task_id: str, task: AbstractTask):
        """Wrapper to run the task and handle results/errors."""
        try:
            result = task.run()
            self._send_message('TASK_FINISHED', task_id=task_id, result=result)
        except Exception as e:
            if task_id in self.active_tasks and self.active_tasks[task_id].is_cancelled():
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


def run_plugin_process(pipe: Connection, plugin_path: str, metadata: dict):
    """
    Entry point for the child process.
    Sets up the environment, loads the plugin, and starts the PluginWorker.
    """
    original_stderr = sys.stderr

    def send_trace(msg):
        try:
            pipe.send({'type': 'TRACE', 'msg': msg})
        except (BrokenPipeError, EOFError):
            if original_stderr:
                print(f"[{metadata.get('id', 'Unknown Plugin')}] CRITICAL TRACE ERROR: {msg}", file=original_stderr)
            pass

    try:
        send_trace('Plugin process started. Setting up environment.')
        importlib.invalidate_caches()

        project_root = os.path.abspath(os.path.join(plugin_path, '..', '..', '..'))
        sys.path.insert(0, project_root)
        
        libs_dir = os.path.join(plugin_path, "libs")
        if os.path.exists(libs_dir):
            sys.path.insert(0, libs_dir)
        sys.path.insert(0, plugin_path)
        send_trace(f"sys.path in plugin process: {sys.path}")

        entry_point = metadata["entry_point"]
        module_name, class_name = entry_point.split(":")
        
        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name)
        
        plugin_instance = plugin_class()
        send_trace('Plugin loaded successfully in sandbox.')

        if not isinstance(plugin_instance, PluginBase):
             send_trace(f"WARNING: Plugin {metadata['id']} does not inherit from PluginBase. This is required for the new architecture.")

        worker = PluginWorker(pipe, plugin_instance)
        worker.run()

    except Exception as e:
        error_info = {'type': 'CRITICAL_ERROR', 'error': str(e), 'traceback': traceback.format_exc()}
        try:
            pipe.send(error_info)
        except (BrokenPipeError, EOFError):
            if original_stderr:
                print(f"[{metadata.get('id', 'Unknown Plugin')}] CRITICAL ERROR (pipe closed): {e}", file=original_stderr)
                traceback.print_exc(file=original_stderr)


class SandboxedPluginWrapper(QObject):
    progress_updated = pyqtSignal(str, int)
    method_finished = pyqtSignal(str, object)
    method_failed = pyqtSignal(str, str, str)
    critical_error = pyqtSignal(str)
    data_event_received = pyqtSignal(str, str, dict)

    def __init__(self, plugin_path, metadata):
        super().__init__()
        self.plugin_path = plugin_path
        self.metadata = metadata
        self.process = None
        self.parent_pipe, self.child_pipe = multiprocessing.Pipe()
        self.logger = logging.getLogger(f"SandboxedPluginWrapper-{metadata['id']}")
        self._pipe_thread = None
        self._stop_event = Event()
        self._sync_response_queue = Queue()
        self.active_tasks = set()
        self._pipe_lock = Lock()

    def start(self):
        self.process = multiprocessing.Process(target=run_plugin_process, args=(self.child_pipe, self.plugin_path, self.metadata))
        self.process.daemon = True
        self.process.start()
        self.logger.info("Sandbox process started.")
        
        self._stop_event.clear()
        self._pipe_thread = Thread(target=self._listen_to_pipe)
        self._pipe_thread.daemon = True
        self._pipe_thread.start()

    def stop(self):
        if self.process and self.process.is_alive():
            self.logger.info("Stopping sandbox process...")
            self._stop_event.set()
            try:
                with self._pipe_lock:
                    self.parent_pipe.send({'type': 'TERMINATE'})
            except (BrokenPipeError, EOFError):
                pass
            
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.logger.warning("Sandbox process did not exit gracefully. Terminating.")
                self.process.terminate()
            else:
                self.logger.info("Sandbox process stopped.")
        
        if self._pipe_thread:
            self._pipe_thread.join(timeout=1)

    def _listen_to_pipe(self):
        while not self._stop_event.is_set():
            try:
                with self._pipe_lock:
                    if not self.parent_pipe.poll(0.1):
                        continue
                    msg = self.parent_pipe.recv()
                
                msg_type = msg.get('type')
                
                if msg_type == 'TRACE':
                    self.logger.debug(f"[Plugin Trace] {msg.get('msg', '').strip()}")
                elif msg_type == 'SYNC_RESPONSE':
                    self._sync_response_queue.put(msg)
                elif msg_type == 'TASK_PROGRESS':
                    self.progress_updated.emit(msg['task_id'], msg['value'])
                elif msg_type == 'TASK_FINISHED':
                    self.method_finished.emit(msg['task_id'], msg.get('result'))
                    self.active_tasks.discard(msg['task_id'])
                elif msg_type == 'TASK_FAILED':
                    self.method_failed.emit(msg['task_id'], msg.get('error', 'Unknown error'), msg.get('traceback', ''))
                    self.active_tasks.discard(msg['task_id'])
                elif msg_type == 'TASK_CANCELLED':
                    self.method_failed.emit(msg['task_id'], 'Task cancelled', '')
                    self.active_tasks.discard(msg['task_id'])
                elif msg_type == 'DATA_EVENT':
                    self.data_event_received.emit(msg['task_id'], msg['event_name'], msg['payload'])
                elif msg_type == 'CRITICAL_ERROR':
                    error_message = f"Plugin process crashed: {msg.get('error')}\n{msg.get('traceback')}"
                    self.logger.error(error_message)
                    self.critical_error.emit(error_message)
                    for tid in list(self.active_tasks):
                        self.method_failed.emit(tid, "Plugin process crashed", "")
                    self.active_tasks.clear()
                    break

            except (EOFError, BrokenPipeError):
                self.logger.warning("Pipe closed unexpectedly.")
                if not self._stop_event.is_set():
                    self.critical_error.emit("Plugin process pipe closed unexpectedly.")
                break
            except Exception as e:
                self.logger.error(f"Error in pipe listener thread: {e}", exc_info=True)
                if not self._stop_event.is_set():
                    self.critical_error.emit(f"Internal error in pipe listener: {e}")
                break

    # --- Public API for Main Process ---

    def execute_task(self, task_id, action_id, **kwargs):
        self.active_tasks.add(task_id)
        msg = {
            'type': 'EXECUTE_ASYNC_TASK',
            'task_id': task_id,
            'action_id': action_id,
            'kwargs': kwargs
        }
        with self._pipe_lock:
            self.parent_pipe.send(msg)

    def cancel_task(self, task_id):
        msg = {'type': 'CANCEL_TASK', 'task_id': task_id}
        with self._pipe_lock:
            self.parent_pipe.send(msg)

    def pause_task(self, task_id):
        msg = {'type': 'PAUSE_TASK', 'task_id': task_id}
        with self._pipe_lock:
            self.parent_pipe.send(msg)

    def resume_task(self, task_id):
        msg = {'type': 'RESUME_TASK', 'task_id': task_id}
        with self._pipe_lock:
            self.parent_pipe.send(msg)

    def __getattr__(self, name):
        def sync_method_wrapper(*args, **kwargs):
            task_id = f"sync_{name}_{time.time()}"
            
            serializable_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, (str, int, float, bool, list, dict, tuple, type(None))):
                    serializable_kwargs[k] = v
            
            # Serialize args as well
            serializable_args = []
            for v in args:
                if isinstance(v, (str, int, float, bool, list, dict, tuple, type(None))):
                    serializable_args.append(v)
                else:
                    # Fallback for non-serializable args, though this might cause issues if they are needed
                    # For now, we assume simple types for IPC
                    pass

            msg = {
                'type': 'EXECUTE_SYNC_METHOD',
                'task_id': task_id,
                'method_name': name,
                'args': serializable_args,
                'kwargs': serializable_kwargs
            }
            with self._pipe_lock:
                self.parent_pipe.send(msg)
            
            try:
                response = self._sync_response_queue.get(timeout=10)
                if response.get('task_id') != task_id:
                    raise RuntimeError("Mismatched sync response.")
                if response['status'] == 'success':
                    return response['result']
                else:
                    raise Exception(f"Plugin error: {response.get('error')}")
            except Empty:
                raise TimeoutError(f"Timeout waiting for sync method '{name}'")

        return sync_method_wrapper
