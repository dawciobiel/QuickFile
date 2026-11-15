# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The copy/move/delete dialogs are where the broken plugin id originated.

``get_options()`` fed ``options["plugin_id"]`` directly into a ``Task``, so a
wrong value there silently disabled the operation with
``Task ... failed: Plugin not found.``.
"""

from unittest.mock import MagicMock

import pytest

from app.plugin_ids import (
    COPY_PLUGIN_ID,
    DELETE_PLUGIN_ID,
    MOVE_PLUGIN_ID,
    SEARCH_PLUGIN_ID,
)
from utils.copy_dialog import CopyDialog
from utils.delete_dialog import DeleteDialog
from utils.move_dialog import MoveDialog
from utils.search_dialog import SearchDialog


@pytest.fixture
def dependencies():
    return MagicMock(), MagicMock(), MagicMock()


def test_copy_dialog_returns_copy_plugin_id(qapp, dependencies):
    queue_manager, background_manager, theme_manager = dependencies
    dialog = CopyDialog(
        None, ["/src/file"], "/dst", queue_manager, background_manager, theme_manager
    )

    assert dialog.get_options()["plugin_id"] == COPY_PLUGIN_ID
    dialog.deleteLater()


def test_move_dialog_returns_move_plugin_id(qapp, dependencies):
    queue_manager, background_manager, theme_manager = dependencies
    dialog = MoveDialog(
        None, ["/src/file"], "/dst", queue_manager, background_manager, theme_manager
    )

    assert dialog.get_options()["plugin_id"] == MOVE_PLUGIN_ID
    dialog.deleteLater()


def test_delete_dialog_returns_delete_plugin_id(qapp, dependencies):
    queue_manager, background_manager, theme_manager = dependencies
    dialog = DeleteDialog(
        None, ["/src/file"], queue_manager, background_manager, theme_manager
    )

    assert dialog.get_options()["plugin_id"] == DELETE_PLUGIN_ID
    dialog.deleteLater()


def test_search_dialog_returns_search_plugin_id(qapp):
    dialog = SearchDialog(None, "/src")

    assert dialog.get_options()["plugin_id"] == SEARCH_PLUGIN_ID
    dialog.deleteLater()
