# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task

def test_copy_file_success(tmp_path, async_plugin_test_env):
    """Tests successful file copy using the new plugin architecture."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.copy_operation")

    source_file = tmp_path / "source.txt"
    source_file.write_text("Hello World")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    options = {"plugin_id": "org.quickfile.copy_operation"}
    task = Task(TaskType.COPY, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)

    # Register task context
    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="copy_items",
        source_paths=[str(source_file)],
        destination_path=str(dest_dir),
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
        pytest.fail("Timeout waiting for copy task")
    elif exit_code != 0:
        pytest.fail(f"Copy task failed: {async_helper.failed_error}")

    assert (dest_dir / "source.txt").exists()
    assert (dest_dir / "source.txt").read_text() == "Hello World"


def test_copy_cancellation(tmp_path, async_plugin_test_env):
    """Tests cancellation of a long copy operation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.copy_operation")

    # Create a large file (e.g., 500MB) to ensure copy takes some time
    source_file = tmp_path / "large_source.bin"
    with open(source_file, "wb") as f:
        f.seek(500 * 1024 * 1024 - 1)
        f.write(b"\0")
    
    dest_dir = tmp_path / "dest_cancel"
    dest_dir.mkdir()

    options = {"plugin_id": "org.quickfile.copy_operation"}
    task = Task(TaskType.COPY, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="copy_items",
        source_paths=[str(source_file)],
        destination_path=str(dest_dir),
        options=options
    )

    # Wait a bit for the operation to start, but not too long
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

    # Verify that the file was NOT fully copied (or cleaned up)
    # Note: In our implementation, we clean up if cancelled during file copy
    dest_file = dest_dir / "large_source.bin"
    if dest_file.exists():
        assert dest_file.stat().st_size < source_file.stat().st_size
