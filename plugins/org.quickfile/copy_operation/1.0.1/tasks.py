# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import shutil
import time
from app.plugin_system.api import AbstractTask

class CopyTask(AbstractTask):
    def __init__(self, source_paths, destination_path, options):
        super().__init__()
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options

    def run(self):
        self.total_size = 0
        self.copied_size = 0
        self.last_progress_update = 0
        self.last_pct = -1
        
        # Calculate total size
        for src in self.source_paths:
            if os.path.isfile(src):
                self.total_size += os.path.getsize(src)
            elif os.path.isdir(src):
                for root, _, files in os.walk(src):
                    for f in files:
                        self.total_size += os.path.getsize(os.path.join(root, f))

        for src in self.source_paths:
            if self.context.is_cancelled():
                raise InterruptedError("Copy operation cancelled.")
            
            basename = os.path.basename(src)
            dest = os.path.join(self.destination_path, basename)
            
            if os.path.isdir(src):
                self._copy_tree_recursive(src, dest)
            else:
                self._copy_file_chunked(src, dest)

    def _copy_tree_recursive(self, src, dest):
        if self.context.is_cancelled():
            raise InterruptedError("Copy operation cancelled.")
        
        os.makedirs(dest, exist_ok=True)
        shutil.copystat(src, dest)
        
        for entry in os.listdir(src):
            src_path = os.path.join(src, entry)
            dest_path = os.path.join(dest, entry)
            
            if os.path.isdir(src_path):
                self._copy_tree_recursive(src_path, dest_path)
            else:
                self._copy_file_chunked(src_path, dest_path)

    def _copy_file_chunked(self, src, dest):
        if self.context.is_cancelled():
            raise InterruptedError("Copy operation cancelled.")
        self.context.wait_if_paused()

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        
        chunk_size = 64 * 1024
        with open(src, 'rb') as fsrc, open(dest, 'wb') as fdest:
            while True:
                if self.context.is_cancelled():
                    raise InterruptedError("Copy operation cancelled.")
                self.context.wait_if_paused()
                
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                
                fdest.write(chunk)
                self.copied_size += len(chunk)
                
                if self.total_size > 0:
                    pct = int(self.copied_size * 100 / self.total_size)
                    if pct != self.last_pct and (time.time() - self.last_progress_update > 0.1):
                        self.emit_progress(pct)
                        self.last_pct = pct
                        self.last_progress_update = time.time()
        
        shutil.copystat(src, dest)
