# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from quickfile.app.plugin_system.api import PluginBase, AbstractTask
from .tasks import CopyTask

class CopyOperationPlugin(PluginBase):
    def get_name(self):
        return "Standard Copy Operation"

    def get_description(self):
        return "Provides standard file copy functionality."

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "copy_items":
            return CopyTask(kwargs['source_paths'], kwargs['destination_path'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
