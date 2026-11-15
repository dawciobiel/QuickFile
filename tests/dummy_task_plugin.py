# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
A plugin written against the explicit task API (``TaskPlugin`` + ``PluginTask``).

It mirrors ``tests/dummy_plugin.py`` action by action, so the runtime tests can
run the same scenarios through both adapters and prove that the choice of style
changes nothing on the wire.
"""

import time

from app.plugin_system.api import PluginTask, TaskPlugin


class EchoTask(PluginTask):
    """Reports 100% and returns whatever it was given."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def run(self, ctx):
        ctx.progress(100)
        return {"echo": self.kwargs}


class ProgressTask(PluginTask):
    """Emits ``steps`` progress values with a small delay between them."""

    def __init__(self, steps=3, delay=0.0, **kwargs):
        self.steps = steps
        self.delay = delay

    def run(self, ctx):
        for step in range(1, self.steps + 1):
            ctx.wait_if_paused()
            ctx.check_cancelled()
            time.sleep(self.delay)
            ctx.progress(round(step * 100 / self.steps))
        return {"steps": self.steps}


class FailingTask(PluginTask):
    """Raises, so the runtime has to turn it into an ERROR."""

    def run(self, ctx):
        raise RuntimeError("dummy task failed on purpose")


class CancelAwareTask(PluginTask):
    """Raises TaskCancelled as soon as the host cancels the task."""

    def run(self, ctx):
        while True:
            ctx.check_cancelled()
            time.sleep(0.01)


class CancelIgnorantTask(PluginTask):
    """Never checks the context; the host must time out and kill the process."""

    def __init__(self, duration=60.0):
        self.duration = duration

    def run(self, ctx):
        time.sleep(self.duration)
        return {"ignored_cancel": True}


class EventTask(PluginTask):
    """Emits a domain event before finishing."""

    def run(self, ctx):
        ctx.event("item_found", {"path": "/tmp/found.txt"})
        return {"events": 1}


class InputTask(PluginTask):
    """Asks the host for input and returns the answer."""

    def run(self, ctx):
        return {"answer": ctx.request_input("ask", {"question": "value?"})}


class LoggingTask(PluginTask):
    """Sends a warning to the host log."""

    def run(self, ctx):
        ctx.log("warning", "dummy task says hello")
        return {"logged": True}


ACTIONS = {
    "echo": EchoTask,
    "progress": ProgressTask,
    "fail": FailingTask,
    "cancel_aware": CancelAwareTask,
    "cancel_ignorant": CancelIgnorantTask,
    "event": EventTask,
    "input": InputTask,
    "log": LoggingTask,
}


class DummyTaskPlugin(TaskPlugin):
    def get_name(self):
        return "Dummy Task Plugin"

    def get_description(self):
        return "Deterministic plugin written against the explicit task API."

    def get_menu_actions(self):
        return [{"action_id": action_id} for action_id in ACTIONS]

    def create_task(self, action_id, **kwargs):
        try:
            task_class = ACTIONS[action_id]
        except KeyError:
            raise ValueError(f"Unknown dummy action: {action_id}") from None
        return task_class(**kwargs)
