# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import glob
import json
import os
from typing import Iterator, List, Tuple

from packaging import version

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

#: Source trees in the repository. ``plugins/`` ships with the application and
#: is copied into the user directory at startup; ``plugins-external/`` only
#: produces packages and never reaches the runtime. Order matters: the shipped
#: copy wins, exactly like ``PluginManager`` ignores an external id collision.
REPOSITORY_PLUGIN_ROOTS = ('plugins', 'plugins-external')


def plugin_source_roots(project_root: str = None) -> List[str]:
    """Return the plugin source trees that exist in the repository."""
    root = project_root or PROJECT_ROOT
    return [
        os.path.join(root, name)
        for name in REPOSITORY_PLUGIN_ROOTS
        if os.path.isdir(os.path.join(root, name))
    ]


def iter_plugin_version_paths(
    plugin_group: str = 'org.quickfile', project_root: str = None
) -> Iterator[Tuple[str, str, str]]:
    """Yield ``(plugin_name, version_dir_name, metadata_path)`` for every source.

    A plugin found in ``plugins/`` hides the copy in ``plugins-external/``:
    that is what the runtime does with a duplicate id, and tests must check the
    code users actually load.
    """
    seen = set()
    for source_root in plugin_source_roots(project_root):
        group_dir = os.path.join(source_root, plugin_group)
        for metadata_path in sorted(
            glob.glob(os.path.join(group_dir, '*', '*', 'metadata.json'))
        ):
            version_dir_name = os.path.basename(os.path.dirname(metadata_path))
            plugin_name = os.path.basename(
                os.path.dirname(os.path.dirname(metadata_path))
            )
            if plugin_name in seen:
                continue
            seen.add(plugin_name)
            yield plugin_name, version_dir_name, metadata_path


def iter_plugin_metadata(
    plugin_group: str = 'org.quickfile', project_root: str = None
) -> Iterator[Tuple[str, dict]]:
    """Yield ``(metadata_path, metadata)`` for every plugin source, deduplicated by id."""
    seen = set()
    for _name, _version, metadata_path in iter_plugin_version_paths(
        plugin_group, project_root
    ):
        with open(metadata_path, encoding='utf-8') as handle:
            metadata = json.load(handle)
        if metadata['id'] in seen:
            continue
        seen.add(metadata['id'])
        yield metadata_path, metadata


def get_latest_plugin_path(plugin_group: str, plugin_name: str) -> str:
    """
    Finds the path to the latest version of a given plugin.

    Searches the shipped tree first, then the external source tree.

    Args:
        plugin_group: The group of the plugin (e.g., 'org.quickfile').
        plugin_name: The name of the plugin (e.g., 'file_splitter').

    Returns:
        The absolute path to the latest version directory of the plugin.
    """
    try:
        plugin_base_dir = None
        for source_root in plugin_source_roots():
            candidate = os.path.join(source_root, plugin_group, plugin_name)
            if os.path.isdir(candidate):
                plugin_base_dir = candidate
                break

        if plugin_base_dir is None:
            raise FileNotFoundError(
                f"Plugin base directory not found for: {plugin_group}.{plugin_name}"
            )

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
