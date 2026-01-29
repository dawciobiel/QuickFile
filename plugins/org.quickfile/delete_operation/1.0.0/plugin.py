# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginBase, AbstractTask
from tasks import DeleteTask

class DeleteOperationPlugin(PluginBase):
    @property
    def name(self):
        return "Standard Delete Operation"

    @property
    def description(self):
        return "Provides standard file delete functionality."

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "delete_items":
            return DeleteTask(kwargs['item_paths'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
