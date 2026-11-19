# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Explicit updates for external plugins.

The feed (``plugin-index.json``) names the available versions and their
integrity data. Nothing is checked in the background: ``check`` only reports,
and ``update`` downloads into a temporary directory, verifies size and SHA-256,
then hands the file to ``app.plugin_installer``. The previous version is left
in place, so ``rollback`` can disable the newest one without any network
access.

Specification: ``docs/architecture/plugins/plugins.md``
("Aktualizacja wtyczki zewnętrznej").
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse
from urllib.request import url2pathname

from app.plugin_installer import (
    PluginInstallationError,
    default_destination,
    default_install_dir,
    install as install_plugin,
)
from app.plugin_state import (
    ExternalPlugin,
    PluginStateError,
    is_shipped,
    scan_external_plugins,
)

DEFAULT_FEED = (
    "https://github.com/dawciobiel/QuickFile/releases/latest/download/"
    "plugin-index.json"
)
INDEX_SCHEMA_VERSION = 1
MAX_PACKAGE_SIZE = 256 * 1024 * 1024
MAX_FEED_SIZE = 8 * 1024 * 1024
ALLOWED_SCHEMES = {"https", "file"}
VERSION_PATTERN = re.compile(r"^\d+(\.\d+)*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

STATUS_UPDATE_AVAILABLE = "update-available"
STATUS_UP_TO_DATE = "up-to-date"
STATUS_NOT_IN_FEED = "not-in-feed"
STATUS_MANAGED = "managed-by-application"


class UpdateError(Exception):
    """Raised when the feed or an update cannot be handled safely."""


@dataclass(frozen=True)
class FeedEntry:
    plugin_id: str
    version: str
    file: str
    sha256: str
    size: int


@dataclass(frozen=True)
class Feed:
    url: str
    packages: Tuple[FeedEntry, ...]


@dataclass(frozen=True)
class CheckResult:
    plugin_id: str
    installed: str
    available: Optional[str]
    status: str


@dataclass(frozen=True)
class CheckReport:
    feed: str
    packages: Tuple[CheckResult, ...]


@dataclass(frozen=True)
class UpdateResult:
    plugin_id: str
    version: str
    status: str
    path: str
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RollbackResult:
    plugin_id: str
    disabled_version: str
    active_version: str
    path: str


def load_feed(feed_url: str = DEFAULT_FEED) -> Feed:
    """Read and validate the whole feed; one bad entry invalidates it."""
    _validate_url(feed_url)
    raw = _read_url(feed_url, MAX_FEED_SIZE, "Feed")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateError(f"Cannot parse feed {feed_url}: {error}") from error

    if not isinstance(document, dict):
        raise UpdateError(f"Feed {feed_url} must contain a JSON object.")

    schema_version = document.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version < 1
    ):
        raise UpdateError(f"Invalid schema_version in feed {feed_url}.")
    if schema_version > INDEX_SCHEMA_VERSION:
        raise UpdateError(
            f"Unsupported schema_version {schema_version} in feed {feed_url}; "
            f"this version supports {INDEX_SCHEMA_VERSION}."
        )

    packages = document.get("packages")
    if not isinstance(packages, list):
        raise UpdateError(f"Feed {feed_url} must contain a packages list.")

    entries: List[FeedEntry] = []
    seen = set()
    for index, item in enumerate(packages):
        entry = _parse_entry(item, index, feed_url)
        key = (entry.plugin_id, entry.version)
        if key in seen:
            raise UpdateError(
                f"Duplicate package {entry.plugin_id} {entry.version} "
                f"in feed {feed_url}."
            )
        seen.add(key)
        entries.append(entry)
    return Feed(feed_url, tuple(entries))


def _parse_entry(item, index: int, feed_url: str) -> FeedEntry:
    where = f"package #{index} in feed {feed_url}"
    if not isinstance(item, dict):
        raise UpdateError(f"Invalid {where}: expected an object.")

    plugin_id = item.get("id")
    version = item.get("version")
    file_name = item.get("file")
    sha256 = item.get("sha256")
    size = item.get("size")

    if not isinstance(plugin_id, str) or not plugin_id.strip():
        raise UpdateError(f"Invalid {where}: id must be a non-empty string.")
    if not isinstance(version, str) or not VERSION_PATTERN.match(version):
        raise UpdateError(f"Invalid {where}: version must be digits and dots.")
    if (
        not isinstance(file_name, str)
        or not file_name
        or os.path.basename(file_name) != file_name
        or "/" in file_name
        or "\\" in file_name
    ):
        raise UpdateError(f"Invalid {where}: file must be a bare file name.")
    if not isinstance(sha256, str) or not SHA256_PATTERN.match(sha256):
        raise UpdateError(
            f"Invalid {where}: sha256 must be 64 lowercase hex characters."
        )
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise UpdateError(f"Invalid {where}: size must be a non-negative integer.")

    return FeedEntry(plugin_id, version, file_name, sha256, size)


def check_updates(
    feed_url: str = DEFAULT_FEED,
    dest: Optional[str] = None,
    install_dir: Optional[str] = None,
) -> CheckReport:
    """Compare installed external plugins with the feed."""
    feed = load_feed(feed_url)
    destination = os.path.abspath(dest or default_destination())
    shipped_root = os.path.abspath(install_dir or default_install_dir())
    installed = _scan_installed(destination)
    newest = _newest_versions(feed)

    results = []
    for plugin_id in sorted(installed):
        current = installed[plugin_id]
        available = newest.get(plugin_id)
        if is_shipped(plugin_id, shipped_root):
            status = STATUS_MANAGED
        elif available is None:
            status = STATUS_NOT_IN_FEED
        elif _version_key(current.version) < _version_key(available.version):
            status = STATUS_UPDATE_AVAILABLE
        else:
            status = STATUS_UP_TO_DATE
        results.append(
            CheckResult(
                plugin_id,
                current.version,
                available.version if available is not None else None,
                status,
            )
        )
    return CheckReport(feed.url, tuple(results))


def update_plugin(
    plugin_id: str,
    feed_url: str = DEFAULT_FEED,
    version: Optional[str] = None,
    dest: Optional[str] = None,
    install_dir: Optional[str] = None,
    installer=None,
) -> UpdateResult:
    """Install a newer version of one external plugin."""
    feed = load_feed(feed_url)
    destination = os.path.abspath(dest or default_destination())
    shipped_root = os.path.abspath(install_dir or default_install_dir())

    if is_shipped(plugin_id, shipped_root):
        raise UpdateError(
            f"Plugin {plugin_id} is shipped with QuickFile; it is updated "
            "with the application, not from the feed."
        )

    installed = _scan_installed(destination)
    current = installed.get(plugin_id)
    if current is None:
        raise UpdateError(
            f"Plugin {plugin_id} is not installed in {destination}; "
            "install it first."
        )

    entries = [entry for entry in feed.packages if entry.plugin_id == plugin_id]
    if not entries:
        raise UpdateError(f"Plugin {plugin_id} is not in the feed {feed_url}.")
    chosen = _select_entry(entries, version, plugin_id)

    comparison = _compare_versions(chosen.version, current.version)
    if comparison == 0:
        return UpdateResult(
            plugin_id,
            current.version,
            "up-to-date",
            os.path.join(current.path, current.version),
        )
    if comparison < 0:
        raise UpdateError(
            f"Cannot update {plugin_id} from {current.version} to older "
            f"version {chosen.version}; use rollback."
        )

    if chosen.size > MAX_PACKAGE_SIZE:
        raise UpdateError(
            f"Package {chosen.file} is larger than the 256 MiB limit."
        )

    with tempfile.TemporaryDirectory(prefix="quickfile-update-") as scratch:
        package = _download(feed.url, chosen, scratch)
        installed_plugin = (installer or install_plugin)(
            package, dest=destination, install_dir=shipped_root
        )

    return UpdateResult(
        installed_plugin.plugin_id,
        installed_plugin.version,
        "installed",
        installed_plugin.path,
        tuple(installed_plugin.warnings),
    )


def rollback(
    plugin_id: str,
    dest: Optional[str] = None,
    install_dir: Optional[str] = None,
) -> RollbackResult:
    """Disable the newest active version so the previous one is loaded."""
    destination = os.path.abspath(dest or default_destination())
    shipped_root = os.path.abspath(install_dir or default_install_dir())

    if is_shipped(plugin_id, shipped_root):
        raise UpdateError(
            f"Plugin {plugin_id} is shipped with QuickFile; there is nothing "
            "to roll back."
        )

    installed = _scan_installed(destination)
    current = installed.get(plugin_id)
    if current is None:
        raise UpdateError(
            f"Plugin {plugin_id} is not installed in {destination}."
        )
    if len(current.versions) < 2:
        raise UpdateError(
            f"Plugin {plugin_id} has only one active version; "
            "there is nothing to roll back to."
        )

    newest = current.versions[0]
    newest_path = os.path.join(current.path, newest)
    disabled_path = newest_path + ".disabled"
    if os.path.exists(disabled_path):
        raise UpdateError(
            f"{disabled_path} already exists; refusing to overwrite it."
        )

    os.rename(newest_path, disabled_path)
    return RollbackResult(
        plugin_id, newest, current.versions[1], current.path
    )


def _select_entry(
    entries: Sequence[FeedEntry], version: Optional[str], plugin_id: str
) -> FeedEntry:
    if version is None:
        return max(entries, key=lambda entry: _version_key(entry.version))
    for entry in entries:
        if entry.version == version:
            return entry
    raise UpdateError(f"Version {version} of {plugin_id} is not in the feed.")


def _download(feed_url: str, entry: FeedEntry, directory: str) -> str:
    url = urljoin(feed_url, entry.file)
    _validate_url(url)
    path = os.path.join(directory, entry.file)
    written = 0
    try:
        with _open_url(url) as source, open(path, "wb") as destination:
            while True:
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > entry.size:
                    raise UpdateError(
                        f"Package {entry.file} exceeds the declared size "
                        f"of {entry.size} bytes."
                    )
                destination.write(chunk)
    except UpdateError:
        raise
    except OSError as error:
        raise UpdateError(f"Cannot download {url}: {error}") from error

    if written != entry.size:
        raise UpdateError(
            f"Package {entry.file} size is {written} bytes, "
            f"expected {entry.size}."
        )

    actual = _hash_file(path)
    if actual != entry.sha256:
        raise UpdateError(
            f"Package {entry.file} SHA-256 is {actual}, "
            f"expected {entry.sha256}."
        )
    return path


def _newest_versions(feed: Feed) -> Dict[str, FeedEntry]:
    newest: Dict[str, FeedEntry] = {}
    for entry in feed.packages:
        current = newest.get(entry.plugin_id)
        if current is None or _version_key(entry.version) > _version_key(
            current.version
        ):
            newest[entry.plugin_id] = entry
    return newest


def _scan_installed(destination: str) -> Dict[str, ExternalPlugin]:
    try:
        plugins = scan_external_plugins(destination, include_disabled=False)
    except PluginStateError as error:
        raise UpdateError(str(error)) from error
    return {plugin.plugin_id: plugin for plugin in plugins}


def _version_key(version: str):
    return tuple(map(int, version.split(".")))


def _compare_versions(left: str, right: str) -> int:
    left_key = _version_key(left)
    right_key = _version_key(right)
    return (left_key > right_key) - (left_key < right_key)


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UpdateError(
            f"Unsupported URL scheme {parsed.scheme!r} in {url}; "
            "use https or file."
        )
    if parsed.scheme == "https" and not parsed.netloc:
        raise UpdateError(f"Missing host in feed URL {url}.")
    if parsed.scheme == "file" and not parsed.path:
        raise UpdateError(f"Missing path in feed URL {url}.")


def _open_url(url: str):
    parsed = urlparse(url)
    try:
        if parsed.scheme == "file":
            return open(url2pathname(parsed.path), "rb")
        return urllib.request.urlopen(url, timeout=30)
    except OSError as error:
        raise UpdateError(f"Cannot read {url}: {error}") from error


def _read_url(url: str, limit: int, label: str) -> bytes:
    with _open_url(url) as handle:
        try:
            data = handle.read(limit + 1)
        except OSError as error:
            raise UpdateError(f"Cannot read {url}: {error}") from error
    if len(data) > limit:
        raise UpdateError(f"{label} {url} is larger than {limit} bytes.")
    return data


def _hash_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _print_check(report: CheckReport, as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "feed": report.feed,
                    "packages": [
                        {
                            "id": item.plugin_id,
                            "installed": item.installed,
                            "available": item.available,
                            "status": item.status,
                        }
                        for item in report.packages
                    ],
                },
                indent=2,
            )
        )
        return

    if not report.packages:
        print("No external plugins installed.")
        return
    for item in report.packages:
        print(
            f"{item.plugin_id}: {item.status} "
            f"(installed {item.installed}, "
            f"available {item.available or '-'})"
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.plugin_updater",
        description="Check, update and roll back external plugins.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check_parser = commands.add_parser(
        "check", help="Report available updates without changing anything."
    )
    check_parser.add_argument("--feed", default=DEFAULT_FEED)
    check_parser.add_argument("--json", action="store_true", dest="as_json")

    update_parser = commands.add_parser(
        "update", help="Install a newer version from the feed."
    )
    update_parser.add_argument("plugin_id")
    update_parser.add_argument("--feed", default=DEFAULT_FEED)
    update_parser.add_argument("--version", default=None)

    rollback_parser = commands.add_parser(
        "rollback", help="Disable the newest version in favour of the previous."
    )
    rollback_parser.add_argument("plugin_id")

    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "check":
            _print_check(
                check_updates(arguments.feed), as_json=arguments.as_json
            )
        elif arguments.command == "update":
            result = update_plugin(
                arguments.plugin_id,
                arguments.feed,
                version=arguments.version,
            )
            if result.status == "up-to-date":
                print(f"{result.plugin_id} {result.version} is up to date.")
            else:
                print(
                    f"Installed {result.plugin_id} {result.version} "
                    f"at {result.path}"
                )
                for warning in result.warnings:
                    print(f"warning: {warning}")
        else:
            result = rollback(arguments.plugin_id)
            print(
                f"Disabled {result.plugin_id} {result.disabled_version}; "
                f"active version is {result.active_version}."
            )
    except (UpdateError, PluginInstallationError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
