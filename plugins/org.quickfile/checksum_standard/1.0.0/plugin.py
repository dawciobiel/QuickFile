# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginTask, TaskPlugin
from tasks import ChecksumTask


class ChecksumPlugin(TaskPlugin):
    SUPPORTED_ALGORITHMS = ["crc32", "md5", "sha1", "sha256"]

    def get_name(self):
        return "Standard Checksum Calculator"

    def get_description(self):
        return "Calculates CRC32, MD5, SHA1, and SHA256 checksums for files."

    def get_supported_algorithms(self):
        return self.SUPPORTED_ALGORITHMS

    def create_task(self, action_id: str, **kwargs) -> PluginTask:
        if action_id == "calculate_checksum":
            return ChecksumTask(kwargs['source_paths'][0], kwargs['algorithms'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
