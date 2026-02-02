# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from quickfile.app.plugin_system.api import PluginBase, AbstractTask
from tasks import CreateZipTask


class ZipArchiverPlugin(PluginBase):
    def get_name(self):
        return "ZIP Archiver"

    def get_description(self):
        return "Creates ZIP archives."

    def get_supported_extensions(self):
        """Returns a list of supported archive extensions."""
        return ["zip"]

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        if action_id == "create_archive":
            return CreateZipTask(kwargs['source_paths'], kwargs['destination_path'], kwargs['options'])
        else:
            raise ValueError(f"Unknown action_id: {action_id}")
