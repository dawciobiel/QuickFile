# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from app.plugin_system.api import PluginBase, AbstractTask
from tasks import SplitFileTask, JoinFilesTask

class FileSplitterPlugin(PluginBase):
    def get_name(self):
        return "File Splitter"

    def get_description(self):
        return "Splits large files into smaller parts and joins them back."

    def get_menu_actions(self):
        return [
            {
                "text": "Split File...",
                "menu": "file",
                "action_id": "split_file",
                "dialog_module": "ui.split_join_dialogs",
                "dialog_class": "SplitDialog",
                "task_type": "SPLIT_FILE"
            },
            {
                "text": "Join Files...",
                "menu": "file",
                "action_id": "join_files",
                "dialog_module": "ui.split_join_dialogs",
                "dialog_class": "JoinDialog",
                "task_type": "JOIN_FILES"
            }
        ]

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "split_file":
            return SplitFileTask(kwargs['source_paths'][0], kwargs['destination_path'], kwargs['options'])
        elif action_id == "join_files":
            return JoinFilesTask(kwargs['source_paths'][0], kwargs['destination_path'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
