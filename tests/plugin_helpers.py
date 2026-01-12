# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
from packaging import version

def get_latest_plugin_path(plugin_group: str, plugin_name: str) -> str:
    """
    Finds the path to the latest version of a given plugin.

    Args:
        plugin_group: The group of the plugin (e.g., 'org.quickfile').
        plugin_name: The name of the plugin (e.g., 'file_splitter').

    Returns:
        The absolute path to the latest version directory of the plugin.
    """
    try:
        # Go up two levels from the current file's directory (tests/) to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        plugin_base_dir = os.path.join(project_root, 'plugins', plugin_group, plugin_name)

        if not os.path.isdir(plugin_base_dir):
            raise FileNotFoundError(f"Plugin base directory not found: {plugin_base_dir}")

        versions = [
            d for d in os.listdir(plugin_base_dir)
            if os.path.isdir(os.path.join(plugin_base_dir, d))
            and d[0].isdigit()  # Basic check to avoid directories like '__pycache__'
        ]

        if not versions:
            raise FileNotFoundError(f"No version directories found for plugin: {plugin_name}")

        # Sort versions using the packaging library to correctly handle semantic versioning
        latest_version = sorted(versions, key=version.Version, reverse=True)[0]

        return os.path.join(plugin_base_dir, latest_version)
    except Exception as e:
        # Provide more context in case of an error
        raise RuntimeError(f"Failed to get latest path for plugin '{plugin_name}': {e}") from e
