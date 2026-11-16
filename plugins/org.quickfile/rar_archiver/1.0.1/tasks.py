# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import rarfile
from app.plugin_system.api import PluginTask

class ExtractRarTask(PluginTask):
    def __init__(self, source_path, dest_dir, options):
        self.source_path = source_path
        self.dest_dir = dest_dir
        self.options = options
        self.total_files = 0
        self.processed_files = 0
        self.last_progress_update = 0
        self.last_pct = -1

    def run(self, ctx):
        if not os.path.exists(self.dest_dir):
            os.makedirs(self.dest_dir)

        with rarfile.RarFile(self.source_path) as rf:
            self.total_files = len(rf.infolist())

            for member in rf.infolist():
                ctx.check_cancelled()
                ctx.wait_if_paused()

                rf.extract(member, self.dest_dir)
                self._update_progress(ctx)
        
        return {"extract_path": self.dest_dir}

    def _update_progress(self, ctx):
        self.processed_files += 1
        if self.total_files > 0:
            pct = int(self.processed_files * 100 / self.total_files)
            if pct != self.last_pct:
                ctx.progress(pct)
                self.last_pct = pct
