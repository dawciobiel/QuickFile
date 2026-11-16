# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for the bundled ``directory_size`` plugin.

The plugin is the replacement for the in-process scan that used to live in
``FileManager``: the action is now resolved through ``PLUGIN_ID_BY_ACTION`` and
runs in a sandboxed process through the explicit task API.

Specification: ``docs/architecture/plugins/plugins.md``.
"""

import importlib
import json
import os
import sys

import pytest

from app.plugin_system.api import PluginTask, TaskCancelled, TaskContext, TaskPlugin
from app.plugin_system.host import SandboxedPluginWrapper
from tests.plugin_helpers import get_latest_plugin_path

PLUGIN_GROUP = "org.quickfile"
PLUGIN_NAME = "directory_size"


class RecordingContext(TaskContext):
    """Records progress; optionally cancels the task after the first report."""

    def __init__(self, cancel_after_first_progress=False):
        self.task_id = "size-task"
        self.cancelled = False
        self.paused = False
        self.progress_values = []
        self.logs = []
        self.pause_checks = 0
        self._cancel_after_first_progress = cancel_after_first_progress

    def is_cancelled(self):
        return self.cancelled

    def is_paused(self):
        return self.paused

    def wait_if_paused(self):
        self.pause_checks += 1

    def progress(self, percentage):
        self.progress_values.append(percentage)
        if self._cancel_after_first_progress:
            self.cancelled = True

    def log(self, level, message):
        self.logs.append((level, message))


@pytest.fixture(scope="module")
def plugin_version_dir():
    return get_latest_plugin_path(PLUGIN_GROUP, PLUGIN_NAME)


@pytest.fixture
def plugin_modules(plugin_version_dir):
    """Imports ``plugin`` and ``tasks`` from the bundled version directory."""
    saved_modules = {name: sys.modules.pop(name, None) for name in ("plugin", "tasks")}
    sys.path.insert(0, plugin_version_dir)
    try:
        yield importlib.import_module("plugin")
    finally:
        sys.path.remove(plugin_version_dir)
        sys.modules.pop("plugin", None)
        sys.modules.pop("tasks", None)
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module


def make_task(plugin_modules, directory, **kwargs):
    return plugin_modules.DirectorySizePlugin().create_task(
        "calculate_directory_size", source_paths=[str(directory)], **kwargs
    )


# --- Contract ---------------------------------------------------------------


def test_directory_size_plugin_declares_the_explicit_task_api(plugin_modules):
    assert issubclass(plugin_modules.DirectorySizePlugin, TaskPlugin)
    assert isinstance(make_task(plugin_modules, "/tmp"), PluginTask)


def test_directory_size_plugin_rejects_an_unknown_action(plugin_modules):
    with pytest.raises(ValueError, match="Unknown action_id"):
        plugin_modules.DirectorySizePlugin().create_task("something_else")


# --- Behaviour --------------------------------------------------------------


def test_task_returns_the_total_size_and_reports_progress(plugin_modules, tmp_path):
    (tmp_path / "a.bin").write_bytes(b"a" * 1000)
    subdirectory = tmp_path / "sub"
    subdirectory.mkdir()
    (subdirectory / "b.bin").write_bytes(b"b" * 24)
    context = RecordingContext()

    result = make_task(plugin_modules, tmp_path).run(context)

    assert result == 1024
    assert context.progress_values[-1] == 100
    assert all(0 <= value <= 100 for value in context.progress_values)


def test_task_skips_symlinks_so_the_size_is_not_double_counted(
    plugin_modules, tmp_path
):
    target = tmp_path / "target.bin"
    target.write_bytes(b"x" * 32)
    os.symlink(target, tmp_path / "link.bin")
    context = RecordingContext()

    result = make_task(plugin_modules, tmp_path).run(context)

    assert result == 32


def test_task_raises_task_cancelled_when_the_context_says_so(plugin_modules, tmp_path):
    for index in range(20):
        (tmp_path / f"file-{index}.bin").write_bytes(b"x")
    context = RecordingContext(cancel_after_first_progress=True)

    with pytest.raises(TaskCancelled):
        make_task(plugin_modules, tmp_path).run(context)

    assert context.progress_values


# --- The same task over the real protocol -----------------------------------


def test_plugin_calculates_the_size_in_a_sandboxed_process(
    plugin_version_dir, tmp_path, qapp, qtbot
):
    (tmp_path / "a.bin").write_bytes(b"a" * 1000)
    (tmp_path / "b.bin").write_bytes(b"b" * 24)
    with open(
        os.path.join(plugin_version_dir, "metadata.json"), encoding="utf-8"
    ) as handle:
        metadata = json.load(handle)

    wrapper = SandboxedPluginWrapper(plugin_version_dir, metadata)
    wrapper.start()
    try:
        assert wrapper.is_ready()

        with qtbot.waitSignal(wrapper.method_finished, timeout=5000) as blocker:
            wrapper.execute_task(
                task_id="t1",
                action_id="calculate_directory_size",
                source_paths=[str(tmp_path)],
            )
    finally:
        wrapper.stop()

    assert blocker.args == ["t1", 1024]
