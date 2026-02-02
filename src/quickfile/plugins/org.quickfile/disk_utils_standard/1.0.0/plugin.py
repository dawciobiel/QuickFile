# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import shutil
from quickfile.plugins.base import DiskUtilsPlugin

class StandardDiskUtilsPlugin(DiskUtilsPlugin):
    def get_name(self) -> str:
        return "Standard Disk Utils"

    def get_description(self) -> str:
        return "Provides standard disk utility functions using Python's shutil module."

    def get_disk_usage(self, path: str) -> tuple[int, int, int] | None:
        try:
            usage = shutil.disk_usage(path)
            return usage.total, usage.used, usage.free
        except Exception:
            return None
