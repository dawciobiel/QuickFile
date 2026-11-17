# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract for host-rendered plugin settings.

Plugins declare a small, closed schema; the host renders the form. Metadata is
untrusted input, so an invalid schema or an option of the wrong type is an
error instead of a silently broken dialog.
"""

import pytest

from app.plugin_settings import (
    PluginSettingsError,
    defaults_for,
    normalize_options,
    schema_for_plugin,
    validate_schema,
)


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


class FakePlugin:
    def __init__(self, metadata):
        self.metadata = metadata


def test_defaults_are_taken_from_the_schema():
    assert defaults_for(SCHEMA) == {
        "compression": "deflate",
        "compresslevel": 6,
        "enabled": True,
        "note": "",
    }


def test_normalize_fills_defaults_and_preserves_unknown_keys():
    options = normalize_options(SCHEMA, {"compresslevel": 9, "legacy": "keep"})

    assert options == {
        "compression": "deflate",
        "compresslevel": 9,
        "enabled": True,
        "note": "",
        "legacy": "keep",
    }


@pytest.mark.parametrize(
    "options",
    [
        {"compression": "lzma"},
        {"compression": ["deflate"]},
        {"compresslevel": 0},
        {"compresslevel": 10},
        {"compresslevel": "6"},
        {"compresslevel": True},
        {"enabled": "yes"},
        {"note": 1},
    ],
)
def test_invalid_values_are_rejected(options):
    with pytest.raises(PluginSettingsError):
        normalize_options(SCHEMA, options)


@pytest.mark.parametrize(
    "schema",
    [
        {"field": {"title": "No type", "default": "x"}},
        {"field": {"type": "object", "title": "Bad type", "default": {}}},
        {"field": {"type": "string", "title": "No default"}},
        {"field": {"type": "string", "default": "x"}},
        {
            "field": {
                "type": "integer",
                "title": "Inverted",
                "default": 5,
                "minimum": 9,
                "maximum": 1,
            }
        },
        {
            "field": {
                "type": "enum",
                "title": "Bad default",
                "default": "other",
                "choices": [{"value": "one", "label": "One"}],
            }
        },
        {
            "field": {
                "type": "enum",
                "title": "Bad default type",
                "default": ["one"],
                "choices": [{"value": "one", "label": "One"}],
            }
        },
        {
            "field": {
                "type": "enum",
                "title": "No choices",
                "default": "one",
                "choices": [],
            }
        },
    ],
)
def test_invalid_schemas_are_rejected(schema):
    with pytest.raises(PluginSettingsError):
        validate_schema(schema)


def test_schema_for_plugin_reads_metadata():
    plugin = FakePlugin({"id": "org.example.zip", "settings": {"schema": SCHEMA}})

    assert schema_for_plugin(plugin) == SCHEMA


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"settings": {}},
        {"settings": {"schema": {}}},
        {"settings": {"schema": None}},
    ],
)
def test_schema_for_plugin_returns_none_without_a_schema(metadata):
    assert schema_for_plugin(FakePlugin(metadata)) is None
