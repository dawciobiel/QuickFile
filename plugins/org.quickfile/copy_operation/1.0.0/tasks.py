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
        total_size = 0
        copied_size = 0
        
        # Calculate total size for progress
        for src in self.source_paths:
            if os.path.isfile(src):
                total_size += os.path.getsize(src)
            elif os.path.isdir(src):
                for root, _, files in os.walk(src):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))

        last_progress_update = 0
        last_pct = -1

        for src in self.source_paths:
            if self.context.is_cancelled():
                raise InterruptedError("Copy operation cancelled.")
            self.context.wait_if_paused()

            basename = os.path.basename(src)
            dest = os.path.join(self.destination_path, basename)

            if os.path.isdir(src):
                self._copy_tree(src, dest, total_size, copied_size, last_progress_update, last_pct)
                # Update copied_size after tree copy is tricky without return, 
                # so _copy_tree handles progress updates internally and updates copied_size reference? 
                # No, simple recursion is easier.
                # Let's use a helper that returns bytes copied.
            else:
                self._copy_file(src, dest, total_size, copied_size, last_progress_update, last_pct)
                copied_size += os.path.getsize(src)

    def _copy_file(self, src, dest, total_size, current_copied, last_update, last_pct):
        if self.context.is_cancelled():
            raise InterruptedError("Copy operation cancelled.")
        self.context.wait_if_paused()

        # Ensure dest dir exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        file_size = os.path.getsize(src)
        chunk_size = 64 * 1024 # 64KB
        bytes_written = 0

        with open(src, 'rb') as fsrc, open(dest, 'wb') as fdest:
            while True:
                if self.context.is_cancelled():
                    raise InterruptedError("Copy operation cancelled.")
                self.context.wait_if_paused()

                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                
                fdest.write(chunk)
                bytes_written += len(chunk)
                
                # Update global progress
                if total_size > 0:
                    current_total = current_copied + bytes_written
                    pct = int(current_total * 100 / total_size)
                    if pct != last_pct and (time.time() - last_update > 0.1):
                        self.emit_progress(pct)
                        last_pct = pct
                        last_update = time.time()
        
        # Preserve metadata
        shutil.copystat(src, dest)

    def _copy_tree(self, src, dest, total_size, current_copied, last_update, last_pct):
        if self.context.is_cancelled():
            raise InterruptedError("Copy operation cancelled.")
        
        os.makedirs(dest, exist_ok=True)
        shutil.copystat(src, dest)
        
        entries = os.listdir(src)
        
        for entry in entries:
            src_path = os.path.join(src, entry)
            dest_path = os.path.join(dest, entry)
            
            if os.path.isdir(src_path):
                self._copy_tree(src_path, dest_path, total_size, current_copied, last_update, last_pct)
            else:
                self._copy_file(src_path, dest_path, total_size, current_copied, last_update, last_pct)
                current_copied += os.path.getsize(src_path) # This local update won't affect the caller loop correctly in this simple recursion structure.
                # Ideally, we should pass a mutable object for 'current_copied' or use a class attribute.
                
    # Refactoring to use class attribute for tracking progress across recursion
    
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
