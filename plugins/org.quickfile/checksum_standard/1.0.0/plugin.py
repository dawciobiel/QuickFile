# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginBase, AbstractTask
from tasks import ChecksumTask

class ChecksumPlugin(PluginBase):
    SUPPORTED_ALGORITHMS = ["crc32", "md5", "sha1", "sha256"]

    @property
    def name(self):
        return "Standard Checksum Calculator"

    @property
    def description(self):
        return "Calculates CRC32, MD5, SHA1, and SHA256 checksums for files."

    def get_supported_algorithms(self):
        return self.SUPPORTED_ALGORITHMS

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "calculate_checksum":
            return ChecksumTask(kwargs['file_path'], kwargs['algorithms'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
