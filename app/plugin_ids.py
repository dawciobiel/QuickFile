# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Single source of truth for bundled plugin identifiers.

A plugin **id** is not a plugin **type**. Three plugins share the type
``standard_operations`` (copy, move, delete) and each one has a different id.
Using the type as an id makes ``TaskQueueManager`` log
``Task ... failed: Plugin not found.`` and the operation never runs.

Dialogs and the dialog handler must use these constants instead of string
literals so the mapping stays in one place.
"""

from typing import Optional

COPY_PLUGIN_ID = "org.quickfile.copy_operation"
MOVE_PLUGIN_ID = "org.quickfile.move_operation"
DELETE_PLUGIN_ID = "org.quickfile.delete_operation"
SEARCH_PLUGIN_ID = "org.quickfile.search_standard"
CHECKSUM_PLUGIN_ID = "org.quickfile.checksum_standard"
FILE_SPLITTER_PLUGIN_ID = "org.quickfile.file_splitter"

# TaskType value (action id) -> bundled plugin that implements it.
#
# Tasks for archives and menu actions are resolved dynamically (several
# plugins can implement the same action), so they are not listed here.
PLUGIN_ID_BY_ACTION = {
    "copy_items": COPY_PLUGIN_ID,
    "move_items": MOVE_PLUGIN_ID,
    "delete_items": DELETE_PLUGIN_ID,
    "search": SEARCH_PLUGIN_ID,
    "calculate_checksum": CHECKSUM_PLUGIN_ID,
    "split_file": FILE_SPLITTER_PLUGIN_ID,
    "join_files": FILE_SPLITTER_PLUGIN_ID,
}


def plugin_id_for_action(action_id: str) -> Optional[str]:
    """Return the bundled plugin id that implements ``action_id``, if known."""
    return PLUGIN_ID_BY_ACTION.get(action_id)
