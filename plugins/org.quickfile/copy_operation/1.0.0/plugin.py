# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginBase, AbstractTask
from tasks import CopyTask # Zmieniono import na bezpośredni

class CopyOperationPlugin(PluginBase):
    @property
    def name(self):
        return "Standard Copy Operation"

    @property
    def description(self):
        return "Provides standard file copy functionality."

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "copy_items":
            return CopyTask(kwargs['source_paths'], kwargs['destination_path'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
