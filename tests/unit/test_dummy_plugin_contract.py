# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The runtime tests spawn a real process, so the fixture they simulate has to be
a valid plugin. These checks keep ``tests/dummy_plugin.py`` honest: if the
plugin contract changes, this fails next to the runtime instead of deep inside
a subprocess traceback.
"""

import time

from app.plugin_system.api import AbstractTask, PluginBase, TaskContext
from tests.dummy_plugin import ACTIONS, DummyPlugin


class RecordingContext(TaskContext):
    def __init__(self):
        self.cancelled = False
        self.paused = False
        self.pause_checks = 0

    def is_cancelled(self):
        return self.cancelled

    def is_paused(self):
        return self.paused

    def wait_if_paused(self):
        self.pause_checks += 1


def make_task(action_id):
    plugin = DummyPlugin()
    task = plugin.create_task(action_id)
    context = RecordingContext()
    progress = []
    events = []
    task._initialize(context, progress.append, lambda name, payload: events.append((name, payload)), lambda n, p: {})
    return task, context, progress, events


def test_dummy_plugin_is_a_plugin_base():
    assert isinstance(DummyPlugin(), PluginBase)


def test_dummy_plugin_advertises_every_action_it_can_create():
    plugin = DummyPlugin()

    advertised = {action["action_id"] for action in plugin.get_menu_actions()}
    assert advertised == set(ACTIONS)

    for action_id in advertised:
        assert isinstance(plugin.create_task(action_id), AbstractTask)


def test_dummy_plugin_rejects_an_unknown_action():
    try:
        DummyPlugin().create_task("does_not_exist")
    except ValueError as error:
        assert "does_not_exist" in str(error)
    else:
        raise AssertionError("create_task accepted an unknown action")


def test_progress_task_reports_progress_and_returns():
    task, _, progress, _ = make_task("progress")

    result = task.run()

    assert result == {"steps": 3}
    assert progress == [33, 67, 100]


def test_progress_task_checks_for_pause():
    task, _, _, _ = make_task("progress")

    task.run()

    assert task.context.pause_checks == 3


def test_cancel_aware_task_stops_when_cancelled():
    task, context, _, _ = make_task("cancel_aware")
    context.cancelled = True

    started = time.monotonic()
    result = task.run()

    assert result == {"cancelled": True}
    assert time.monotonic() - started < 0.5


def test_event_task_emits_its_event():
    task, _, _, events = make_task("event")

    task.run()

    assert events == [("item_found", {"path": "/tmp/found.txt"})]
