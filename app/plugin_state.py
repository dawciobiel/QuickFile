# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Enabled/disabled state of external plugins.

The state is stored in the filesystem: a disabled plugin keeps its directory
and versions, but the artifact directory gains a ``.disabled`` suffix. The
loader skips that suffix, so no version of a disabled plugin is imported, and
enabling it again is just a rename back. Nothing is deleted and settings are
keyed by plugin id, so a plugin keeps its settings across disable/enable.

Specification: ``docs/architecture/plugins/plugins.md``
("Zarządzanie wtyczkami zewnętrznymi").
"""

import json
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.plugin_installer import default_destination, default_install_dir
from app.translation_manager import translation_manager

DISABLED_SUFFIX = ".disabled"
VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")


class PluginStateError(Exception):
    """Raised when a plugin cannot be scanned, disabled or enabled safely."""


@dataclass(frozen=True)
class ExternalPlugin:
    plugin_id: str
    version: str
    path: str
    enabled: bool
    versions: Tuple[str, ...]


def scan_external_plugins(
    destination: Optional[str] = None,
    include_disabled: bool = True,
) -> List[ExternalPlugin]:
    """Return external plugins sorted by id, optionally including disabled ones."""
    root = os.path.abspath(os.fspath(destination or default_destination()))
    if not os.path.isdir(root):
        return []

    found = {}
    for group_id in sorted(os.listdir(root)):
        group_path = os.path.join(root, group_id)
        if group_id.startswith("__") or not os.path.isdir(group_path):
            continue

        for entry in sorted(os.listdir(group_path)):
            path = os.path.join(group_path, entry)
            if not os.path.isdir(path):
                continue
            enabled = not entry.endswith(DISABLED_SUFFIX)
            if not enabled and not include_disabled:
                continue

            versions = _version_directories(path)
            if not versions:
                continue
            plugin_id = _read_plugin_id(os.path.join(path, versions[0]))
            if plugin_id is None:
                continue
            if plugin_id in found:
                raise PluginStateError(
                    translation_manager.translate(
                        "PluginState", "Plugin {id} is installed in more than one directory; resolve the duplicate first."
                    ).format(id=plugin_id)
                )
            found[plugin_id] = ExternalPlugin(
                plugin_id, versions[0], path, enabled, tuple(versions)
            )

    return sorted(found.values(), key=lambda plugin: plugin.plugin_id)


def disable_plugin(
    plugin_id: str,
    destination: Optional[str] = None,
    install_dir: Optional[str] = None,
) -> ExternalPlugin:
    """Disable every version of one external plugin by renaming its directory."""
    root = os.path.abspath(os.fspath(destination or default_destination()))
    shipped_root = os.path.abspath(os.fspath(install_dir or default_install_dir()))

    if is_shipped(plugin_id, shipped_root):
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "Plugin {id} is shipped with QuickFile and cannot be disabled here."
            ).format(id=plugin_id)
        )

    current = _find_plugin(root, plugin_id)
    if current is None:
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "Plugin {id} is not installed in {root}."
            ).format(id=plugin_id, root=root)
        )
    if not current.enabled:
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "Plugin {id} is already disabled."
            ).format(id=plugin_id)
        )

    target = current.path + DISABLED_SUFFIX
    if os.path.exists(target):
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "{target} already exists; refusing to overwrite it."
            ).format(target=target)
        )

    os.rename(current.path, target)
    return ExternalPlugin(
        current.plugin_id,
        current.version,
        target,
        False,
        current.versions,
    )


def enable_plugin(
    plugin_id: str,
    destination: Optional[str] = None,
    install_dir: Optional[str] = None,
) -> ExternalPlugin:
    """Re-enable one external plugin by removing the ``.disabled`` suffix."""
    root = os.path.abspath(os.fspath(destination or default_destination()))
    shipped_root = os.path.abspath(os.fspath(install_dir or default_install_dir()))

    if is_shipped(plugin_id, shipped_root):
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "Plugin {id} is shipped with QuickFile and cannot be enabled here."
            ).format(id=plugin_id)
        )

    current = _find_plugin(root, plugin_id)
    if current is None:
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "Plugin {id} is not installed in {root}."
            ).format(id=plugin_id, root=root)
        )
    if current.enabled:
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "Plugin {id} is already enabled."
            ).format(id=plugin_id)
        )

    target = current.path[: -len(DISABLED_SUFFIX)]
    if os.path.exists(target):
        raise PluginStateError(
            translation_manager.translate(
                "PluginState", "{target} already exists; refusing to overwrite it."
            ).format(target=target)
        )

    os.rename(current.path, target)
    return ExternalPlugin(
        current.plugin_id,
        current.version,
        target,
        True,
        current.versions,
    )


def is_shipped(plugin_id: str, install_dir: str) -> bool:
    """Whether the application ships a plugin with this id."""
    group_id, _, artifact_id = plugin_id.rpartition(".")
    return bool(group_id) and os.path.isdir(
        os.path.join(install_dir, group_id, artifact_id)
    )


def _find_plugin(root: str, plugin_id: str) -> Optional[ExternalPlugin]:
    for plugin in scan_external_plugins(root, include_disabled=True):
        if plugin.plugin_id == plugin_id:
            return plugin
    return None


def _version_directories(plugin_path: str) -> List[str]:
    versions = [
        name
        for name in os.listdir(plugin_path)
        if VERSION_PATTERN.match(name)
        and os.path.isdir(os.path.join(plugin_path, name))
    ]
    versions.sort(key=_version_key, reverse=True)
    return versions


def _read_plugin_id(version_path: str) -> Optional[str]:
    metadata_path = os.path.join(version_path, "metadata.json")
    try:
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    plugin_id = metadata.get("id") if isinstance(metadata, dict) else None
    return plugin_id if isinstance(plugin_id, str) and plugin_id else None


def _version_key(version: str):
    return tuple(map(int, version.split(".")))
