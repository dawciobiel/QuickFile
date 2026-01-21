import importlib.util
import logging
import multiprocessing
import os
import sys
import traceback
from multiprocessing.connection import Connection

from PyQt6.QtCore import QObject, pyqtSignal


# --- Code running in the child process ---

def run_plugin_process(pipe: Connection, plugin_path: str, metadata: dict):
    """
    Entry point for the child process.
    """
    # Configure logging in the child process
    logging.basicConfig(level=logging.DEBUG, format=f'[Plugin {metadata["id"]}] %(message)s')
    logger = logging.getLogger(f"PluginProcess-{metadata['id']}")

    def progress_forwarder(value):
        """Forwards progress from the plugin to the main process via the pipe."""
        # noinspection PyUnresolvedReferences
        pipe.send({'type': 'PROGRESS', 'value': value})

    try:
        # Invalidate import caches to ensure fresh module loading
        importlib.invalidate_caches()

        # 1. Environment setup (sys.path)
        libs_dir = os.path.join(plugin_path, "libs")
        if os.path.exists(libs_dir):
            sys.path.insert(0, libs_dir)
        sys.path.insert(0, plugin_path)

        logger.debug(f"sys.path in plugin process: {sys.path}")  # Log sys.path

        # 2. Load the plugin
        entry_point = metadata["entry_point"]
        module_name, class_name = entry_point.split(":")
        module_file_path = os.path.join(plugin_path, module_name.replace('.', os.sep) + '.py')

        spec = importlib.util.spec_from_file_location(metadata["id"], module_file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin_class = getattr(module, class_name)
        plugin_instance = plugin_class()

        logger.info("Plugin loaded successfully in sandbox.")

        # 3. Message loop
        while True:
            # noinspection PyUnresolvedReferences
            if pipe.poll(1):  # Wait 1s for a message
                # noinspection PyUnresolvedReferences
                msg = pipe.recv()
                if msg['type'] == 'EXIT':
                    break
                elif msg['type'] == 'CALL':
                    method_name = msg['method']
                    args = msg.get('args', [])
                    kwargs = msg.get('kwargs', {})

                    # Replace the placeholder with the actual progress forwarder
                    if 'progress_callback' in kwargs:
                        kwargs['progress_callback'] = progress_forwarder

                    try:
                        if hasattr(plugin_instance, method_name):
                            method = getattr(plugin_instance, method_name)
                            result = method(*args, **kwargs)
                            # noinspection PyUnresolvedReferences
                            pipe.send({'type': 'RESPONSE', 'status': 'success', 'result': result})
                        else:
                            # noinspection PyUnresolvedReferences
                            pipe.send(
                                {'type': 'RESPONSE', 'status': 'error', 'error': f'Method {method_name} not found'})
                    except Exception as e:
                        # noinspection PyUnresolvedReferences
                        pipe.send({'type': 'RESPONSE', 'status': 'error', 'error': str(e),
                                   'traceback': traceback.format_exc()})
    except Exception as e:
        logger.error(f"Critical error in plugin process: {e}")
        # noinspection PyUnresolvedReferences
        pipe.send({'type': 'RESPONSE', 'status': 'critical_error', 'error': str(e)})


# --- Code used in the main application ---

class SandboxedPluginWrapper(QObject):
    progress_updated = pyqtSignal(object)

    def __init__(self, plugin_path, metadata):
        super().__init__()
        self.plugin_path = plugin_path
        self.metadata = metadata
        self.process = None
        self.parent_pipe, self.child_pipe = multiprocessing.Pipe()

    def start(self):
        self.process = multiprocessing.Process(
            target=run_plugin_process,
            args=(self.child_pipe, self.plugin_path, self.metadata)
        )
        self.process.start()

    def stop(self):
        if self.process and self.process.is_alive():
            # noinspection PyUnresolvedReferences
            self.parent_pipe.send({'type': 'EXIT'})
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.terminate()

    def __getattr__(self, name):
        """
        Magic: Redirects method calls to the child process.
        e.g., plugin.get_name() -> sends CALL get_name message
        """

        def wrapper(*args, **kwargs):
            if not self.process or not self.process.is_alive():
                raise RuntimeError("Plugin process is not running")

            # Replace the actual signal with a placeholder that the child process will understand
            if 'progress_callback' in kwargs:
                kwargs['progress_callback'] = True  # Placeholder

            # noinspection PyUnresolvedReferences
            self.parent_pipe.send({
                'type': 'CALL',
                'method': name,
                'args': args,
                'kwargs': kwargs
            })

            # Wait for response (blocking with timeout)
            while True:
                # noinspection PyUnresolvedReferences
                if self.parent_pipe.poll(5):  # Timeout 5s
                    # noinspection PyUnresolvedReferences
                    response = self.parent_pipe.recv()
                    if response.get('type') == 'PROGRESS':
                        self.progress_updated.emit(response['value'])
                        continue  # Continue waiting for the final response
                    elif response.get('type') == 'RESPONSE':
                        if response['status'] == 'success':
                            return response['result']
                        else:
                            raise Exception(f"Plugin error: {response.get('error')}")
                    else:
                        raise Exception(f"Invalid response from plugin: {response}")
                else:
                    raise TimeoutError("Plugin timed out")

        return wrapper
