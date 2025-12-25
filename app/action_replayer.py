import json
import logging
import os
import shutil
import tempfile

from file_operations.file_manager import FileManager
from file_operations.directory_synchronizer import DirectorySynchronizer

class ActionReplayer:
    def __init__(self, log_path, file_manager: FileManager, dir_synchronizer: DirectorySynchronizer):
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Action log file not found: {log_path}")
            
        self.log_path = log_path
        self.file_manager = file_manager
        self.dir_synchronizer = dir_synchronizer
        
        self.sandbox_dir = tempfile.mkdtemp(prefix="quickfile_replay_")
        self.path_map = {}
        logging.info(f"ActionReplayer initialized. Sandbox created at: {self.sandbox_dir}")

    def run(self):
        logging.info(f"Starting replay of {self.log_path}...")
        try:
            with open(self.log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    self._process_action(json.loads(line))
            logging.info("Replay finished successfully.")
        except Exception as e:
            logging.error(f"An error occurred during replay: {e}")
            logging.exception(e)
        finally:
            self.cleanup()

    def _remap_path(self, anonymized_path):
        # Simple remapping for now, assuming root is the sandbox
        # We might need a more robust way to handle this if paths are complex
        # For now, we just join the anonymized path to the sandbox root, removing any leading slash
        if anonymized_path.startswith('/'):
            anonymized_path = anonymized_path[1:]
        return os.path.join(self.sandbox_dir, anonymized_path)

    def _process_action(self, action_data):
        action_name = action_data.get("action")
        params = action_data.get("params", {})
        
        logging.info(f"Executing action: {action_name} with params: {params}")

        # Remap paths in params
        remapped_params = {}
        for key, value in params.items():
            if isinstance(value, str) and ('path' in key or 'source' in key or 'destination' in key):
                remapped_params[key] = self._remap_path(value)
            elif isinstance(value, list) and ('paths' in key or 'sources' in key):
                 remapped_params[key] = [self._remap_path(p) for p in value]
            else:
                remapped_params[key] = value
        
        # Get the handler and execute
        handler = getattr(self, f"_handle_{action_name}", None)
        if handler:
            handler(**remapped_params)
        else:
            logging.warning(f"No handler found for action: {action_name}")

    def _ensure_dir_exists(self, file_path):
        dir_name = os.path.dirname(file_path)
        os.makedirs(dir_name, exist_ok=True)

    # --- Action Handlers ---

    def _handle_create_directory(self, path, **kwargs):
        self.file_manager.create_directory(os.path.dirname(path), os.path.basename(path))

    def _handle_create_file(self, path, **kwargs):
        self._ensure_dir_exists(path)
        self.file_manager.create_file(os.path.dirname(path), os.path.basename(path))

    def _handle_copy(self, sources, destination, options, **kwargs):
        self._ensure_dir_exists(destination)
        for src in sources:
            # In sandbox, source files don't exist, so we create dummy ones
            self._ensure_dir_exists(src)
            if not os.path.exists(src):
                with open(src, 'w') as f:
                    f.write("dummy content")
        
        self.file_manager.copy_items_batch(sources, destination, options)

    def _handle_move(self, sources, destination, options, **kwargs):
        self._ensure_dir_exists(destination)
        for src in sources:
            self._ensure_dir_exists(src)
            if not os.path.exists(src):
                with open(src, 'w') as f:
                    f.write("dummy content")

        self.file_manager.move_items_batch(sources, destination, options)

    def _handle_delete(self, paths, options, **kwargs):
        for path in paths:
            # Ensure dummy file exists to be deleted
            if not os.path.exists(path):
                self._ensure_dir_exists(path)
                with open(path, 'w') as f:
                    f.write("dummy content")
        
        self.file_manager.delete_items_batch(paths, options.get("move_to_trash", True))

    def _handle_rename(self, path, new_name, **kwargs):
        if not os.path.exists(path):
            self._ensure_dir_exists(path)
            with open(path, 'w') as f:
                f.write("dummy content")
        self.file_manager.rename_item(path, new_name)

    def _handle_sync_dirs(self, source, destination, options, **kwargs):
        self._ensure_dir_exists(source)
        self._ensure_dir_exists(destination)
        # Create some dummy files to test sync
        with open(os.path.join(source, "file1.txt"), 'w') as f: f.write("a")
        with open(os.path.join(source, "file2.txt"), 'w') as f: f.write("b")
        with open(os.path.join(destination, "file2.txt"), 'w') as f: f.write("c")
        with open(os.path.join(destination, "file3.txt"), 'w') as f: f.write("d")
        
        self.dir_synchronizer.synchronize(source, destination, options)

    def cleanup(self):
        logging.info(f"Cleaning up sandbox directory: {self.sandbox_dir}")
        try:
            shutil.rmtree(self.sandbox_dir)
        except Exception as e:
            logging.error(f"Failed to clean up sandbox directory: {e}")
