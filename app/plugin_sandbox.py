import importlib.util
import inspect
import logging
import multiprocessing
import os
import sys
import time
import traceback
from multiprocessing.connection import Connection
from queue import Queue, Empty
from threading import Thread, Event

from PyQt6.QtCore import QObject, pyqtSignal

from app.plugin_task_interface import SandboxedTaskContext, SandboxedTask


# --- Code running in the child process ---

def run_plugin_process(pipe: Connection, plugin_path: str, metadata: dict):
    """
    Entry point for the child process.
    """
    original_stderr = sys.stderr
    active_contexts = {}  # Słownik do przechowywania kontekstów zadań

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

        def progress_forwarder(task_id):
            def _forward(value):
                try:
                    pipe.send({'type': 'PROGRESS', 'task_id': task_id, 'value': value})
                except (BrokenPipeError, EOFError):
                    pass

            return _forward

        while True:
            if not pipe.poll(0.01):
                continue

            msg = pipe.recv()
            if msg['type'] == 'EXIT':
                send_trace('Received EXIT signal. Terminating.')
                break
            elif msg['type'] == 'CALL':
                method_name = msg['method']
                args = msg.get('args', [])
                kwargs = msg.get('kwargs', {})

                task_id = msg.get('task_id')
                send_trace(f"Received CALL for method: {method_name} with task_id: {task_id}")

                try:
                    method = getattr(plugin_instance, method_name)
                    sig = inspect.signature(method)

                    if 'progress_callback' in sig.parameters:
                        kwargs['progress_callback'] = progress_forwarder(task_id)
                    if 'task_context' in sig.parameters:
                        task_context = SandboxedTaskContext(pipe, task_id)
                        active_contexts[task_id] = task_context
                        kwargs['task_context'] = task_context
                    if 'task' in sig.parameters:
                        kwargs['task'] = SandboxedTask(pipe, task_id)
                    if 'send_trace' in sig.parameters:
                        kwargs['send_trace'] = send_trace

                    send_trace(f"Calling method {method_name} with kwargs: {kwargs}")
                    result = method(*args, **kwargs)
                    send_trace(f"Method {method_name} executed successfully.")
                    
                    try:
                        pipe.send({'type': 'RESPONSE', 'task_id': task_id, 'status': 'success', 'result': result})
                    except Exception as send_err:
                        send_trace(f"Error sending RESPONSE: {send_err}")
                        raise

                except InterruptedError as e:
                    pipe.send({'type': 'RESPONSE', 'task_id': task_id, 'status': 'cancelled', 'error': str(e)})
                except Exception as e:
                    pipe.send({'type': 'RESPONSE', 'task_id': task_id, 'status': 'error', 'error': str(e),
                               'traceback': traceback.format_exc()})
                finally:
                    if task_id in active_contexts:
                        del active_contexts[task_id]

            elif msg['type'] == 'GET_PROPERTY':
                prop_name = msg['property']
                task_id = msg.get('task_id')
                try:
                    prop_value = getattr(plugin_instance, prop_name)
                    if callable(prop_value):
                        raise AttributeError(f"'{prop_name}' is a method, not a property.")
                    pipe.send(
                        {'type': 'PROPERTY_RESPONSE', 'task_id': task_id, 'status': 'success', 'result': prop_value})
                except Exception as e:
                    pipe.send({'type': 'PROPERTY_RESPONSE', 'task_id': task_id, 'status': 'error', 'error': str(e),
                               'traceback': traceback.format_exc()})
            
            elif msg['type'] == 'UPDATE_CANCELLED_STATUS':
                task_id = msg.get('task_id')
                if task_id in active_contexts:
                    active_contexts[task_id].set_cancelled(msg['is_cancelled'])
            
            elif msg['type'] == 'UPDATE_PAUSED_STATUS':
                task_id = msg.get('task_id')
                if task_id in active_contexts:
                    active_contexts[task_id].set_paused(msg['is_paused'])

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
        self._property_response_queue = Queue()
        self.active_async_tasks = set()

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
                self.parent_pipe.send({'type': 'EXIT'})
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
                        self._sync_response_queue.put(response)

                elif msg_type == 'PROPERTY_RESPONSE':
                    self._property_response_queue.put(response)

                elif msg_type == 'PROGRESS':
                    if task_id:
                        self.progress_updated.emit(task_id, response['value'])
                
                elif msg_type == 'TRACE':
                    self.logger.debug(f"[Plugin Trace] {response.get('msg', '').strip()}")

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

    def update_cancelled_status(self, task_id, is_cancelled):
        try:
            self.parent_pipe.send({'type': 'UPDATE_CANCELLED_STATUS', 'task_id': task_id, 'is_cancelled': is_cancelled})
        except (BrokenPipeError, EOFError):
            pass

    def update_paused_status(self, task_id, is_paused):
        try:
            self.parent_pipe.send({'type': 'UPDATE_PAUSED_STATUS', 'task_id': task_id, 'is_paused': is_paused})
        except (BrokenPipeError, EOFError):
            pass

    def __getattr__(self, name):
        if name in self.__dict__ or name in SandboxedPluginWrapper.__dict__:
            return object.__getattribute__(self, name)

        if name in ['name', 'description']:
            self.parent_pipe.send({'type': 'GET_PROPERTY', 'property': name})
            try:
                response = self._property_response_queue.get(timeout=5)
                if response.get('type') == 'PROPERTY_RESPONSE':
                    if response['status'] == 'success':
                        return response['result']
                    else:
                        raise AttributeError(f"Failed to get property '{name}' from plugin: {response.get('error')}\n{response.get('traceback', '')}")
                else:
                    raise RuntimeError(f"Received unexpected message type '{response.get('type')}' from property queue.")
            except Empty:
                raise TimeoutError(f"Timeout waiting for property '{name}' from plugin.")
            except Exception as e:
                raise AttributeError(f"Error getting property '{name}' from plugin: {e}")

        def wrapper(*args, **kwargs):
            if not self.process or not self.process.is_alive():
                raise RuntimeError("Plugin process is not running")

            is_async = 'task' in kwargs
            task_id = None
            
            message = {'type': 'CALL', 'method': name, 'args': args, 'kwargs': {}}

            if is_async:
                task_id = kwargs['task'].id
                self.task_map[task_id] = kwargs['task']
                self.active_async_tasks.add(task_id)
                
                message['task_id'] = task_id
                message['kwargs']['task'] = {'task_id': task_id}
                message['kwargs']['task_context'] = {'task_id': task_id}
                message['kwargs']['progress_callback'] = True
                message['kwargs']['send_trace'] = True
                
                for k, v in kwargs.items():
                    if k not in ['task', 'task_context', 'progress_callback', 'send_trace']:
                        message['kwargs'][k] = v
            else:
                task_id = f"sync_{name}_{time.time()}"
                message['task_id'] = task_id
                message['kwargs'] = kwargs

            self.parent_pipe.send(message)

            if is_async:
                return

            try:
                response = self._sync_response_queue.get(timeout=10)
                
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
