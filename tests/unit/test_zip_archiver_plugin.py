# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
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


def test_create_zip_cancellation(tmp_path, async_plugin_test_env, qtbot):
    """Tests cancellation of a ZIP archive creation."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.zip_archiver")

    # Setup: 32 MB of incompressible data. The archive has to stay in flight
    # long enough for the cancel to arrive — 1000 tiny files finished in under
    # 50 ms on CI and the task completed before the cancel was sent.
    source_dir = tmp_path / "source_large"
    source_dir.mkdir()
    for i in range(32):
        (source_dir / f"file_{i}.bin").write_bytes(os.urandom(1024 * 1024))

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

    # Cancel only after the plugin has reported progress, i.e. while it is
    # actually writing. Sleeping for a fixed time raced the completion.
    qtbot.waitUntil(lambda: bool(async_helper.received_progress), timeout=5000)
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


def test_extract_zip_success(tmp_path, async_plugin_test_env):
    """Tests successful ZIP archive extraction through the plugin process."""
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.zip_archiver")

    source_zip = tmp_path / "source.zip"
    with zipfile.ZipFile(source_zip, "w") as zipf:
        zipf.writestr("file1.txt", "Hello")
        zipf.writestr("subdir/file2.txt", "World")

    dest_dir = tmp_path / "extracted"
    options = {"plugin_id": "org.quickfile.zip_archiver"}
    task = Task(
        TaskType.EXTRACT_ARCHIVE,
        source_paths=[str(source_zip)],
        destination_path=str(dest_dir),
        options=options,
    )

    background_task_manager.register_plugin_task(task, async_helper.plugin_wrapper)

    async_helper.plugin_wrapper.execute_task(
        task_id=task.id,
        action_id="extract_archive",
        source_path=str(source_zip),
        dest_dir=str(dest_dir),
        options=options,
    )

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: async_helper.task_finished_event.exit(3))
    timer.start(5000)

    exit_code = async_helper.task_finished_event.exec()
    timer.stop()

    if exit_code == 3:
        pytest.fail("Timeout waiting for zip extract task")
    elif exit_code != 0:
        pytest.fail(f"Zip extract task failed: {async_helper.failed_error}")

    assert (dest_dir / "file1.txt").read_text() == "Hello"
    assert (dest_dir / "subdir" / "file2.txt").read_text() == "World"
