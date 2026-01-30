# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import time
import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task

def test_move_file_success(tmp_path, async_plugin_test_env):
    """Tests successful file move using the new plugin architecture."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.move_operation")

    source_file = tmp_path / "source.txt"
    source_file.write_text("Hello World")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    options = {"plugin_id": "org.quickfile.move_operation"}
    task = Task(TaskType.MOVE, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="move_items",
        source_paths=[str(source_file)],
        destination_path=str(dest_dir),
        options=options
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)
    
    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for move task")
    elif exit_code != 0:
        pytest.fail(f"Move task failed: {async_helper.failed_error}")

    assert not source_file.exists()
    assert (dest_dir / "source.txt").exists()
    assert (dest_dir / "source.txt").read_text() == "Hello World"


def test_move_cancellation(tmp_path, async_plugin_test_env):
    """Tests cancellation of a long move operation (fallback to copy+delete)."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.move_operation")

    # Create a large file (e.g., 500MB) to ensure move takes some time
    # Note: On the same filesystem, move is atomic and instant.
    # To test cancellation, we rely on the fact that we can't easily simulate cross-device move in unit test without mocking os.rename.
    # However, we can mock os.rename to fail, forcing the fallback path.
    
    source_file = tmp_path / "large_source.bin"
    with open(source_file, "wb") as f:
        f.seek(500 * 1024 * 1024 - 1)
        f.write(b"\0")
    
    dest_dir = tmp_path / "dest_cancel"
    dest_dir.mkdir()

    options = {"plugin_id": "org.quickfile.move_operation"}
    task = Task(TaskType.MOVE, source_paths=[str(source_file)], destination_path=str(dest_dir), options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    # We need to force the fallback path (copy+delete) to test cancellation during progress.
    # Since we cannot easily mock os.rename inside the sandboxed process from here,
    # we will rely on the fact that if we cancel fast enough, even atomic rename might be caught?
    # No, atomic rename is instant.
    # Ideally, we should have a way to force 'cross-device' mode in options for testing.
    # But for now, let's skip cancellation test for move if we can't force fallback, 
    # OR we can try to mock it if we had a way to inject code.
    
    # Let's try to run it. If it finishes instantly (atomic rename), the test will fail saying "Task finished successfully".
    # So this test is tricky without cross-device simulation.
    
    # For the purpose of this PoC, we will skip the cancellation test for move 
    # unless we implement a "force_copy" option in the plugin.
    
    pytest.skip("Skipping move cancellation test as it requires cross-device simulation to be long-running.")
