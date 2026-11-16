# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Options produced by the delete dialog, including the Trash fallback."""

from unittest.mock import MagicMock

import pytest

from utils.delete_dialog import DeleteDialog


@pytest.fixture
def dialog(qapp):
    dependencies = MagicMock(), MagicMock(), MagicMock()
    queue_manager, background_manager, theme_manager = dependencies
    delete_dialog = DeleteDialog(
        None, ["/src/file"], queue_manager, background_manager, theme_manager
    )
    yield delete_dialog
    delete_dialog.deleteLater()


def test_move_to_trash_is_the_default_without_a_permanent_fallback(dialog):
    options = dialog.get_options()

    assert options["move_to_trash"] is True
    assert options["permanent_fallback"] is False
    assert dialog.fallback_checkbox.isEnabled()


def test_fallback_is_reported_when_both_boxes_are_checked(dialog):
    dialog.fallback_checkbox.setChecked(True)

    assert dialog.get_options()["permanent_fallback"] is True


def test_fallback_is_ignored_and_cleared_when_trash_is_unchecked(dialog):
    dialog.fallback_checkbox.setChecked(True)
    dialog.move_to_trash_checkbox.setChecked(False)

    options = dialog.get_options()

    assert options["move_to_trash"] is False
    assert options["permanent_fallback"] is False
    assert not dialog.fallback_checkbox.isEnabled()
    assert not dialog.fallback_checkbox.isChecked()
