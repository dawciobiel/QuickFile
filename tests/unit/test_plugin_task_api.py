# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for the explicit task API and the adapter that selects it.

Nothing here starts a process or touches Qt: the API is a plain Python contract,
and the adapter is the only place that knows about both styles. The runtime
tests in ``test_plugin_runtime.py`` cover the same plugin over a real pipe.

Specification: ``docs/architecture/plugins/plugins.md`` ("Kontrakt zadań").
"""

import pytest

from app.plugin_system.api import (
    AbstractTask,
    PluginBase,
    PluginTask,
    TaskCancelled,
    TaskContext,
    TaskPlugin,
)
from app.plugin_system.runtime import (
    LegacyPluginAdapter,
    TaskPluginAdapter,
    adapter_for,
)
from tests.dummy_plugin import DummyPlugin
from tests.dummy_task_plugin import ACTIONS, DummyTaskPlugin


class RecordingContext(TaskContext):
    """A context that records everything the task does with it."""

    def __init__(self, cancelled=False):
        self.task_id = "task-1"
        self.cancelled = cancelled
        self.paused = False
        self.progress_values = []
        self.events = []
        self.inputs = []
        self.logs = []
        self.pause_checks = 0

    def is_cancelled(self):
        return self.cancelled

    def is_paused(self):
        return self.paused

    def wait_if_paused(self):
        self.pause_checks += 1

    def progress(self, percent):
        self.progress_values.append(percent)

    def event(self, name, payload=None):
        self.events.append((name, payload))

    def request_input(self, name, payload=None):
        self.inputs.append((name, payload))
        return {"answer": 42}

    def log(self, level, message):
        self.logs.append((level, message))


# --- The contract a task author sees ----------------------------------------


def test_the_context_is_passed_to_run_as_an_argument():
    context = RecordingContext()

    result = ACTIONS["progress"](steps=4).run(context)

    assert result == {"steps": 4}
    assert context.progress_values == [25, 50, 75, 100]
    # Pause is checked once per step, and the task never touches self.context.
    assert context.pause_checks == 4


def test_a_task_returns_its_result_instead_of_storing_it():
    task = ACTIONS["echo"](payload={"a": 1})

    assert task.run(RecordingContext()) == {"echo": {"payload": {"a": 1}}}


def test_check_cancelled_raises_a_dedicated_exception():
    context = RecordingContext(cancelled=True)

    with pytest.raises(TaskCancelled):
        ACTIONS["cancel_aware"]().run(context)


def test_check_cancelled_is_silent_when_the_task_is_alive():
    RecordingContext().check_cancelled()  # must not raise


def test_a_task_can_ask_the_host_for_input():
    context = RecordingContext()

    assert ACTIONS["input"]().run(context) == {"answer": {"answer": 42}}
    assert context.inputs == [("ask", {"question": "value?"})]


def test_a_task_can_report_events_and_logs():
    context = RecordingContext()

    ACTIONS["event"]().run(context)
    ACTIONS["log"]().run(context)

    assert context.events == [("item_found", {"path": "/tmp/found.txt"})]
    assert context.logs == [("warning", "dummy task says hello")]


# --- The plugin author's base classes ---------------------------------------


def test_a_task_plugin_is_still_a_plugin_base():
    """The host rejects anything that is not a PluginBase."""
    assert isinstance(DummyTaskPlugin(), PluginBase)


def test_plugin_task_is_not_an_abstract_task():
    """The two styles must stay distinguishable, not inherit from each other."""
    assert not issubclass(PluginTask, AbstractTask)
    assert not issubclass(AbstractTask, PluginTask)


def test_dummy_task_plugin_advertises_every_action_it_can_create():
    plugin = DummyTaskPlugin()

    advertised = {action["action_id"] for action in plugin.get_menu_actions()}
    assert advertised == set(ACTIONS)

    for action_id in advertised:
        assert isinstance(plugin.create_task(action_id), PluginTask)


def test_dummy_task_plugin_rejects_an_unknown_action():
    with pytest.raises(ValueError, match="Unknown dummy action"):
        DummyTaskPlugin().create_task("does_not_exist")


# --- Adapter selection ------------------------------------------------------


def test_adapter_for_picks_the_explicit_adapter():
    assert isinstance(adapter_for(DummyTaskPlugin()), TaskPluginAdapter)


def test_adapter_for_picks_the_legacy_adapter():
    assert isinstance(adapter_for(DummyPlugin()), LegacyPluginAdapter)


def test_adapter_for_rejects_something_that_is_not_a_plugin():
    with pytest.raises(TypeError, match="PluginBase"):
        adapter_for(object())


# --- What the explicit adapter does -----------------------------------------


def test_the_adapter_runs_the_task_with_the_runtime_context():
    context = RecordingContext()
    adapter = TaskPluginAdapter(DummyTaskPlugin())

    task = adapter.create_task("progress", {"steps": 2}, context)

    assert task.run() == {"steps": 2}
    assert context.progress_values == [50, 100]


def test_the_adapter_passes_kwargs_to_the_plugin_factory():
    adapter = TaskPluginAdapter(DummyTaskPlugin())

    task = adapter.create_task("echo", {"payload": {"b": 2}}, RecordingContext())

    assert task.run() == {"echo": {"payload": {"b": 2}}}


def test_the_adapter_rejects_a_task_of_the_legacy_style():
    class ConfusedPlugin(TaskPlugin):
        def get_name(self):
            return "Confused"

        def get_description(self):
            return "Declares TaskPlugin but returns an AbstractTask."

        def create_task(self, action_id, **kwargs):
            class LegacyTask(AbstractTask):
                def run(self):
                    return None

            return LegacyTask()

    adapter = TaskPluginAdapter(ConfusedPlugin())

    with pytest.raises(TypeError, match="PluginTask"):
        adapter.create_task("anything", {}, RecordingContext())


def test_the_adapter_reports_an_unknown_action_as_a_plugin_error():
    adapter = TaskPluginAdapter(DummyTaskPlugin())

    with pytest.raises(ValueError, match="Unknown dummy action"):
        adapter.create_task("does_not_exist", {}, RecordingContext())
