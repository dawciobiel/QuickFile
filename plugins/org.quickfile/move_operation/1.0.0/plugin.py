# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginBase, AbstractTask
from tasks import MoveTask

class MoveOperationPlugin(PluginBase):
    @property
    def name(self):
        return "Standard Move Operation"

    @property
    def description(self):
        return "Provides standard file move functionality."

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "move_items":
            return MoveTask(kwargs['source_paths'], kwargs['destination_path'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
