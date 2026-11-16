# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginTask, TaskPlugin
from tasks import SearchTask

class SearchPlugin(TaskPlugin):
    def get_name(self):
        return "Standard Search"

    def get_description(self):
        return "Provides file search functionality."

    def create_task(self, action_id: str, **kwargs) -> PluginTask:
        if action_id == "search":
            return SearchTask(kwargs['start_path'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
