# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Offline installation of external plugins.

A package is a zip of one plugin version directory, or that directory itself.
The archive carries no ``groupId/artifactId`` path: metadata names the plugin,
so the destination is derived instead of trusted.

Everything is validated before the result is moved into place. Refusing is the
normal answer for collisions: the loader ignores a copy of an already shipped
id, and silently replacing a version would hide what changed.

Nothing here touches the network or installs Python dependencies; that stays a
separate, explicit action (``PluginDependencyManager.install_dependencies``).
"""

import argparse
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.external_tools import ExternalToolsError, requirements_for
from app.plugin_dependency_manager import PluginDependencyManager
from app.plugin_settings import PluginSettingsError, validate_schema

VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")
IGNORED_DIRECTORIES = {"__pycache__"}
IGNORED_SUFFIXES = (".pyc",)


class PluginInstallationError(Exception):
    """Raised when a package cannot be installed safely."""


@dataclass(frozen=True)
class InstalledPlugin:
    plugin_id: str
    version: str
    path: str
    warnings: Tuple[str, ...] = ()


def default_destination() -> str:
    return os.path.join(os.path.expanduser("~/.config/QuickFile"), "plugins-external")


def default_install_dir() -> str:
    return os.path.join(os.path.expanduser("~/.config/QuickFile"), "plugins")


def install(
    source,
    dest: Optional[str] = None,
    install_dir: Optional[str] = None,
    dependency_manager: Optional[PluginDependencyManager] = None,
) -> InstalledPlugin:
    """Install one plugin package into ``dest``.

    ``install_dir`` is only read, never written: it tells the installer which
    plugins already ship with the application.
    """
    source = os.fspath(source)
    destination_root = os.path.abspath(dest or default_destination())
    shipped_root = os.path.abspath(install_dir or default_install_dir())

    if not os.path.exists(source):
        raise PluginInstallationError(f"Package not found: {source}")

    os.makedirs(destination_root, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".install-", dir=destination_root)
    try:
        package_root = _materialise(source, os.path.join(staging, "package"))
        metadata = _read_metadata(package_root)
        plugin_id, version = _validate_metadata(package_root, metadata)
        group_id, artifact_id = _split_plugin_id(plugin_id)
        target = os.path.join(
            destination_root, group_id, artifact_id, version
        )

        _refuse_collisions(target, plugin_id, shipped_root)
        warnings = _dependency_warnings(
            package_root, metadata, dependency_manager
        )

        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.replace(package_root, target)
        return InstalledPlugin(plugin_id, version, target, tuple(warnings))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _materialise(source: str, target: str) -> str:
    """Copy or extract ``source`` into ``target`` and return the plugin root."""
    if os.path.isdir(source):
        _copy_tree(source, target)
    else:
        _extract_archive(source, target)
    return _locate_plugin_root(target)


def _copy_tree(source: str, target: str) -> None:
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRECTORIES]
        relative = os.path.relpath(dirpath, source)
        destination_dir = target if relative == "." else os.path.join(target, relative)
        os.makedirs(destination_dir, exist_ok=True)

        for filename in filenames:
            if filename.endswith(IGNORED_SUFFIXES):
                continue
            shutil.copy2(
                os.path.join(dirpath, filename),
                os.path.join(destination_dir, filename),
            )


def _extract_archive(archive_path: str, target: str) -> None:
    try:
        archive = zipfile.ZipFile(archive_path)
    except (zipfile.BadZipFile, OSError) as error:
        raise PluginInstallationError(
            f"{archive_path} is not a readable zip archive: {error}"
        ) from error

    with archive:
        for info in archive.infolist():
            _validate_member(info)
            if info.is_dir():
                continue
            relative = _safe_relative_path(info.filename)
            if relative is None:
                continue

            destination = os.path.join(target, relative)
            os.makedirs(os.path.dirname(destination) or target, exist_ok=True)
            with archive.open(info) as source, open(destination, "wb") as output:
                shutil.copyfileobj(source, output)


def _validate_member(info: zipfile.ZipInfo) -> None:
    mode = info.external_attr >> 16
    if mode and stat.S_ISLNK(mode):
        raise PluginInstallationError(
            f"Package contains a symlink ({info.filename}); symlinks are not allowed."
        )


def _safe_relative_path(name: str) -> Optional[str]:
    """Reject escaping paths; return ``None`` for entries to skip."""
    if "\\" in name or ":" in name.split("/")[0]:
        raise PluginInstallationError(
            f"Package contains an invalid path: {name!r}"
        )

    parts = name.split("/")
    if name.startswith("/") or ".." in parts:
        raise PluginInstallationError(
            f"Package contains a path outside the plugin directory: {name!r}"
        )

    parts = [part for part in parts if part not in ("", ".")]
    if not parts:
        return None
    if parts[0] in IGNORED_DIRECTORIES or parts[-1].endswith(IGNORED_SUFFIXES):
        return None
    return os.path.join(*parts)


def _locate_plugin_root(base: str) -> str:
    roots = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRECTORIES]
        if "metadata.json" in filenames:
            roots.append(dirpath)

    if len(roots) != 1:
        raise PluginInstallationError(
            "Package must contain exactly one metadata.json, "
            f"found {len(roots)}."
        )

    root = roots[0]
    relative = os.path.relpath(root, base)
    if relative == ".":
        return root

    wrapper = relative.split(os.sep)
    if len(wrapper) != 1:
        raise PluginInstallationError(
            "metadata.json must be at the package root or in a single "
            "top-level directory."
        )

    extra = set(os.listdir(base)) - IGNORED_DIRECTORIES - {wrapper[0]}
    if extra:
        raise PluginInstallationError(
            "Package has entries outside the plugin directory: "
            + ", ".join(sorted(extra))
        )
    return root


def _read_metadata(package_root: str) -> dict:
    metadata_path = os.path.join(package_root, "metadata.json")
    try:
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise PluginInstallationError(
            f"Cannot read metadata.json: {error}"
        ) from error

    if not isinstance(metadata, dict):
        raise PluginInstallationError("metadata.json must contain an object.")
    return metadata


def _validate_metadata(package_root: str, metadata: dict) -> Tuple[str, str]:
    plugin_id = _require_string(metadata, "id")
    if "." not in plugin_id:
        raise PluginInstallationError(
            f"Plugin id {plugin_id!r} must look like 'org.example.plugin'."
        )

    version = _require_string(metadata, "version")
    if not VERSION_PATTERN.match(version):
        raise PluginInstallationError(
            f"Invalid plugin version {version!r}; expected digits and dots."
        )

    _require_string(metadata, "type")

    entry_point = _require_string(metadata, "entry_point")
    module_name, separator, class_name = entry_point.partition(":")
    if not separator or not module_name or not class_name:
        raise PluginInstallationError(
            f"Invalid entry_point {entry_point!r}; expected 'module:Class'."
        )
    if not os.path.isfile(os.path.join(package_root, module_name + ".py")):
        raise PluginInstallationError(
            f"entry_point module {module_name!r} is missing from the package."
        )

    group_id, artifact_id = _split_plugin_id(plugin_id)
    declared_group = metadata.get("group_id")
    if declared_group is not None and declared_group != group_id:
        raise PluginInstallationError(
            f"group_id {declared_group!r} does not match id {plugin_id!r}."
        )
    declared_artifact = metadata.get("artifact_id")
    if declared_artifact is not None and declared_artifact != artifact_id:
        raise PluginInstallationError(
            f"artifact_id {declared_artifact!r} does not match id {plugin_id!r}."
        )

    schema = (metadata.get("settings") or {}).get("schema")
    if schema is not None:
        try:
            validate_schema(schema)
        except PluginSettingsError as error:
            raise PluginInstallationError(
                f"Invalid settings schema: {error}"
            ) from error

    try:
        requirements_for(metadata)
    except ExternalToolsError as error:
        raise PluginInstallationError(
            f"Invalid external_tools declaration: {error}"
        ) from error

    return plugin_id, version


def _require_string(metadata: dict, field: str) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PluginInstallationError(
            f"metadata.json must define a non-empty {field}."
        )
    return value


def _split_plugin_id(plugin_id: str) -> Tuple[str, str]:
    group_id, _, artifact_id = plugin_id.rpartition(".")
    return group_id, artifact_id


def _refuse_collisions(target: str, plugin_id: str, shipped_root: str) -> None:
    group_id, artifact_id = _split_plugin_id(plugin_id)
    shipped_path = os.path.join(shipped_root, group_id, artifact_id)
    if os.path.isdir(shipped_path):
        raise PluginInstallationError(
            f"Plugin {plugin_id} is shipped with QuickFile; an installed copy "
            "would be ignored. Remove it from the release first."
        )

    if os.path.exists(target):
        raise PluginInstallationError(
            f"Version {os.path.basename(target)} of {plugin_id} is already "
            f"installed at {target}; refusing to overwrite."
        )


def _dependency_warnings(
    package_root: str,
    metadata: dict,
    manager: Optional[PluginDependencyManager],
) -> List[str]:
    manager = manager or PluginDependencyManager()
    status = manager.check_dependencies(package_root, metadata)

    try:
        manager.validate_isolation(status, metadata)
    except ValueError as error:
        raise PluginInstallationError(str(error)) from error

    if status.satisfied:
        return []
    return [
        "missing Python dependencies: "
        + ", ".join(status.missing)
        + ". Install them explicitly with the plugin's offline wheels."
    ]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.plugin_installer",
        description="Install an external QuickFile plugin from an archive.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    install_parser = commands.add_parser(
        "install", help="Install a plugin package (zip or directory)."
    )
    install_parser.add_argument("source")
    install_parser.add_argument(
        "--dest", default=None, help="External plugin directory."
    )
    install_parser.add_argument(
        "--install-dir",
        dest="install_dir",
        default=None,
        help="Directory of plugins shipped with the application (read only).",
    )

    arguments = parser.parse_args(argv)

    try:
        result = install(
            arguments.source,
            dest=arguments.dest,
            install_dir=arguments.install_dir,
        )
    except (PluginInstallationError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(result.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
