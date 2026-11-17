# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Archive plugins declare what they can do, and the declaration is checked
against ``create_task``.

``type: archive`` puts a plugin in the archive slot, but it does not say
whether the plugin creates archives, extracts them, or both. Without
capabilities the create dialog offered RAR (extract-only) and the extract path
picked ZIP (create-only). The vocabulary lives in ``Capability``.

Specification: ``docs/architecture/plugins/plugins.md`` ("Capabilities").
"""

import glob
import importlib
import json
import os
import sys
from contextlib import contextmanager

import pytest

from app.plugin_system.api import Capability, PluginTask
from tests.plugin_helpers import get_latest_plugin_path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins", "org.quickfile")

CAPABILITY_ACTIONS = {
    Capability.ARCHIVE_CREATE: "create_archive",
    Capability.ARCHIVE_EXTRACT: "extract_archive",
}


def _archive_cases():
    cases = []
    for metadata_path in sorted(
        glob.glob(os.path.join(PLUGINS_DIR, "*", "*", "metadata.json"))
    ):
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
        if metadata.get("type") == "archive":
            cases.append((metadata_path, metadata))
    return cases


CASES = _archive_cases()


@contextmanager
def _load_plugin(version_dir):
    saved = {name: sys.modules.pop(name, None) for name in ("plugin", "tasks")}
    sys.path.insert(0, version_dir)
    try:
        tasks = importlib.import_module("tasks")
        yield importlib.import_module("plugin"), tasks
    finally:
        sys.path.remove(version_dir)
        sys.modules.pop("plugin", None)
        sys.modules.pop("tasks", None)
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module


def _kwargs(tmp_path):
    return {
        "source_paths": [str(tmp_path / "source")],
        "source_path": str(tmp_path / "source.rar"),
        "destination_path": str(tmp_path / "archive.zip"),
        "dest_dir": str(tmp_path / "extracted"),
        "options": {},
    }


EXPECTED_CAPABILITIES = {
    "org.quickfile.zip_archiver": {
        Capability.ARCHIVE_CREATE,
        Capability.ARCHIVE_EXTRACT,
    },
    "org.quickfile.rar_archiver": {Capability.ARCHIVE_EXTRACT},
}


def test_the_contract_covers_both_archive_plugins():
    assert {metadata["id"] for _, metadata in CASES} == set(EXPECTED_CAPABILITIES)


@pytest.mark.parametrize(
    "metadata_path,metadata", CASES, ids=[meta["id"] for _, meta in CASES]
)
def test_archive_plugins_declare_the_capabilities_they_are_shipped_with(
    metadata_path, metadata
):
    assert set(metadata["capabilities"]) == EXPECTED_CAPABILITIES[metadata["id"]]


@pytest.mark.parametrize(
    "metadata_path,metadata", CASES, ids=[meta["id"] for _, meta in CASES]
)
def test_archive_capabilities_are_declared_and_known(metadata_path, metadata):
    capabilities = metadata.get("capabilities")

    assert capabilities, (
        f"{metadata['id']} does not declare capabilities; type=archive alone "
        "cannot tell creation from extraction"
    )
    assert set(capabilities) <= Capability.ALL, (
        f"{metadata['id']} declares unknown archive capabilities: "
        f"{sorted(set(capabilities) - Capability.ALL)}"
    )


@pytest.mark.parametrize(
    "metadata_path,metadata", CASES, ids=[meta["id"] for _, meta in CASES]
)
def test_declared_capabilities_match_create_task(metadata_path, metadata, tmp_path):
    version_dir = get_latest_plugin_path(
        "org.quickfile", metadata["id"].split(".")[-1]
    )
    declared_actions = {
        CAPABILITY_ACTIONS[capability]
        for capability in metadata["capabilities"]
    }

    with _load_plugin(version_dir) as (plugin_module, _tasks):
        plugin = getattr(plugin_module, metadata["class_name"])()

        for action_id in CAPABILITY_ACTIONS.values():
            if action_id in declared_actions:
                task = plugin.create_task(action_id, **_kwargs(tmp_path))
                assert isinstance(task, PluginTask)
            else:
                with pytest.raises(ValueError):
                    plugin.create_task(action_id, **_kwargs(tmp_path))
