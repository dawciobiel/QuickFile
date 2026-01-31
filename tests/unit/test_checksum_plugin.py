# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task

def test_checksum_success(tmp_path, async_plugin_test_env):
    """Tests successful checksum calculation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.checksum_standard")

    source_file = tmp_path / "source.txt"
    source_file.write_text("Hello World")

    options = {
        "plugin_id": "org.quickfile.checksum_standard",
        "algorithms": ["md5", "sha256"]
    }
    task = Task(TaskType.CHECKSUM, source_paths=[str(source_file)], options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="calculate_checksum",
        source_paths=[str(source_file)], # Changed from file_path to source_paths
        algorithms=["md5", "sha256"]
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for checksum task")
    elif exit_code != 0:
        pytest.fail(f"Checksum task failed: {async_helper.failed_error}")

    _, results = async_helper.finished_result
    assert "md5" in results
    assert "sha256" in results
    assert results["md5"] == "b10a8db164e0754105b7a99be72e3fe5"
    assert results["sha256"] == "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"


def test_checksum_cancellation(tmp_path, async_plugin_test_env):
    """Tests cancellation of a checksum calculation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.checksum_standard")

    source_file = tmp_path / "large_source.bin"
    with open(source_file, "wb") as f:
        f.seek(100 * 1024 * 1024 - 1) # 100MB
        f.write(b"\0")
    
    options = {
        "plugin_id": "org.quickfile.checksum_standard",
        "algorithms": ["sha256"]
    }
    task = Task(TaskType.CHECKSUM, source_paths=[str(source_file)], options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="calculate_checksum",
        source_paths=[str(source_file)], # Changed from file_path to source_paths
        algorithms=["sha256"]
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
