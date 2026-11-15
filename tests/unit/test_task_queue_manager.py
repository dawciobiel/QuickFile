# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for resolving a task to a plugin in TaskQueueManager.

The regression these tests exist for: the copy/move/delete dialogs stored the
plugin *type* ("org.quickfile.standard_operations") in ``options["plugin_id"]``.
No loaded plugin has that id, so the queue reported
``Task ... failed: Plugin not found.`` and the operation never started.
"""

from unittest.mock import MagicMock

import pytest

from app.enums import TaskStatus, TaskType
from app.plugin_ids import COPY_PLUGIN_ID
from app.task_queue_manager import Task, TaskQueueManager


@pytest.fixture
def plugin_manager():
    manager = MagicMock()
    manager.get_plugin_by_id.return_value = None
    return manager


@pytest.fixture
def queue(qapp, plugin_manager):
    background_task_manager = MagicMock()
    background_task_manager.plugin_wrappers = {}
    return TaskQueueManager(
        file_manager=MagicMock(),
        directory_synchronizer=MagicMock(),
        plugin_manager=plugin_manager,
        background_task_manager=background_task_manager,
    )


def register_copy_plugin(plugin_manager):
    plugin = MagicMock()
    plugin.metadata = {"id": COPY_PLUGIN_ID}
    plugin_manager.get_plugin_by_id.side_effect = (
        lambda plugin_id: plugin if plugin_id == COPY_PLUGIN_ID else None
    )
    return plugin


def test_copy_task_with_correct_plugin_id_runs(queue, plugin_manager):
    plugin = register_copy_plugin(plugin_manager)
    task = Task(TaskType.COPY, ["/src/a"], "/dst", {"plugin_id": COPY_PLUGIN_ID})

    queue.add_task(task)

    plugin.execute_task.assert_called_once()
    assert task.status == TaskStatus.IN_PROGRESS


def test_copy_task_with_plugin_type_instead_of_id_still_runs(queue, plugin_manager):
    """Old dialogs passed the type; the queue must recover from it."""
    plugin = register_copy_plugin(plugin_manager)
    task = Task(
        TaskType.COPY,
        ["/src/a"],
        "/dst",
        {"plugin_id": "org.quickfile.standard_operations"},
    )

    queue.add_task(task)

    plugin.execute_task.assert_called_once_with(
        task_id=task.id,
        action_id=TaskType.COPY.value,
        options=task.options,
        source_paths=["/src/a"],
        destination_path="/dst",
    )
    assert task.status == TaskStatus.IN_PROGRESS


def test_copy_task_without_plugin_id_uses_task_type(queue, plugin_manager):
    plugin = register_copy_plugin(plugin_manager)
    task = Task(TaskType.COPY, ["/src/a"], "/dst", {})

    queue.add_task(task)

    plugin.execute_task.assert_called_once()
    assert task.status == TaskStatus.IN_PROGRESS


def test_task_fails_clearly_when_no_plugin_exists(queue, plugin_manager):
    task = Task(
        TaskType.COPY,
        ["/src/a"],
        "/dst",
        {"plugin_id": "org.quickfile.standard_operations"},
    )

    queue.add_task(task)

    assert task.status == TaskStatus.ERROR
    assert COPY_PLUGIN_ID in task.details
    assert task.id not in queue.active_tasks
