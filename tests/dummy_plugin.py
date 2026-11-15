# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
A plugin that exists only for tests.

It implements the current ``PluginBase``/``AbstractTask`` contract and has
deterministic, dependency-free behaviour, so the runtime tests can spawn a real
process without touching Qt, the network or the user's files.
"""

import time

from app.plugin_system.api import AbstractTask, PluginBase


class EchoTask(AbstractTask):
    """Reports 100% and returns whatever it was given."""

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def run(self):
        self.emit_progress(100)
        return {"echo": self.kwargs}


class ProgressTask(AbstractTask):
    """Emits ``steps`` progress values with a small delay between them."""

    def __init__(self, steps=3, delay=0.0, **kwargs):
        super().__init__()
        self.steps = steps
        self.delay = delay

    def run(self):
        for step in range(1, self.steps + 1):
            self.context.wait_if_paused()
            if self.context.is_cancelled():
                return {"stopped_at": step}
            time.sleep(self.delay)
            self.emit_progress(round(step * 100 / self.steps))
        return {"steps": self.steps}


class FailingTask(AbstractTask):
    """Raises, so the runtime has to turn it into an ERROR."""

    def run(self):
        raise RuntimeError("dummy task failed on purpose")


class CancelAwareTask(AbstractTask):
    """Checks the context and returns as soon as it is cancelled."""

    def run(self):
        while not self.context.is_cancelled():
            time.sleep(0.01)
        return {"cancelled": True}


class CancelIgnorantTask(AbstractTask):
    """Never checks the context; the host must time out and kill the process."""

    def __init__(self, duration=60.0):
        super().__init__()
        self.duration = duration

    def run(self):
        time.sleep(self.duration)
        return {"ignored_cancel": True}


class EventTask(AbstractTask):
    """Emits a domain event before finishing."""

    def run(self):
        self.emit_event("item_found", {"path": "/tmp/found.txt"})
        return {"events": 1}


ACTIONS = {
    "echo": EchoTask,
    "progress": ProgressTask,
    "fail": FailingTask,
    "cancel_aware": CancelAwareTask,
    "cancel_ignorant": CancelIgnorantTask,
    "event": EventTask,
}


class DummyPlugin(PluginBase):
    def get_name(self):
        return "Dummy Plugin"

    def get_description(self):
        return "Deterministic plugin used by the runtime tests."

    def get_menu_actions(self):
        return [{"action_id": action_id} for action_id in ACTIONS]

    def create_task(self, action_id, **kwargs):
        try:
            task_class = ACTIONS[action_id]
        except KeyError:
            raise ValueError(f"Unknown dummy action: {action_id}") from None
        return task_class(**kwargs)
