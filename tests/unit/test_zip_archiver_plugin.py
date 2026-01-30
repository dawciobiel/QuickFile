# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import time
import zipfile

import pytest
from PyQt6.QtCore import QTimer

from app.enums import TaskType
from app.task_queue_manager import Task


def test_create_zip_success(tmp_path, async_plugin_test_env):
    """Tests successful ZIP archive creation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.zip_archiver")

    # Setup
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("Hello")
    (source_dir / "subdir").mkdir()
    (source_dir / "subdir" / "file2.txt").write_text("World")

    dest_path = tmp_path / "archive.zip"

    options = {"plugin_id": "org.quickfile.zip_archiver"}
    task = Task(TaskType.CREATE_ARCHIVE, source_paths=[str(source_dir)], destination_path=str(dest_path),
                options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="create_archive",
        source_paths=[str(source_dir)],
        destination_path=str(dest_path),
        options=options
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)

    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for zip task")
    elif exit_code != 0:
        pytest.fail(f"Zip task failed: {async_helper.failed_error}")

    assert dest_path.exists()
    with zipfile.ZipFile(dest_path, 'r') as zipf:
        assert "source/file1.txt" in zipf.namelist()
        assert "source/subdir/file2.txt" in zipf.namelist()


def test_create_zip_cancellation(tmp_path, async_plugin_test_env):
    """Tests cancellation of a ZIP archive creation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.zip_archiver")

    # Setup
    source_dir = tmp_path / "source_large"
    source_dir.mkdir()
    for i in range(1000):
        (source_dir / f"file_{i}.txt").write_text("some content")

    dest_path = tmp_path / "archive_cancelled.zip"

    options = {"plugin_id": "org.quickfile.zip_archiver"}
    task = Task(TaskType.CREATE_ARCHIVE, source_paths=[str(source_dir)], destination_path=str(dest_path),
                options=options)

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="create_archive",
        source_paths=[str(source_dir)],
        destination_path=str(dest_path),
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
