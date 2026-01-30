# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginBase, AbstractTask
from tasks import ExtractRarTask

class RarArchiverPlugin(PluginBase):
    @property
    def name(self):
        return "RAR Archiver"

    @property
    def description(self):
        return "Extracts RAR archives."

    def get_supported_extensions(self):
        return [".rar"]

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "extract_archive":
            return ExtractRarTask(kwargs['source_path'], kwargs['dest_dir'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
