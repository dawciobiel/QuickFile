# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Publish built plugin packages as GitHub Release assets.

Re-running a failed release must be safe: an asset that is already there with
the same bytes is skipped, and an asset with different bytes is an error rather
than a silent replacement. The decision logic lives here so it can be tested
without network access; ``gh`` is only the transport.

The release also carries ``plugin-index.json``, generated from the same files
and uploaded last so a client never sees an index pointing at a missing asset.

Specification: ``docs/architecture/plugins/plugins.md`` ("Publikacja paczek").
"""

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

INDEX_NAME = "plugin-index.json"
INDEX_SCHEMA_VERSION = 1
VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")


class PublishError(Exception):
    """Raised when packages cannot be published safely."""


@dataclass(frozen=True)
class Package:
    path: str
    name: str
    size: int
    sha256: str
    plugin_id: str = ""
    version: str = ""


@dataclass(frozen=True)
class Action:
    kind: str
    name: str
    detail: str


class GhClient:
    """Thin wrapper around ``gh release`` commands."""

    def __init__(self, repo: Optional[str] = None, runner=None):
        self.repo = repo
        self._runner = runner or self._run

    def _run(self, args: Sequence[str]) -> str:
        command = ["gh", *args]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "gh failed"
            raise PublishError(f"{' '.join(command)}: {message}")
        return result.stdout

    def _repo_args(self) -> List[str]:
        return ["--repo", self.repo] if self.repo else []

    def release_assets(self, tag: str) -> Dict[str, dict]:
        output = self._runner(
            ["release", "view", tag, *self._repo_args(), "--json", "assets"]
        )
        try:
            data = json.loads(output or "{}")
        except json.JSONDecodeError as error:
            raise PublishError(
                f"Cannot parse the release response for {tag}: {error}"
            ) from error

        return {asset["name"]: asset for asset in data.get("assets") or []}

    def download_asset(self, tag: str, name: str, directory: str) -> str:
        self._runner(
            [
                "release",
                "download",
                tag,
                *self._repo_args(),
                "--pattern",
                name,
                "--dir",
                directory,
                "--clobber",
            ]
        )
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            raise PublishError(
                f"gh did not download the release asset {name} to {directory}."
            )
        return path

    def upload_asset(self, tag: str, path: str) -> None:
        self._runner(["release", "upload", tag, path, *self._repo_args()])

    def create_release(self, tag: str) -> None:
        self._runner(
            [
                "release",
                "create",
                tag,
                *self._repo_args(),
                "--verify-tag",
                "--title",
                tag,
                "--notes",
                f"Plugin packages for {tag}.",
            ]
        )


def publish_packages(
    tag: str,
    package_dirs: Sequence[str],
    gh: GhClient,
    dry_run: bool = False,
    create_release: bool = False,
) -> List[Action]:
    """Upload every missing package; leave identical assets alone."""
    packages = _collect_packages(package_dirs)
    actions: List[Action] = []

    try:
        assets = gh.release_assets(tag)
    except PublishError:
        if not create_release:
            raise
        actions.append(Action("create", tag, "release does not exist"))
        if not dry_run:
            gh.create_release(tag)
        assets = {}

    with tempfile.TemporaryDirectory(prefix="quickfile-publish-") as scratch:
        for package in packages:
            _publish_asset(tag, package, gh, assets, actions, dry_run, scratch)

        _publish_asset(
            tag,
            _write_index(packages, scratch),
            gh,
            assets,
            actions,
            dry_run,
            scratch,
        )

    return actions


def _publish_asset(
    tag: str,
    package: Package,
    gh: GhClient,
    assets: Dict[str, dict],
    actions: List[Action],
    dry_run: bool,
    scratch: str,
) -> None:
    existing = assets.get(package.name)
    if existing is None:
        actions.append(Action("upload", package.name, "missing from release"))
        if not dry_run:
            gh.upload_asset(tag, package.path)
        return

    if not _asset_matches(package, existing, gh, tag, scratch):
        raise PublishError(
            f"Release asset {package.name} differs from {package.path}; "
            "refusing to replace it."
        )
    actions.append(Action("skip", package.name, "identical"))


def _collect_packages(package_dirs: Sequence[str]) -> List[Package]:
    packages = []
    seen = {}

    for directory in package_dirs:
        directory = os.fspath(directory)
        if not os.path.isdir(directory):
            raise PublishError(f"Package directory not found: {directory}")

        for path in sorted(glob.glob(os.path.join(directory, "*.zip"))):
            name = os.path.basename(path)
            if name in seen:
                raise PublishError(
                    f"Duplicate package name {name} in {seen[name]} and {path}."
                )
            seen[name] = path
            plugin_id, version = _read_package_identity(path, name)
            packages.append(
                Package(
                    path,
                    name,
                    os.path.getsize(path),
                    _hash_file(path),
                    plugin_id,
                    version,
                )
            )

    if not packages:
        raise PublishError(
            "No .zip packages found in: " + ", ".join(os.fspath(d) for d in package_dirs)
        )
    return packages


def _read_package_identity(path: str, name: str):
    """Read ``id`` and ``version`` from ``metadata.json`` inside the package."""
    try:
        with zipfile.ZipFile(path) as archive:
            try:
                raw = archive.read("metadata.json")
            except KeyError:
                raise PublishError(
                    f"Package {name} has no metadata.json at its root."
                ) from None
    except (zipfile.BadZipFile, OSError) as error:
        raise PublishError(f"Cannot read package {name}: {error}") from error

    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublishError(f"Invalid metadata.json in {name}: {error}") from error

    plugin_id = metadata.get("id") if isinstance(metadata, dict) else None
    version = metadata.get("version") if isinstance(metadata, dict) else None
    if not isinstance(plugin_id, str) or not plugin_id:
        raise PublishError(f"metadata.json in {name} must define id and version.")
    if not isinstance(version, str) or not version:
        raise PublishError(f"metadata.json in {name} must define id and version.")
    if not VERSION_PATTERN.match(version):
        raise PublishError(
            f"Metadata version {version!r} in {name} is not a valid version."
        )

    artifact_id = plugin_id.rsplit(".", 1)[-1]
    expected = f"{artifact_id}-{version}.zip"
    if name != expected:
        raise PublishError(
            f"Package {name} does not match metadata id {plugin_id!r} and "
            f"version {version!r} (expected {expected})."
        )
    return plugin_id, version


def _write_index(packages: Sequence[Package], scratch: str) -> Package:
    """Render the deterministic index and store it in the scratch directory."""
    entries = [
        {
            "id": package.plugin_id,
            "version": package.version,
            "file": package.name,
            "sha256": package.sha256,
            "size": package.size,
        }
        for package in sorted(
            packages,
            key=lambda item: (item.plugin_id, _version_key(item.version)),
        )
    ]
    content = json.dumps(
        {"schema_version": INDEX_SCHEMA_VERSION, "packages": entries},
        indent=2,
        sort_keys=True,
    )
    path = os.path.join(scratch, INDEX_NAME)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content + "\n")
    return Package(path, INDEX_NAME, os.path.getsize(path), _hash_file(path))


def _version_key(version: str):
    return tuple(map(int, version.split(".")))


def _asset_matches(
    package: Package, asset: dict, gh: GhClient, tag: str, scratch: str
) -> bool:
    size = asset.get("size")
    if size is not None and size != package.size:
        return False

    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1] == package.sha256

    downloaded = gh.download_asset(tag, package.name, scratch)
    return _hash_file(downloaded) == package.sha256


def _hash_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _format_action(action: Action, dry_run: bool) -> str:
    verbs = {
        "create": ("would create release", "created release"),
        "upload": ("would upload", "uploaded"),
        "skip": ("skip", "skip"),
    }
    dry_verb, real_verb = verbs[action.kind]
    verb = dry_verb if dry_run else real_verb
    return f"{verb} {action.name} ({action.detail})"


def main(argv: Optional[List[str]] = None, client: Optional[object] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/publish_plugin_packages.py",
        description="Publish plugin package zips as GitHub Release assets.",
    )
    parser.add_argument("--tag", required=True, help="Existing release tag.")
    parser.add_argument(
        "--packages",
        nargs="+",
        required=True,
        help="Directories containing the built .zip packages.",
    )
    parser.add_argument(
        "--repo", default=None, help="Owner/name; gh infers it when omitted."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without changing the release.",
    )
    parser.add_argument(
        "--create-release",
        action="store_true",
        help="Create the release for an existing tag if it is missing.",
    )
    arguments = parser.parse_args(argv)

    gh = client or GhClient(repo=arguments.repo)
    try:
        actions = publish_packages(
            arguments.tag,
            arguments.packages,
            gh,
            dry_run=arguments.dry_run,
            create_release=arguments.create_release,
        )
    except (PublishError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    for action in actions:
        print(_format_action(action, arguments.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
