# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Bundled plugins must ship a schema the host can actually render.

The host trusts the schema shape but not its contents: an unknown type, a
missing default or a default outside its range would make the settings form
unusable. Bundled metadata is part of the application, so it is checked here
instead of failing at runtime.

Specification: ``docs/architecture/plugins/plugins.md`` ("Ustawienia pluginów").
"""

import glob
import json
import os

import pytest

from app.plugin_settings import defaults_for, validate_schema

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins", "org.quickfile")


def _settings_cases():
    cases = []
    for metadata_path in sorted(
        glob.glob(os.path.join(PLUGINS_DIR, "*", "*", "metadata.json"))
    ):
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
        schema = (metadata.get("settings") or {}).get("schema")
        if schema:
            cases.append((metadata_path, metadata, schema))
    return cases


CASES = _settings_cases()


def test_the_contract_covers_the_zip_plugin():
    assert "org.quickfile.zip_archiver" in {
        metadata["id"] for _, metadata, _ in CASES
    }


@pytest.mark.parametrize(
    "metadata_path,metadata,schema", CASES, ids=[meta["id"] for _, meta, _ in CASES]
)
def test_bundled_settings_schemas_are_valid(metadata_path, metadata, schema):
    validate_schema(schema)


def test_zip_defaults_match_the_settings_contract():
    _, metadata, schema = next(
        case for case in CASES if case[1]["id"] == "org.quickfile.zip_archiver"
    )

    assert defaults_for(schema) == {
        "compression": "deflate",
        "compresslevel": 6,
    }
