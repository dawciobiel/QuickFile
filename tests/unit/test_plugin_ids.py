# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract tests for plugin identifiers.

The regression these tests exist for: the copy/move/delete dialogs put the
plugin *type* ("org.quickfile.standard_operations") into ``options["plugin_id"]``
instead of the plugin *id*. ``TaskQueueManager`` then logged
``Task ... failed: Plugin not found.`` and nothing was copied.
"""

import json
import os

import pytest

from app.enums import TaskType
from app.plugin_ids import (
    CHECKSUM_PLUGIN_ID,
    COPY_PLUGIN_ID,
    DELETE_PLUGIN_ID,
    FILE_SPLITTER_PLUGIN_ID,
    MOVE_PLUGIN_ID,
    PLUGIN_ID_BY_ACTION,
    SEARCH_PLUGIN_ID,
    plugin_id_for_action,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins", "org.quickfile")


def bundled_plugin_ids():
    ids = set()
    for plugin_name in os.listdir(PLUGINS_DIR):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        if not os.path.isdir(plugin_path):
            continue
        for version in os.listdir(plugin_path):
            metadata_path = os.path.join(plugin_path, version, "metadata.json")
            if os.path.isfile(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as handle:
                    ids.add(json.load(handle)["id"])
    return ids


def test_all_referenced_plugin_ids_exist_in_the_bundle():
    known = bundled_plugin_ids()
    referenced = {
        COPY_PLUGIN_ID,
        MOVE_PLUGIN_ID,
        DELETE_PLUGIN_ID,
        SEARCH_PLUGIN_ID,
        CHECKSUM_PLUGIN_ID,
        FILE_SPLITTER_PLUGIN_ID,
    }

    assert referenced <= known, f"Unknown plugin ids: {sorted(referenced - known)}"


@pytest.mark.parametrize(
    "action_id, expected",
    [
        (TaskType.COPY.value, COPY_PLUGIN_ID),
        (TaskType.MOVE.value, MOVE_PLUGIN_ID),
        (TaskType.DELETE.value, DELETE_PLUGIN_ID),
        (TaskType.SEARCH.value, SEARCH_PLUGIN_ID),
        (TaskType.CHECKSUM.value, CHECKSUM_PLUGIN_ID),
        (TaskType.SPLIT_FILE.value, FILE_SPLITTER_PLUGIN_ID),
        (TaskType.JOIN_FILES.value, FILE_SPLITTER_PLUGIN_ID),
    ],
)
def test_action_to_plugin_mapping(action_id, expected):
    assert plugin_id_for_action(action_id) == expected


def test_unknown_action_has_no_plugin():
    assert plugin_id_for_action("does_not_exist") is None


def test_every_mapping_key_is_a_real_task_action():
    """Guard against typos in the mapping keys."""
    task_actions = {task_type.value for task_type in TaskType}
    unknown = set(PLUGIN_ID_BY_ACTION) - task_actions
    assert not unknown, f"Mapping keys are not TaskType values: {sorted(unknown)}"
