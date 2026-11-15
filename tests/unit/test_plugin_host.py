# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for the host side of the runtime protocol.

These start a real plugin process from a temporary plugin directory. The plugin
body is a copy of ``tests/dummy_plugin.py``, so the test does not depend on any
bundled plugin and cannot be broken by changes to the shipped ones.

What matters here is the contract the rest of the application relies on:
``is_ready()``, ``execute_task()``, the four control methods, attribute-style
synchronous calls and the five Qt signals.
"""

import json
import os
import shutil
import time

import pytest

from app.plugin_system.host import SandboxedPluginWrapper

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DUMMY_PLUGIN_SOURCE = os.path.join(PROJECT_ROOT, "tests", "dummy_plugin.py")
PLUGIN_ID = "org.quickfile.dummy"
PLUGIN_VERSION = "0.1.0"


def _write_plugin(directory):
    version_dir = os.path.join(directory, "org.quickfile", "dummy", PLUGIN_VERSION)
    os.makedirs(version_dir)
    shutil.copyfile(DUMMY_PLUGIN_SOURCE, os.path.join(version_dir, "plugin.py"))

    metadata = {
        "id": PLUGIN_ID,
        "name": "Dummy Plugin",
        "version": PLUGIN_VERSION,
        "author": "QuickFile Team",
        "type": "checksum",
        "description": "Deterministic plugin used by the runtime tests.",
        "entry_point": "plugin:DummyPlugin",
        "class_name": "DummyPlugin",
        "sandboxed": True,
        "platforms": ["linux", "windows", "macos"],
    }
    with open(os.path.join(version_dir, "metadata.json"), "w", encoding="utf-8") as handle:
        json.dump(metadata, handle)

    return version_dir, metadata


@pytest.fixture
def plugin(tmp_path):
    return _write_plugin(str(tmp_path))


@pytest.fixture
def wrapper(plugin, qapp):
    path, metadata = plugin
    instance = SandboxedPluginWrapper(path, metadata)
    instance.start()
    yield instance
    instance.stop()


def test_start_completes_the_handshake(wrapper):
    assert wrapper.is_ready()
    assert "get_name" in wrapper._plugin_methods
    assert "create_task" in wrapper._plugin_methods


def test_attribute_call_returns_the_plugin_value(wrapper):
    assert wrapper.get_name() == "Dummy Plugin"


def test_attribute_call_serialises_arguments_and_results(wrapper):
    actions = wrapper.get_menu_actions()

    assert isinstance(actions, list)
    assert all(isinstance(action, dict) for action in actions)
    assert "echo" in {action["action_id"] for action in actions}


def test_unknown_attribute_fails_fast_on_a_live_plugin(wrapper):
    started = time.monotonic()
    with pytest.raises(AttributeError):
        wrapper.does_not_exist
    assert time.monotonic() - started < 0.5


def test_execute_task_emits_the_result(wrapper, qtbot):
    with qtbot.waitSignal(wrapper.method_finished, timeout=5000) as blocker:
        wrapper.execute_task(task_id="t1", action_id="echo", payload={"a": 1})

    assert blocker.args == ["t1", {"echo": {"payload": {"a": 1}}}]
    assert "t1" not in wrapper.active_tasks


def test_progress_is_emitted_before_the_result(wrapper, qtbot):
    progress = []
    wrapper.progress_updated.connect(lambda task_id, value: progress.append(value))

    with qtbot.waitSignal(wrapper.method_finished, timeout=5000):
        wrapper.execute_task(task_id="t1", action_id="progress")

    assert progress == [33, 67, 100]


def test_domain_events_reach_the_ui(wrapper, qtbot):
    events = []
    wrapper.data_event_received.connect(
        lambda task_id, name, payload: events.append((name, payload))
    )

    with qtbot.waitSignal(wrapper.method_finished, timeout=5000):
        wrapper.execute_task(task_id="t1", action_id="event")

    assert events == [("item_found", {"path": "/tmp/found.txt"})]


def test_failure_is_reported_with_the_plugin_message_and_traceback(wrapper, qtbot):
    with qtbot.waitSignal(wrapper.method_failed, timeout=5000) as blocker:
        wrapper.execute_task(task_id="t1", action_id="fail")

    task_id, error, traceback_text = blocker.args
    assert task_id == "t1"
    assert "dummy task failed on purpose" in error
    assert "RuntimeError" in traceback_text


def test_cancel_reports_the_task_as_cancelled(wrapper, qtbot):
    wrapper.execute_task(task_id="t1", action_id="cancel_aware")
    time.sleep(0.1)

    started = time.monotonic()
    with qtbot.waitSignal(wrapper.method_failed, timeout=2000) as blocker:
        wrapper.cancel_task("t1")

    assert list(blocker.args[:2]) == ["t1", "Task cancelled"]
    assert time.monotonic() - started < 0.5


def test_pause_and_resume_keep_the_task_alive(wrapper, qtbot):
    wrapper.execute_task(
        task_id="t1", action_id="progress", steps=20, delay=0.02
    )
    time.sleep(0.05)
    wrapper.pause_task("t1")
    time.sleep(0.1)

    with qtbot.waitSignal(wrapper.method_finished, timeout=2000):
        wrapper.resume_task("t1")

    assert "t1" not in wrapper.active_tasks


def test_several_tasks_on_one_plugin_run_in_order(wrapper, qtbot):
    results = []
    wrapper.method_finished.connect(lambda task_id, _value: results.append(task_id))

    with qtbot.waitSignal(wrapper.method_finished, timeout=5000):
        wrapper.execute_task(task_id="t1", action_id="echo")
        wrapper.execute_task(task_id="t2", action_id="echo")

    qtbot.waitUntil(lambda: len(results) == 2, timeout=5000)
    assert results == ["t1", "t2"]


def test_stop_terminates_the_process(wrapper):
    process = wrapper.process

    wrapper.stop()

    assert not process.is_alive()
    assert not wrapper.is_ready()


def test_a_crash_fails_every_active_task(wrapper, qtbot):
    wrapper.execute_task(task_id="t1", action_id="cancel_ignorant", duration=60.0)
    time.sleep(0.1)

    with qtbot.waitSignal(wrapper.method_failed, timeout=5000) as blocker:
        wrapper.process.terminate()

    task_id, error, _traceback = blocker.args
    assert task_id == "t1"
    assert "crashed" in error.lower()
    assert not wrapper.is_ready()


def test_execute_after_stop_fails_the_task_instead_of_raising(wrapper):
    wrapper.stop()
    failures = []
    wrapper.method_failed.connect(
        lambda task_id, error, _tb: failures.append((task_id, error))
    )

    wrapper.execute_task(task_id="t1", action_id="echo")

    assert failures == [("t1", "Plugin is not available")]


def test_a_plugin_that_cannot_load_is_not_ready_and_does_not_hang(tmp_path, qapp):
    path, metadata = _write_plugin(str(tmp_path))
    with open(os.path.join(path, "plugin.py"), "w", encoding="utf-8") as handle:
        handle.write("raise RuntimeError('broken plugin')\n")

    instance = SandboxedPluginWrapper(path, metadata)
    started = time.monotonic()
    instance.start()

    assert not instance.is_ready()
    assert time.monotonic() - started < instance.STARTUP_TIMEOUT

    instance.stop()


def test_the_wrapper_can_be_started_again_after_stop(plugin, qapp):
    path, metadata = plugin
    instance = SandboxedPluginWrapper(path, metadata)

    instance.start()
    assert instance.is_ready()
    instance.stop()
    assert not instance.is_ready()

    instance.start()
    try:
        assert instance.is_ready()
        assert instance.get_name() == "Dummy Plugin"
    finally:
        instance.stop()
