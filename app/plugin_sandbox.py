import importlib.util
import logging
import multiprocessing
import os
import sys
import traceback
from multiprocessing.connection import Connection
from threading import Thread, Event
from queue import Queue, Empty
import time

from PyQt6.QtCore import QObject, pyqtSignal

from app.plugin_task_interface import SandboxedTaskContext, SandboxedTask


# --- Code running in the child process ---

def run_plugin_process(pipe: Connection, plugin_path: str, metadata: dict):
    """
    Entry point for the child process.
    """
    original_stderr = sys.stderr
    current_task_id = None

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

        libs_dir = os.path.join(plugin_path, "libs")
        if os.path.exists(libs_dir):
            sys.path.insert(0, libs_dir)
        sys.path.insert(0, plugin_path)
        send_trace(f"sys.path in plugin process: {sys.path}")

        entry_point = metadata["entry_point"]
        module_name, class_name = entry_point.split(":")
        module_file_path = os.path.join(plugin_path, module_name.replace('.', os.sep) + '.py')
        send_trace(f"Loading plugin from: {module_file_path}")

        spec = importlib.util.spec_from_file_location(metadata["id"], module_file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugin_class = getattr(module, class_name)
        plugin_instance = plugin_class()
        send_trace('Plugin loaded successfully in sandbox.')

        def progress_forwarder(value):
            if current_task_id:
                try:
                    pipe.send({'type': 'PROGRESS', 'task_id': current_task_id, 'value': value})
                except (BrokenPipeError, EOFError):
                    pass

        while True:
            if not pipe.poll(1):
                time.sleep(0.01)
                continue

            msg = pipe.recv()
            if msg['type'] == 'EXIT':
                send_trace('Received EXIT signal. Terminating.')
                break
            elif msg['type'] == 'CALL':
                method_name = msg['method']
                args = msg.get('args', [])
                kwargs = msg.get('kwargs', {})
                
                current_task_id = msg.get('task_id')

                send_trace(f"Received CALL for method: {method_name} with task_id: {current_task_id}")

                if 'progress_callback' in kwargs:
                    kwargs['progress_callback'] = progress_forwarder
                if 'task_context' in kwargs:
                    kwargs['task_context'] = SandboxedTaskContext(pipe, kwargs['task_context']['task_id'])
                if 'task' in kwargs:
                    kwargs['task'] = SandboxedTask(pipe, kwargs['task']['task_id'])
                if 'send_trace' in kwargs:
                    kwargs['send_trace'] = send_trace

                try:
                    send_trace(f"Calling method {method_name} with kwargs: {kwargs}") # Added debug trace
                    method = getattr(plugin_instance, method_name)
                    send_trace(f"Executing method: {method_name}")
                    result = method(*args, **kwargs)
                    send_trace(f"Method {method_name} executed successfully.")
                    pipe.send({'type': 'RESPONSE', 'task_id': current_task_id, 'status': 'success', 'result': result})
                except InterruptedError as e:
                    pipe.send({'type': 'RESPONSE', 'task_id': current_task_id, 'status': 'cancelled', 'error': str(e)})
                except Exception as e:
                    pipe.send({'type': 'RESPONSE', 'task_id': current_task_id, 'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()})
                finally:
                    current_task_id = None

    except Exception as e:
        error_info = {'type': 'CRITICAL_ERROR', 'error': str(e), 'traceback': traceback.format_exc()}
        try:
            pipe.send(error_info)
        except (BrokenPipeError, EOFError):
            if original_stderr:
                print(f"[{metadata.get('id', 'Unknown Plugin')}] CRITICAL ERROR (pipe closed): {e}", file=original_stderr)
                traceback.print_exc(file=original_stderr)


# --- Code used in the main application ---

class SandboxedPluginWrapper(QObject):
    progress_updated = pyqtSignal(str, int)
    method_finished = pyqtSignal(str, object)
    method_failed = pyqtSignal(str, str, str)
    critical_error = pyqtSignal(str)

    def __init__(self, plugin_path, metadata):
        super().__init__()
        self.plugin_path = plugin_path
        self.metadata = metadata
        self.process = None
        self.parent_pipe, self.child_pipe = multiprocessing.Pipe()
        self.task_map = {}
        self.logger = logging.getLogger(f"SandboxedPluginWrapper-{metadata['id']}")
        self._pipe_thread = None
        self._stop_event = Event()
        self._sync_response_queue = Queue()
        self.active_async_tasks = set()

    def start(self):
        self.process = multiprocessing.Process(target=run_plugin_process, args=(self.child_pipe, self.plugin_path, self.metadata))
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
                self.parent_pipe.send({'type': 'EXIT'})
            except (BrokenPipeError, EOFError):
                pass # Pipe might already be closed
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
                if not self.parent_pipe.poll(0.1):
                    continue
                
                response = self.parent_pipe.recv()
                msg_type = response.get('type')
                task_id = response.get('task_id')

                if msg_type == 'RESPONSE':
                    if task_id in self.active_async_tasks:
                        if response['status'] == 'success':
                            self.method_finished.emit(task_id, response.get('result'))
                        elif response['status'] == 'cancelled':
                            self.method_failed.emit(task_id, response.get('error', 'Task cancelled'), '')
                        else:
                            self.method_failed.emit(task_id, response.get('error', ''), response.get('traceback', ''))
                        self.active_async_tasks.discard(task_id)
                    else:
                        # This is a response for a synchronous call
                        self._sync_response_queue.put(response)
                
                elif msg_type == 'PROGRESS':
                    if task_id:
                        self.progress_updated.emit(task_id, response['value'])
                
                elif msg_type == 'TRACE':
                    self.logger.debug(f"[Plugin Trace] {response.get('msg', '').strip()}")

                elif msg_type == 'GET_CONTEXT_STATUS':
                    task = self.task_map.get(task_id)
                    if task and task.context:
                        self.parent_pipe.send({'is_cancelled': bool(task.context.is_cancelled), 'is_paused': bool(task.context.is_paused)})
                    else:
                        self.parent_pipe.send({'is_cancelled': False, 'is_paused': False})

                elif msg_type in ('SET_TASK_DETAILS', 'SET_TASK_OVERALL_PROGRESS', 'SET_TASK_PROGRESS'):
                    task = self.task_map.get(task_id)
                    if task:
                        if msg_type == 'SET_TASK_DETAILS':
                            task.set_details(response['details'])
                        elif msg_type == 'SET_TASK_OVERALL_PROGRESS':
                            task.set_overall_progress(response['progress'])
                        elif msg_type == 'SET_TASK_PROGRESS':
                            task.set_progress(response['progress'])
                
                elif msg_type == 'EMIT_DIRECTORY_CHANGED':
                    task = self.task_map.get(task_id)
                    if task:
                        task.directory_changed.emit(response['path'])

                elif msg_type == 'CRITICAL_ERROR':
                    error_message = f"Plugin process crashed: {response.get('error')}\n{response.get('traceback')}"
                    self.logger.error(error_message)
                    self.critical_error.emit(error_message)
                    for tid in list(self.active_async_tasks):
                        self.method_failed.emit(tid, "Plugin process crashed", response.get('traceback', ''))
                    self.active_async_tasks.clear()
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

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            if not self.process or not self.process.is_alive():
                raise RuntimeError("Plugin process is not running")

            is_async = 'task' in kwargs
            task_id = None
            
            # Prepare the message to be sent
            message = {'type': 'CALL', 'method': name, 'args': args, 'kwargs': {}}

            if is_async:
                task_id = kwargs['task'].id
                self.task_map[task_id] = kwargs['task']
                self.active_async_tasks.add(task_id)
                
                # Pass only the necessary info to the plugin process
                message['task_id'] = task_id
                message['kwargs']['task'] = {'task_id': task_id}
                message['kwargs']['task_context'] = {'task_id': task_id}
                message['kwargs']['progress_callback'] = True # Placeholder
                message['kwargs']['send_trace'] = True # Placeholder
                
                # Pass other relevant kwargs
                for k, v in kwargs.items():
                    if k not in ['task', 'task_context', 'progress_callback', 'send_trace']:
                        message['kwargs'][k] = v
            else:
                # For sync calls, generate a temporary ID
                task_id = f"sync_{name}_{time.time()}"
                message['task_id'] = task_id
                message['kwargs'] = kwargs

            self.logger.debug(f"Sending CALL for method: {name} (async: {is_async})")
            self.parent_pipe.send(message)

            if is_async:
                return

            # --- Synchronous path ---
            try:
                response = self._sync_response_queue.get(timeout=10)
                
                # Verify if the response matches the request
                if response.get('task_id') != task_id:
                    raise RuntimeError(f"Mismatched sync response. Expected {task_id}, got {response.get('task_id')}")

                if response.get('type') == 'RESPONSE':
                    if response['status'] == 'success':
                        return response['result']
                    else:
                        raise Exception(f"Plugin error: {response.get('error')}\n{response.get('traceback', '')}")
                else:
                    raise RuntimeError(f"Received unexpected message type '{response.get('type')}' from sync queue.")
            except Empty:
                raise TimeoutError(f"Timeout waiting for synchronous response for method '{name}'.")

        return wrapper
