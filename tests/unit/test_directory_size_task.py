# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for "calculate directory size".

The regression these tests exist for: ``FileManager.calculate_directory_size``
was fully implemented but never called. ``TaskQueueManager`` routed
``TaskType.CALCULATE_SIZE`` through the plugin queue, which rejected it with
"requires a 'plugin_id'" because no plugin implements that action.
"""

import os
import time
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt

from app.background_task_manager import BackgroundTaskManager
from app.enums import TaskStatus, TaskType
from app.task_queue_manager import Task, TaskQueueManager
from file_operations.file_manager import FileManager


class CancelledContext:
    is_cancelled = True


@pytest.fixture
def manager(qapp):
    instance = BackgroundTaskManager()
    yield instance
    instance.shutdown()


@pytest.fixture
def queue(qapp, manager):
    return TaskQueueManager(
        file_manager=FileManager(),
        directory_synchronizer=MagicMock(),
        plugin_manager=MagicMock(),
        background_task_manager=manager,
    )


def test_size_task_finishes_with_the_total_size(tmp_path, queue, qtbot):
    (tmp_path / "a.bin").write_bytes(b"a" * 1000)
    subdirectory = tmp_path / "sub"
    subdirectory.mkdir()
    (subdirectory / "b.bin").write_bytes(b"b" * 24)

    task = Task(TaskType.CALCULATE_SIZE, [str(tmp_path)])

    with qtbot.waitSignal(queue.task_finished, timeout=5000):
        queue.add_task(task)

    assert task.status is TaskStatus.FINISHED
    assert task.result == 1024
    assert task.progress == 100


def test_cancelling_a_size_task_ends_as_cancelled(tmp_path, queue, qtbot, monkeypatch):
    for index in range(50):
        (tmp_path / f"file-{index}.bin").write_bytes(b"x")

    real_getsize = os.path.getsize

    def slow_getsize(path):
        time.sleep(0.01)
        return real_getsize(path)

    monkeypatch.setattr("file_operations.file_manager.os.path.getsize", slow_getsize)

    task = Task(TaskType.CALCULATE_SIZE, [str(tmp_path)])
    task.progress_changed.connect(
        lambda _progress: queue.cancel_task(task.id),
        type=Qt.ConnectionType.DirectConnection,
    )

    with qtbot.waitSignal(queue.task_finished, timeout=10000):
        queue.add_task(task)

    assert task.status is TaskStatus.CANCELLED


def test_calculate_directory_size_reports_progress_through_the_callback(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 10)

    class RecordingCallback:
        """What ``Worker`` passes as ``progress_callback``: a Qt signal."""

        def __init__(self):
            self.values = []

        def emit(self, value):
            self.values.append(value)

    reported = RecordingCallback()

    size = FileManager().calculate_directory_size(
        str(tmp_path), progress_callback=reported
    )

    assert size == 10
    assert reported.values
    assert reported.values[-1] == 100


def test_calculate_directory_size_stops_when_the_context_is_cancelled(tmp_path):
    with pytest.raises(InterruptedError):
        FileManager().calculate_directory_size(
            str(tmp_path), task_context=CancelledContext()
        )
