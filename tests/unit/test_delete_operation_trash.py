# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for the delete task's Trash handling and symlink safety.

Specification: ``docs/architecture/plugins/plugins.md``.

Two regressions are covered here:

* ``DeleteDialog`` used to send ``move_to_trash=True`` while the plugin ignored
  it and deleted permanently. On Linux nothing ever reached the Trash.
* Permanent deletion walked the tree with ``os.walk`` and then called
  ``os.rmdir`` on everything listed as a directory. A symlink to a directory
  appears there too, so deleting the link first destroyed the target's files
  and then failed on ``os.rmdir``.
"""

import importlib
import logging
import os
import sys

import pytest

from app.plugin_system.api import TaskContext
from tests.plugin_helpers import get_latest_plugin_path

PLUGIN_GROUP = "org.quickfile"
PLUGIN_NAME = "delete_operation"


class RecordingContext(TaskContext):
    def __init__(self):
        self.task_id = "delete-task"
        self.cancelled = False
        self.paused = False
        self.progress_values = []
        self.logs = []

    def is_cancelled(self):
        return self.cancelled

    def is_paused(self):
        return self.paused

    def wait_if_paused(self):
        pass

    def progress(self, percentage):
        self.progress_values.append(percentage)

    def log(self, level, message):
        self.logs.append((level, message))


@pytest.fixture(scope="module")
def plugin_version_dir():
    return get_latest_plugin_path(PLUGIN_GROUP, PLUGIN_NAME)


@pytest.fixture
def plugin_modules(plugin_version_dir):
    """Imports ``plugin`` and ``tasks`` from the bundled version directory."""
    saved_modules = {name: sys.modules.pop(name, None) for name in ("plugin", "tasks")}
    sys.path.insert(0, plugin_version_dir)
    try:
        tasks = importlib.import_module("tasks")
        yield importlib.import_module("plugin"), tasks
    finally:
        sys.path.remove(plugin_version_dir)
        sys.modules.pop("plugin", None)
        sys.modules.pop("tasks", None)
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module


def run_task(plugin_modules, paths, **options):
    _plugin, tasks = plugin_modules
    task = tasks.DeleteTask([str(path) for path in paths], options)
    context = RecordingContext()
    progress = []
    task._initialize(
        context,
        progress.append,
        lambda _name, _payload: None,
        lambda _name, _payload: {},
    )
    task.run()
    return context, progress


# --- Move to Trash -----------------------------------------------------------


def test_move_to_trash_is_the_default_and_uses_send2trash(
    plugin_modules, tmp_path, mocker
):
    _plugin, tasks = plugin_modules
    path = tmp_path / "doomed.txt"
    path.write_text("still here")
    send2trash = mocker.patch.object(tasks.send2trash, "send2trash")

    _context, progress = run_task(plugin_modules, [path])

    send2trash.assert_called_once_with(str(path))
    assert path.exists()
    assert progress[-1] == 100


def test_a_failed_trash_move_keeps_the_file_and_explains_the_fix(
    plugin_modules, tmp_path, mocker
):
    _plugin, tasks = plugin_modules
    path = tmp_path / "doomed.txt"
    path.write_text("do not delete me")
    mocker.patch.object(
        tasks.send2trash,
        "send2trash",
        side_effect=PermissionError(13, "Permission denied"),
    )

    with pytest.raises(tasks.TrashUnavailableError) as error:
        run_task(plugin_modules, [path], move_to_trash=True)

    assert path.read_text() == "do not delete me"
    assert "Move to Trash" in str(error.value)


def test_permanent_fallback_deletes_when_the_user_opted_in(
    plugin_modules, tmp_path, mocker, caplog
):
    _plugin, tasks = plugin_modules
    path = tmp_path / "doomed.txt"
    path.write_text("delete me")
    mocker.patch.object(
        tasks.send2trash,
        "send2trash",
        side_effect=PermissionError(13, "Permission denied"),
    )

    with caplog.at_level(logging.WARNING):
        run_task(
            plugin_modules,
            [path],
            move_to_trash=True,
            permanent_fallback=True,
        )

    assert not path.exists()
    assert any("permanently" in record.getMessage() for record in caplog.records)


# --- Permanent deletion and symlinks ----------------------------------------


def test_permanent_delete_removes_a_symlink_without_touching_its_target(
    plugin_modules, tmp_path
):
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("keep me")
    link = tmp_path / "link"
    os.symlink(target, link)

    run_task(plugin_modules, [link], move_to_trash=False)

    assert not os.path.lexists(link)
    assert (target / "keep.txt").read_text() == "keep me"


def test_permanent_delete_removes_nested_symlinks_without_following_them(
    plugin_modules, tmp_path
):
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("keep me")
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "tree.txt").write_text("delete me")
    os.symlink(target, tree / "link")

    run_task(plugin_modules, [tree], move_to_trash=False)

    assert not tree.exists()
    assert (target / "keep.txt").read_text() == "keep me"


def test_permanent_delete_removes_a_broken_symlink(plugin_modules, tmp_path):
    link = tmp_path / "broken"
    os.symlink(tmp_path / "does-not-exist", link)

    run_task(plugin_modules, [link], move_to_trash=False)

    assert not os.path.lexists(link)
