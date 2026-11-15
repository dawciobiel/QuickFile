# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for pausing and resuming a registered plugin task.

The regression these tests exist for: ``BackgroundTaskManager.resume_task``
read ``self.active_tasks`` (a ``TaskQueueManager`` attribute) and ``TaskStatus``
(not imported), so resuming a paused task from the queue raised
``AttributeError`` and left the task ``PAUSED`` forever. Pause worked, resume
never did.
"""

import threading
import time
from unittest.mock import MagicMock

import pytest

from app.background_task_manager import BackgroundTaskManager
from app.enums import TaskStatus, TaskType
from app.task_queue_manager import Task, TaskQueueManager


class FakeWrapper:
    """Records what the host was asked to do; no process involved."""

    def __init__(self):
        self.cancelled = []
        self.paused = []
        self.resumed = []

    def cancel_task(self, task_id):
        self.cancelled.append(task_id)

    def pause_task(self, task_id):
        self.paused.append(task_id)

    def resume_task(self, task_id):
        self.resumed.append(task_id)


@pytest.fixture
def manager(qapp):
    instance = BackgroundTaskManager()
    yield instance
    instance.shutdown()


@pytest.fixture
def queue(qapp, manager):
    return TaskQueueManager(
        file_manager=MagicMock(),
        directory_synchronizer=MagicMock(),
        plugin_manager=MagicMock(),
        background_task_manager=manager,
    )


def register(manager, wrapper):
    task = Task(TaskType.CHECKSUM, ["/tmp/source"])
    manager.register_plugin_task(task, wrapper)
    return task


def test_pause_task_forwards_to_the_plugin_wrapper(manager):
    wrapper = FakeWrapper()
    task = register(manager, wrapper)

    manager.pause_task(task.id)

    assert wrapper.paused == [task.id]
    assert task.context.is_paused()


def test_resume_task_forwards_to_the_plugin_wrapper(manager):
    wrapper = FakeWrapper()
    task = register(manager, wrapper)

    manager.pause_task(task.id)
    manager.resume_task(task.id)

    assert wrapper.resumed == [task.id]
    assert not task.context.is_paused()


def test_resume_task_of_an_unknown_task_is_a_no_op(manager):
    manager.resume_task("does-not-exist")  # must not raise


def test_resume_task_works_without_a_plugin_wrapper(manager):
    """In-process tasks register a context but no sandboxed wrapper."""
    task = register(manager, None)

    manager.pause_task(task.id)
    manager.resume_task(task.id)

    assert not task.context.is_paused()


def test_resume_wakes_a_worker_blocked_in_wait_if_paused(manager):
    task = register(manager, None)
    manager.pause_task(task.id)
    unblocked = threading.Event()

    def worker():
        task.context.wait_if_paused()
        unblocked.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        time.sleep(0.05)
        assert not unblocked.is_set(), "wait_if_paused returned while paused"

        manager.resume_task(task.id)

        assert unblocked.wait(1.0), "resume did not wake the waiting worker"
    finally:
        manager.resume_task(task.id)
        thread.join(1.0)


def test_queue_resume_moves_the_task_back_to_in_progress(queue, manager):
    wrapper = FakeWrapper()
    task = register(manager, wrapper)
    queue.active_tasks[task.id] = task

    queue.pause_task(task.id)
    assert task.status == TaskStatus.PAUSED

    queue.resume_task(task.id)

    assert task.status == TaskStatus.IN_PROGRESS
    assert wrapper.resumed == [task.id]
