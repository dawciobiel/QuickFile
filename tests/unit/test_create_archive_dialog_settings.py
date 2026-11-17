# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""CreateArchiveDialog uses host-rendered settings stored per plugin id."""

from unittest.mock import MagicMock

from PyQt6.QtWidgets import QDialog

from utils.create_archive_dialog import CreateArchiveDialog


SCHEMA = {
    "compression": {
        "type": "enum",
        "title": "Compression method",
        "default": "deflate",
        "choices": [
            {"value": "deflate", "label": "Deflate"},
            {"value": "store", "label": "Store"},
        ],
    },
    "compresslevel": {
        "type": "integer",
        "title": "Compression level",
        "default": 6,
        "minimum": 1,
        "maximum": 9,
    },
}


class FakeArchivePlugin:
    def __init__(self, plugin_id, name, extensions, schema=None):
        self.metadata = {"id": plugin_id}
        if schema is not None:
            self.metadata["settings"] = {"schema": schema}
        self.name = name
        self.extensions = extensions

    def get_name(self):
        return self.name

    def get_supported_extensions(self):
        return list(self.extensions)


class FakeSettingsManager:
    def __init__(self, stored=None):
        self.stored = {key: dict(value) for key, value in (stored or {}).items()}
        self.saved = {}

    def get_plugin_settings(self, plugin_id):
        return dict(self.stored.get(plugin_id, {}))

    def set_plugin_settings(self, plugin_id, options):
        self.saved[plugin_id] = dict(options)
        self.stored[plugin_id] = dict(options)


def make_dialog(plugin, settings_manager):
    plugin_manager = MagicMock()
    plugin_manager.get_archivers.return_value = [plugin]
    return CreateArchiveDialog(
        None, plugin_manager, "/tmp", settings_manager=settings_manager
    )


def test_stored_options_are_loaded_and_schema_defaults_are_filled(qapp):
    plugin = FakeArchivePlugin("org.example.zip", "ZIP", ["zip"], SCHEMA)
    settings_manager = FakeSettingsManager(
        {"org.example.zip": {"compression": "store", "legacy": "keep"}}
    )
    dialog = make_dialog(plugin, settings_manager)
    try:
        options = dialog.get_data()["options"]

        assert options["compression"] == "store"
        assert options["compresslevel"] == 6
        assert options["legacy"] == "keep"
        assert options["plugin_id"] == "org.example.zip"
    finally:
        dialog.deleteLater()


def test_settings_button_opens_the_host_form_and_persists_the_result(
    qapp, monkeypatch
):
    seen = {}

    class FakeSettingsDialog:
        def __init__(self, parent, plugin_name, schema, current_options):
            seen["plugin_name"] = plugin_name
            seen["schema"] = schema
            seen["options"] = current_options

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_options(self):
            return {"compression": "store", "compresslevel": 9}

    monkeypatch.setattr(
        "utils.create_archive_dialog.PluginSettingsDialog", FakeSettingsDialog
    )

    plugin = FakeArchivePlugin("org.example.zip", "ZIP", ["zip"], SCHEMA)
    settings_manager = FakeSettingsManager()
    dialog = make_dialog(plugin, settings_manager)
    try:
        dialog.show_plugin_settings()

        assert seen["plugin_name"] == "ZIP"
        assert seen["schema"] == SCHEMA
        assert settings_manager.saved == {
            "org.example.zip": {"compression": "store", "compresslevel": 9}
        }

        options = dialog.get_data()["options"]
        assert options["compression"] == "store"
        assert options["compresslevel"] == 9
        assert options["plugin_id"] == "org.example.zip"
    finally:
        dialog.deleteLater()


def test_cancelling_the_form_keeps_the_previous_options(qapp, monkeypatch):
    class CancelledSettingsDialog:
        def __init__(self, parent, plugin_name, schema, current_options):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

        def get_options(self):
            raise AssertionError("cancelled dialog must not be read")

    monkeypatch.setattr(
        "utils.create_archive_dialog.PluginSettingsDialog", CancelledSettingsDialog
    )

    plugin = FakeArchivePlugin("org.example.zip", "ZIP", ["zip"], SCHEMA)
    settings_manager = FakeSettingsManager(
        {"org.example.zip": {"compression": "store", "compresslevel": 3}}
    )
    dialog = make_dialog(plugin, settings_manager)
    try:
        dialog.show_plugin_settings()

        assert settings_manager.saved == {}
        assert dialog.get_data()["options"]["compresslevel"] == 3
    finally:
        dialog.deleteLater()
