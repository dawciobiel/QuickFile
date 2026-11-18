# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Publish built plugin packages as GitHub Release assets.

Re-running a failed release must be safe: an asset that is already there with
the same bytes is skipped, and an asset with different bytes is an error rather
than a silent replacement. The decision logic lives here so it can be tested
without network access; ``gh`` is only the transport.

Specification: ``docs/architecture/plugins/plugins.md`` ("Publikacja paczek").
"""

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


class PublishError(Exception):
    """Raised when packages cannot be published safely."""


@dataclass(frozen=True)
class Package:
    path: str
    name: str
    size: int
    sha256: str


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
            existing = assets.get(package.name)
            if existing is None:
                actions.append(
                    Action("upload", package.name, "missing from release")
                )
                if not dry_run:
                    gh.upload_asset(tag, package.path)
                continue

            if not _asset_matches(package, existing, gh, tag, scratch):
                raise PublishError(
                    f"Release asset {package.name} differs from {package.path}; "
                    "refusing to replace it."
                )
            actions.append(Action("skip", package.name, "identical"))

    return actions


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
            packages.append(
                Package(path, name, os.path.getsize(path), _hash_file(path))
            )

    if not packages:
        raise PublishError(
            "No .zip packages found in: " + ", ".join(os.fspath(d) for d in package_dirs)
        )
    return packages


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
