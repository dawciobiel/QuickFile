# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import fnmatch
from quickfile.app.plugin_system.api import AbstractTask

class SearchTask(AbstractTask):
    def __init__(self, start_path, options):
        super().__init__()
        self.start_path = start_path
        self.options = options
        self.file_name_pattern = options.get("file_name", "*")
        self.case_sensitive = options.get("case_sensitive", False)
        self.include_hidden = options.get("include_hidden", True)
        self.exclude_paths = options.get("exclude_paths", [])

    def run(self):
        self.emit_event("log", {"message": "Search task started."})
        
        if not self.case_sensitive:
            self.file_name_pattern = self.file_name_pattern.lower()

        for root, dirs, files in os.walk(self.start_path, topdown=True):
            if self.context.is_cancelled():
                self.emit_event("log", {"message": "Search cancelled during directory walk."})
                raise InterruptedError("Search operation cancelled.")
            self.context.wait_if_paused()

            # Filter directories
            if not self.include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # Filter out excluded paths
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in self.exclude_paths]

            # Process files
            for file in files:
                if self.context.is_cancelled():
                    self.emit_event("log", {"message": "Search cancelled during file walk."})
                    raise InterruptedError("Search operation cancelled.")
                
                file_to_match = file if self.case_sensitive else file.lower()
                
                if fnmatch.fnmatch(file_to_match, self.file_name_pattern):
                    full_path = os.path.join(root, file)
                    self.emit_event("item_found", {"path": full_path})
        
        self.emit_event("log", {"message": "Search task finished."})
        return "Search complete" # Jawny return
