# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""The host renders a plugin settings schema as a standard Qt form."""

import pytest

from app.plugin_settings import PluginSettingsError
from utils.plugin_settings_dialog import PluginSettingsDialog


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
    "enabled": {"type": "boolean", "title": "Enabled", "default": True},
    "note": {"type": "string", "title": "Note", "default": ""},
}


def test_the_form_starts_with_defaults(qapp):
    dialog = PluginSettingsDialog(None, "ZIP Archiver", SCHEMA)
    try:
        assert dialog.get_options() == {
            "compression": "deflate",
            "compresslevel": 6,
            "enabled": True,
            "note": "",
        }
    finally:
        dialog.deleteLater()


def test_edited_values_are_returned(qapp):
    dialog = PluginSettingsDialog(
        None,
        "ZIP Archiver",
        SCHEMA,
        {"compression": "deflate", "compresslevel": 6},
    )
    try:
        dialog._widgets["compression"].setCurrentIndex(1)
        dialog._widgets["compresslevel"].setValue(9)
        dialog._widgets["enabled"].setChecked(False)
        dialog._widgets["note"].setText("hello")

        assert dialog.get_options() == {
            "compression": "store",
            "compresslevel": 9,
            "enabled": False,
            "note": "hello",
        }
    finally:
        dialog.deleteLater()


def test_options_unknown_to_the_schema_survive_an_edit(qapp):
    dialog = PluginSettingsDialog(
        None, "ZIP Archiver", SCHEMA, {"legacy": "keep", "compresslevel": 3}
    )
    try:
        dialog._widgets["compresslevel"].setValue(5)

        assert dialog.get_options()["legacy"] == "keep"
        assert dialog.get_options()["compresslevel"] == 5
    finally:
        dialog.deleteLater()


def test_an_invalid_schema_is_rejected(qapp):
    with pytest.raises(PluginSettingsError):
        PluginSettingsDialog(
            None,
            "Broken",
            {"field": {"type": "unknown", "title": "Field", "default": "x"}},
        )
