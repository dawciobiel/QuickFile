# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task

def test_basic_search(tmp_path, async_plugin_test_env):
    """Tests basic search functionality."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    # Setup test files
    (tmp_path / "test.txt").touch()
    (tmp_path / "another.log").touch()
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "test2.txt").touch()

    options = {
        "plugin_id": "org.quickfile.search_standard",
        "file_name": "*.txt"
    }
    task = Task(TaskType.SEARCH, source_paths=[str(tmp_path)], options=options)

    # Listen for data events
    found_items = []
    async_helper.plugin_wrapper.data_event_received.connect(
        lambda task_id, event_name, payload: found_items.append(payload['path']) if event_name == 'item_found' else None
    )

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)
    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="search",
        start_path=str(tmp_path),
        options=options
    )

    # Wait for completion
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for search task")
    elif exit_code != 0:
        pytest.fail(f"Search task failed: {async_helper.failed_error}")

    assert len(found_items) == 2
    assert str(tmp_path / "test.txt") in found_items
    assert str(tmp_path / "subdir" / "test2.txt") in found_items


def test_search_cancellation(tmp_path, async_plugin_test_env):
    """Tests cancellation of a search operation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    # Create a deep directory structure to make search longer
    base_path = tmp_path
    for i in range(10):
        base_path = base_path / f"dir_{i}"
        base_path.mkdir()
        for j in range(1000): # Zwiększono liczbę plików
            (base_path / f"file_{j}.txt").touch()

    options = {
        "plugin_id": "org.quickfile.search_standard",
        "file_name": "*.txt"
    }
    task = Task(TaskType.SEARCH, source_paths=[str(tmp_path)], options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="search",
        start_path=str(tmp_path),
        options=options
    )

    time.sleep(0.05)
    background_task_manager.cancel_task(task.id)

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for task cancellation")
    elif exit_code == 0:
        pytest.fail("Task finished successfully instead of being cancelled")
    elif exit_code == 1:
        _, error, _ = async_helper.failed_error
        assert "cancelled" in error.lower() or "InterruptedError" in error
