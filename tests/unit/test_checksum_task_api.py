# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The checksum plugin is the first bundled plugin written against the explicit
task API. These tests load its modules the same way the host does (the version
directory on ``sys.path``) but without a process or a pipe, so the loop's
progress and cancellation behaviour can be checked directly.

Specification: ``docs/architecture/plugins/plugins.md`` ("Kontrakt zadań").
"""

import hashlib
import importlib
import sys

import pytest

from app.plugin_system.api import (
    PluginTask,
    TaskCancelled,
    TaskContext,
    TaskPlugin,
)
from tests.plugin_helpers import get_latest_plugin_path

PLUGIN_GROUP = "org.quickfile"
PLUGIN_NAME = "checksum_standard"


class RecordingContext(TaskContext):
    """Records progress; optionally cancels the task after the first report."""

    def __init__(self, cancel_after_first_progress=False):
        self.task_id = "checksum-task"
        self.cancelled = False
        self.paused = False
        self.progress_values = []
        self._cancel_after_first_progress = cancel_after_first_progress

    def is_cancelled(self):
        return self.cancelled

    def is_paused(self):
        return self.paused

    def wait_if_paused(self):
        pass

    def progress(self, percentage):
        self.progress_values.append(percentage)
        if self._cancel_after_first_progress:
            self.cancelled = True


@pytest.fixture
def checksum_plugin_modules():
    """Imports ``plugin`` and ``tasks`` from the bundled version directory."""
    version_dir = get_latest_plugin_path(PLUGIN_GROUP, PLUGIN_NAME)
    saved_modules = {name: sys.modules.pop(name, None) for name in ("plugin", "tasks")}
    sys.path.insert(0, version_dir)
    try:
        plugin = importlib.import_module("plugin")
        yield plugin
    finally:
        sys.path.remove(version_dir)
        sys.modules.pop("plugin", None)
        sys.modules.pop("tasks", None)
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module


def test_checksum_plugin_declares_the_explicit_task_api(checksum_plugin_modules):
    plugin_class = checksum_plugin_modules.ChecksumPlugin

    assert issubclass(plugin_class, TaskPlugin)
    assert isinstance(
        plugin_class().create_task(
            "calculate_checksum", source_paths=["/tmp/anything"], algorithms=["md5"]
        ),
        PluginTask,
    )


def test_checksum_task_returns_hex_digests_and_reports_progress(
    checksum_plugin_modules, tmp_path
):
    source = tmp_path / "source.txt"
    source.write_bytes(b"Hello World")
    task = checksum_plugin_modules.ChecksumPlugin().create_task(
        "calculate_checksum",
        source_paths=[str(source)],
        algorithms=["md5", "sha256", "crc32"],
    )
    context = RecordingContext()

    result = task.run(context)

    assert result["md5"] == hashlib.md5(b"Hello World").hexdigest()
    assert result["sha256"] == hashlib.sha256(b"Hello World").hexdigest()
    assert result["crc32"] == "4a17b156"
    assert context.progress_values == [100]


def test_checksum_task_raises_task_cancelled_when_the_context_says_so(
    checksum_plugin_modules, tmp_path
):
    source = tmp_path / "large.bin"
    source.write_bytes(b"\0" * (256 * 1024))  # four 64 KiB chunks
    task = checksum_plugin_modules.ChecksumPlugin().create_task(
        "calculate_checksum", source_paths=[str(source)], algorithms=["sha256"]
    )
    context = RecordingContext(cancel_after_first_progress=True)

    with pytest.raises(TaskCancelled):
        task.run(context)

    # Cancelled during the second chunk: one progress report, no result.
    assert context.progress_values == [25]
