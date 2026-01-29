# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import shutil
import time
from app.plugin_system.api import AbstractTask

class DeleteTask(AbstractTask):
    def __init__(self, item_paths, options):
        super().__init__()
        self.item_paths = item_paths
        self.options = options
        self.total_items = 0
        self.deleted_items = 0
        self.last_progress_update = 0
        self.last_pct = -1

    def run(self):
        # Phase 1: Count items
        for path in self.item_paths:
            if self.context.is_cancelled():
                raise InterruptedError("Delete operation cancelled.")
            self.context.wait_if_paused()
            
            if os.path.exists(path):
                self.total_items += 1
                if os.path.isdir(path):
                    for _, dirs, files in os.walk(path):
                        if self.context.is_cancelled():
                            raise InterruptedError("Delete operation cancelled.")
                        self.total_items += len(dirs) + len(files)

        # Phase 2: Delete items
        for path in self.item_paths:
            if self.context.is_cancelled():
                raise InterruptedError("Delete operation cancelled.")
            self.context.wait_if_paused()
            
            if os.path.exists(path):
                if os.path.isdir(path):
                    self._delete_tree(path)
                else:
                    os.remove(path)
                    self._update_progress()

    def _delete_tree(self, path):
        if self.context.is_cancelled():
            raise InterruptedError("Delete operation cancelled.")
        
        # We need to walk bottom-up to delete files before directories
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                if self.context.is_cancelled():
                    raise InterruptedError("Delete operation cancelled.")
                self.context.wait_if_paused()
                
                os.remove(os.path.join(root, name))
                self._update_progress()
            
            for name in dirs:
                if self.context.is_cancelled():
                    raise InterruptedError("Delete operation cancelled.")
                self.context.wait_if_paused()
                
                os.rmdir(os.path.join(root, name))
                self._update_progress()
        
        # Finally remove the root directory itself
        if os.path.exists(path):
            os.rmdir(path)
            self._update_progress()

    def _update_progress(self):
        self.deleted_items += 1
        if self.total_items > 0:
            pct = int(self.deleted_items * 100 / self.total_items)
            if pct != self.last_pct and (time.time() - self.last_progress_update > 0.1):
                self.emit_progress(pct)
                self.last_pct = pct
                self.last_progress_update = time.time()
