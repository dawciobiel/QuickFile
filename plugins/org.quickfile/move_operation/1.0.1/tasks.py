# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import shutil
import time
from app.plugin_system.api import AbstractTask

class MoveTask(AbstractTask):
    def __init__(self, source_paths, destination_path, options):
        super().__init__()
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options
        self.total_size = 0
        self.processed_size = 0
        self.last_progress_update = 0
        self.last_pct = -1

    def run(self):
        # Calculate total size for progress reporting (needed for cross-device moves)
        for src in self.source_paths:
            if os.path.isfile(src):
                self.total_size += os.path.getsize(src)
            elif os.path.isdir(src):
                for root, _, files in os.walk(src):
                    for f in files:
                        self.total_size += os.path.getsize(os.path.join(root, f))

        for src in self.source_paths:
            if self.context.is_cancelled():
                raise InterruptedError("Move operation cancelled.")
            self.context.wait_if_paused()

            basename = os.path.basename(src)
            dest = os.path.join(self.destination_path, basename)

            try:
                # Try atomic rename first (fastest, same filesystem)
                os.rename(src, dest)
                # If successful, update progress by the size of the moved item
                self._update_progress_after_rename(src)
            except OSError:
                # Fallback to copy + delete (cross-filesystem)
                if os.path.isdir(src):
                    self._move_tree_recursive(src, dest)
                else:
                    self._move_file_chunked(src, dest)

    def _update_progress_after_rename(self, path):
        """Updates progress counter after a fast rename operation."""
        if os.path.isfile(path):
            self.processed_size += os.path.getsize(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    self.processed_size += os.path.getsize(os.path.join(root, f))
        
        self._emit_progress()

    def _move_tree_recursive(self, src, dest):
        if self.context.is_cancelled():
            raise InterruptedError("Move operation cancelled.")
        
        os.makedirs(dest, exist_ok=True)
        shutil.copystat(src, dest)
        
        for entry in os.listdir(src):
            src_path = os.path.join(src, entry)
            dest_path = os.path.join(dest, entry)
            
            if os.path.isdir(src_path):
                self._move_tree_recursive(src_path, dest_path)
            else:
                self._move_file_chunked(src_path, dest_path)
        
        # Remove source directory after contents are moved
        os.rmdir(src)

    def _move_file_chunked(self, src, dest):
        if self.context.is_cancelled():
            raise InterruptedError("Move operation cancelled.")
        self.context.wait_if_paused()

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        
        chunk_size = 64 * 1024
        with open(src, 'rb') as fsrc, open(dest, 'wb') as fdest:
            while True:
                if self.context.is_cancelled():
                    raise InterruptedError("Move operation cancelled.")
                self.context.wait_if_paused()
                
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                
                fdest.write(chunk)
                self.processed_size += len(chunk)
                self._emit_progress()
        
        shutil.copystat(src, dest)
        os.remove(src)

    def _emit_progress(self):
        if self.total_size > 0:
            pct = int(self.processed_size * 100 / self.total_size)
            if pct != self.last_pct and (time.time() - self.last_progress_update > 0.1):
                self.emit_progress(pct)
                self.last_pct = pct
                self.last_progress_update = time.time()
