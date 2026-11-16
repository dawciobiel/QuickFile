# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginTask, TaskPlugin
from tasks import DirectorySizeTask


class DirectorySizePlugin(TaskPlugin):
    """Measures a directory; replaceable by another implementation per action."""

    def get_name(self):
        return "Directory Size"

    def get_description(self):
        return "Calculates the total size of a directory and its subdirectories."

    def get_menu_actions(self):
        return [{"action_id": "calculate_directory_size"}]

    def create_task(self, action_id: str, **kwargs) -> PluginTask:
        if action_id != "calculate_directory_size":
            raise ValueError(f"Unknown action_id: {action_id}")

        source_paths = kwargs.get("source_paths") or []
        if not source_paths:
            raise ValueError("calculate_directory_size requires source_paths")
        return DirectorySizeTask(source_paths[0])
