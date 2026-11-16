# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import zipfile

from app.plugin_system.api import AbstractTask


class CreateZipTask(AbstractTask):
    def __init__(self, source_paths, destination_path, options):
        super().__init__()
        self.source_paths = source_paths
        self.destination_path = destination_path
        self.options = options
        self.total_files = 0
        self.processed_files = 0
        self.last_progress_update = 0
        self.last_pct = -1

    def run(self):
        compression = self.options.get("compression", zipfile.ZIP_DEFLATED)
        compresslevel = self.options.get("compresslevel", -1)

        # Phase 1: Count files for progress reporting
        for src_path in self.source_paths:
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    self.total_files += len(files)
            else:
                self.total_files += 1

        # Phase 2: Create archive
        with zipfile.ZipFile(self.destination_path, 'w', compression=compression, compresslevel=compresslevel) as zipf:
            for src_path in self.source_paths:
                if self.context.is_cancelled():
                    raise InterruptedError("Archive creation cancelled.")

                if os.path.isdir(src_path):
                    base_dir = os.path.dirname(src_path)
                    for root, _, files in os.walk(src_path):
                        for file in files:
                            if self.context.is_cancelled():
                                raise InterruptedError("Archive creation cancelled.")
                            self.context.wait_if_paused()

                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, base_dir)
                            zipf.write(file_path, arcname)
                            self._update_progress()
                else:  # It's a file
                    if self.context.is_cancelled():
                        raise InterruptedError("Archive creation cancelled.")
                    self.context.wait_if_paused()

                    arcname = os.path.basename(src_path)
                    zipf.write(src_path, arcname)
                    self._update_progress()

        return {"archive_path": self.destination_path}

    def _update_progress(self):
        self.processed_files += 1
        if self.total_files > 0:
            pct = int(self.processed_files * 100 / self.total_files)
            if pct != self.last_pct:
                self.emit_progress(pct)
                self.last_pct = pct
