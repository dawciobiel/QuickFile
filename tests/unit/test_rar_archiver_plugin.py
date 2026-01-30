# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task

# Assume a test.rar file exists in the same directory as this test file.
# It should contain a single file 'test.txt' with content 'hello'.
TEST_RAR_PATH = os.path.join(os.path.dirname(__file__), 'test.rar')

@pytest.mark.skipif(not os.path.exists(TEST_RAR_PATH), reason="test.rar not found")
def test_extract_rar_success(tmp_path, async_plugin_test_env):
    """Tests successful RAR archive extraction."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.rar_archiver")

    dest_dir = tmp_path / "extracted"
    dest_dir.mkdir()

    options = {"plugin_id": "org.quickfile.rar_archiver"}
    task = Task(TaskType.EXTRACT_ARCHIVE, source_paths=[TEST_RAR_PATH], destination_path=str(dest_dir), options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="extract_archive",
        source_path=TEST_RAR_PATH,
        dest_dir=str(dest_dir),
        options=options
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for extract task")
    elif exit_code != 0:
        pytest.fail(f"Extract task failed: {async_helper.failed_error}")

    assert (dest_dir / "test.txt").exists()
    assert (dest_dir / "test.txt").read_text() == "hello"
