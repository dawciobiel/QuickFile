# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Operations behind the plugin management settings page.

The service only wires the existing updater and state functions to one object
with a fixed feed and plugin directories. Keeping it free of Qt makes the UI
testable with a temporary directory and a ``file://`` feed.
"""

import os
from typing import Optional, Sequence

from app.plugin_installer import InstalledPlugin, install
from app.plugin_state import (
    ExternalPlugin,
    disable_plugin,
    enable_plugin,
    scan_external_plugins,
)
from app.plugin_updater import (
    DEFAULT_FEED,
    CheckReport,
    RollbackResult,
    UpdateResult,
    check_updates,
    rollback,
    update_plugin,
)


class PluginManagementService:
    def __init__(
        self,
        feed: str = DEFAULT_FEED,
        dest: Optional[str] = None,
        install_dir: Optional[str] = None,
    ):
        self.feed = feed
        self.dest = os.fspath(dest) if dest is not None else None
        self.install_dir = (
            os.fspath(install_dir) if install_dir is not None else None
        )

    def plugins(self) -> Sequence[ExternalPlugin]:
        return scan_external_plugins(
            self.dest, include_disabled=True
        )

    def install(self, source: str) -> InstalledPlugin:
        return install(
            source, dest=self.dest, install_dir=self.install_dir
        )

    def check(self) -> CheckReport:
        return check_updates(
            self.feed, dest=self.dest, install_dir=self.install_dir
        )

    def update(self, plugin_id: str, version: Optional[str] = None) -> UpdateResult:
        return update_plugin(
            plugin_id,
            self.feed,
            version=version,
            dest=self.dest,
            install_dir=self.install_dir,
        )

    def rollback(self, plugin_id: str) -> RollbackResult:
        return rollback(
            plugin_id, dest=self.dest, install_dir=self.install_dir
        )

    def disable(self, plugin_id: str) -> ExternalPlugin:
        return disable_plugin(
            plugin_id, destination=self.dest, install_dir=self.install_dir
        )

    def enable(self, plugin_id: str) -> ExternalPlugin:
        return enable_plugin(
            plugin_id, destination=self.dest, install_dir=self.install_dir
        )
