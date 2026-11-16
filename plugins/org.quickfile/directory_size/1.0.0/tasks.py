# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os

from app.plugin_system.api import PluginTask


class DirectorySizeTask(PluginTask):
    """Walks a directory twice: once to count files, once to sum their sizes.

    The first pass makes the progress report meaningful; the second one sums
    sizes and checks for cancellation between files, so a huge tree stops
    promptly. Symlinks are skipped, matching the previous in-process scan.
    """

    def __init__(self, directory_path):
        self.directory_path = directory_path

    def run(self, ctx):
        total_files = 0
        for _dirpath, _dirnames, filenames in os.walk(self.directory_path):
            ctx.check_cancelled()
            total_files += len(filenames)

        total_size = 0
        processed_files = 0
        for dirpath, _dirnames, filenames in os.walk(self.directory_path):
            ctx.check_cancelled()
            for name in filenames:
                ctx.check_cancelled()

                path = os.path.join(dirpath, name)
                if not os.path.islink(path):
                    try:
                        total_size += os.path.getsize(path)
                    except OSError as error:
                        ctx.log("warning", f"Could not get size of {path}: {error}")

                processed_files += 1
                if total_files:
                    ctx.progress(int(processed_files * 100 / total_files))

        ctx.progress(100)
        return total_size
