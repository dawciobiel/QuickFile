# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""The create-archive dialog asks only plugins that can create archives."""

from unittest.mock import MagicMock

from app.plugin_system.api import Capability
from utils.create_archive_dialog import CreateArchiveDialog


class FakeArchivePlugin:
    def __init__(self, plugin_id, name, extensions):
        self.metadata = {"id": plugin_id}
        self.name = name
        self.extensions = extensions

    def get_name(self):
        return self.name

    def get_supported_extensions(self):
        return list(self.extensions)


class FakeSettingsManager:
    def get_plugin_settings(self, plugin_id):
        return {}

    def set_plugin_settings(self, plugin_id, options):
        pass


def test_the_dialog_offers_only_plugins_that_can_create_archives(qapp):
    plugin = FakeArchivePlugin("org.example.creator", "ZIP Creator", ["zip"])
    manager = MagicMock()
    manager.get_archivers.return_value = [plugin]

    dialog = CreateArchiveDialog(
        None, manager, "/tmp", settings_manager=FakeSettingsManager()
    )
    try:
        assert dialog.type_combo.count() == 1
        assert dialog.type_combo.itemData(0) is plugin
        manager.get_archivers.assert_called_once_with(Capability.ARCHIVE_CREATE)

        data = dialog.get_data()

        assert data is not None
        assert data["options"]["plugin_id"] == "org.example.creator"
        # Plugins may report "zip" without a leading dot; the path still needs one.
        assert data["destination_path"].endswith("/archive.zip")
        assert data["plugin"] is plugin
    finally:
        dialog.deleteLater()
