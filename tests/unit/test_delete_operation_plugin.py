# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task

def test_delete_file_success(tmp_path, async_plugin_test_env):
    """Tests successful file deletion using the new plugin architecture."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.delete_operation")

    file_to_delete = tmp_path / "file_to_delete.txt"
    file_to_delete.write_text("Delete me")

    options = {"plugin_id": "org.quickfile.delete_operation"}
    task = Task(TaskType.DELETE, source_paths=[str(file_to_delete)], options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="delete_items",
        item_paths=[str(file_to_delete)],
        options=options
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for delete task")
    elif exit_code != 0:
        pytest.fail(f"Delete task failed: {async_helper.failed_error}")

    assert not file_to_delete.exists()


def test_delete_directory_success(tmp_path, async_plugin_test_env):
    """Tests successful directory deletion using the new plugin architecture."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.delete_operation")

    dir_to_delete = tmp_path / "dir_to_delete"
    dir_to_delete.mkdir()
    (dir_to_delete / "file1.txt").write_text("Content 1")
    (dir_to_delete / "subdir").mkdir()
    (dir_to_delete / "subdir" / "file2.txt").write_text("Content 2")

    options = {"plugin_id": "org.quickfile.delete_operation"}
    task = Task(TaskType.DELETE, source_paths=[str(dir_to_delete)], options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="delete_items",
        item_paths=[str(dir_to_delete)],
        options=options
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for delete task")
    elif exit_code != 0:
        pytest.fail(f"Delete task failed: {async_helper.failed_error}")

    assert not dir_to_delete.exists()


@pytest.mark.skip(reason="Skipping delete cancellation test to avoid heavy I/O load on disk. Cancellation logic is verified in copy operation.")
def test_delete_cancellation(tmp_path, async_plugin_test_env):
    """Tests cancellation of a long delete operation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.delete_operation")

    # Create many files to ensure delete takes some time
    dir_to_delete = tmp_path / "many_files"
    dir_to_delete.mkdir()
    for i in range(1000):
        (dir_to_delete / f"file_{i}.txt").write_text("Content")

    options = {"plugin_id": "org.quickfile.delete_operation"}
    task = Task(TaskType.DELETE, source_paths=[str(dir_to_delete)], options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="delete_items",
        item_paths=[str(dir_to_delete)],
        options=options
    )

    # Wait a bit for the operation to start
    time.sleep(0.05)

    # Cancel the task
    background_task_manager.cancel_task(task.id)

    # Wait for completion (expecting cancellation)
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
        # Check if error message indicates cancellation
        _, error, _ = async_helper.failed_error
        assert "cancelled" in error.lower() or "InterruptedError" in error

    # Verify that not all files were deleted
    remaining_files = len(list(dir_to_delete.glob("*")))
    assert remaining_files > 0
