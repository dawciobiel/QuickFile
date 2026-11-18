# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Build installable plugin packages.

A package is a zip of one plugin version directory, exactly the layout
``app.plugin_installer`` accepts. Doing this by hand is how a package ends up
with an extra directory level, a ``__pycache__`` tree or a file the installer
will refuse, so the build ends by installing its own output.

Output is deterministic: sorted entries, fixed timestamps and deflate, so two
builds of the same tree are byte-identical.
"""

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.plugin_installer import (  # noqa: E402
    PluginInstallationError,
    install,
)

VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")
EXCLUDED_DIRECTORIES = {"__pycache__", "libs"}
EXCLUDED_SUFFIXES = (".pyc",)
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "dist", "plugins")


class PluginPackageError(Exception):
    """Raised when a plugin tree cannot be turned into a package."""


def build_package(
    plugin_path, output_dir: Optional[str] = None
) -> Path:
    """Build and verify the package for one plugin.

    ``plugin_path`` is a version directory or a plugin directory; the latter
    selects its highest version, like ``PluginManager`` does.
    """
    version_dir = _resolve_version_dir(os.fspath(plugin_path))
    metadata = _read_metadata(version_dir)

    artifact_id = metadata["id"].rsplit(".", 1)[-1]
    version = metadata["version"]
    if os.path.basename(version_dir) != version:
        raise PluginPackageError(
            f"Directory {os.path.basename(version_dir)!r} does not match "
            f"metadata version {version!r}."
        )

    destination = os.path.abspath(output_dir or DEFAULT_OUTPUT)
    os.makedirs(destination, exist_ok=True)
    package_path = Path(destination) / f"{artifact_id}-{version}.zip"

    entries = _collect_entries(version_dir)
    _write_archive(package_path, version_dir, entries)
    _verify_package(package_path)
    return package_path


def _resolve_version_dir(plugin_path: str) -> str:
    if not os.path.isdir(plugin_path):
        raise PluginPackageError(f"Plugin directory not found: {plugin_path}")

    if os.path.isfile(os.path.join(plugin_path, "metadata.json")):
        return plugin_path

    versions = [
        name
        for name in os.listdir(plugin_path)
        if VERSION_PATTERN.match(name)
        and os.path.isfile(os.path.join(plugin_path, name, "metadata.json"))
    ]
    if not versions:
        raise PluginPackageError(
            f"No version directory with metadata.json in {plugin_path}"
        )

    newest = max(versions, key=lambda name: tuple(map(int, name.split("."))))
    return os.path.join(plugin_path, newest)


def _read_metadata(version_dir: str) -> dict:
    metadata_path = os.path.join(version_dir, "metadata.json")
    try:
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise PluginPackageError(
            f"Cannot read metadata.json in {version_dir}: {error}"
        ) from error

    for field in ("id", "version"):
        value = metadata.get(field) if isinstance(metadata, dict) else None
        if not isinstance(value, str) or not value:
            raise PluginPackageError(
                f"metadata.json in {version_dir} must define {field}"
            )
    return metadata


def _collect_entries(root: str) -> List[str]:
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in EXCLUDED_DIRECTORIES
        )
        for filename in sorted(filenames):
            if filename.endswith(EXCLUDED_SUFFIXES):
                continue
            absolute = os.path.join(dirpath, filename)
            entries.append(os.path.relpath(absolute, root))
    return sorted(entries)


def _write_archive(package_path: Path, root: str, entries: List[str]) -> None:
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in entries:
            info = zipfile.ZipInfo(
                relative.replace(os.sep, "/"), date_time=FIXED_TIMESTAMP
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with open(os.path.join(root, relative), "rb") as handle:
                archive.writestr(info, handle.read())


def _verify_package(package_path: Path) -> None:
    """Install the package into a scratch directory, like a user would."""
    with tempfile.TemporaryDirectory() as scratch:
        install_dir = os.path.join(scratch, "plugins")
        os.makedirs(install_dir)
        try:
            install(
                package_path,
                dest=os.path.join(scratch, "plugins-external"),
                install_dir=install_dir,
            )
        except PluginInstallationError as error:
            raise PluginPackageError(
                f"{package_path.name} failed installer validation: {error}"
            ) from error


def _plugin_directories(source_root: str) -> List[str]:
    if not os.path.isdir(source_root):
        raise PluginPackageError(f"Plugin source root not found: {source_root}")

    directories = []
    for group_id in sorted(os.listdir(source_root)):
        group_path = os.path.join(source_root, group_id)
        if not os.path.isdir(group_path) or group_id.startswith("__"):
            continue
        for artifact_id in sorted(os.listdir(group_path)):
            plugin_path = os.path.join(group_path, artifact_id)
            if os.path.isdir(plugin_path):
                directories.append(plugin_path)
    return directories


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/build_plugin_package.py",
        description="Build installable packages for QuickFile plugins.",
    )
    parser.add_argument(
        "plugin",
        nargs="?",
        help="Plugin directory or version directory to package.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Package every plugin under --source-root.",
    )
    parser.add_argument(
        "--source-root",
        default=os.path.join(PROJECT_ROOT, "plugins"),
        help="Root scanned by --all (default: plugins/).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"Output directory (default: {DEFAULT_OUTPUT}).",
    )
    arguments = parser.parse_args(argv)

    if not arguments.all and not arguments.plugin:
        parser.error("provide a plugin directory or use --all")

    try:
        if arguments.all:
            paths = _plugin_directories(arguments.source_root)
            packages = [
                build_package(path, arguments.output) for path in paths
            ]
        else:
            packages = [build_package(arguments.plugin, arguments.output)]
    except (PluginPackageError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    for package in packages:
        print(package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
