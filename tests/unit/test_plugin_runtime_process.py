# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The runtime tests in ``test_plugin_runtime.py`` run the runtime in a thread.
These two run it in a real child process, which is the only way to catch
problems with argument/result serialization and with ``serve()`` returning an
exit code the host can rely on.

The child is forked, so it inherits the test module and the dummy plugin.
"""

import multiprocessing
import time

import pytest

from app.plugin_system.protocol import MessageType, decode, encode
from app.plugin_system.runtime import (
    LegacyPluginAdapter,
    PluginRuntime,
    TaskPluginAdapter,
)
from tests.dummy_plugin import DummyPlugin
from tests.dummy_task_plugin import DummyTaskPlugin

PLUGIN_ID = "org.quickfile.dummy"
PLUGIN_VERSION = "0.1.0"
CANCEL_BUDGET = 1.0

pytestmark = pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="the test child is forked and needs the in-memory plugin instance",
)


def _run_child(connection, explicit_api=False):
    if explicit_api:
        adapter = TaskPluginAdapter(DummyTaskPlugin())
    else:
        adapter = LegacyPluginAdapter(DummyPlugin())
    runtime = PluginRuntime(
        connection,
        adapter,
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        startup_timeout=2.0,
        shutdown_grace=2.0,
    )
    runtime.serve()


class Child:
    def __init__(self, explicit_api=False):
        context = multiprocessing.get_context("fork")
        self.parent_connection, child_connection = context.Pipe()
        self.process = context.Process(
            target=_run_child, args=(child_connection, explicit_api)
        )
        self.process.daemon = True
        self.process.start()
        child_connection.close()

    def send(self, message_type, **fields):
        self.parent_connection.send(encode(message_type, **fields))

    def recv(self, timeout=3.0):
        if not self.parent_connection.poll(timeout):
            raise AssertionError(f"No message within {timeout}s")
        return decode(self.parent_connection.recv())

    def expect(self, message_type, timeout=3.0, ignore=(MessageType.LOG,)):
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"No {message_type} within {timeout}s")
            message = self.recv(remaining)
            if message.type in ignore:
                continue
            assert message.type is message_type, f"Expected {message_type}, got {message.type}"
            return message

    def handshake(self):
        self.send(
            MessageType.HELLO,
            protocol_min=1,
            protocol_max=1,
            plugin_id=PLUGIN_ID,
        )
        return self.expect(MessageType.READY)

    def close(self):
        if self.process.is_alive():
            self.process.terminate()
        self.process.join(3)
        self.parent_connection.close()


@pytest.fixture
def child():
    instance = Child()
    yield instance
    instance.close()


def test_real_process_runs_a_task_and_exits_cleanly(child):
    ready = child.handshake()
    assert ready["plugin_id"] == PLUGIN_ID

    child.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="echo",
        kwargs={"payload": {"nested": [1, 2, 3]}},
    )
    result = child.expect(MessageType.RESULT, ignore=(MessageType.LOG, MessageType.PROGRESS))
    assert result["value"] == {"echo": {"payload": {"nested": [1, 2, 3]}}}

    child.send(MessageType.SHUTDOWN)
    assert child.expect(MessageType.BYE) is not None
    child.process.join(3)
    assert not child.process.is_alive()
    assert child.process.exitcode == 0


def test_real_process_cancels_a_running_task_and_stays_usable(child):
    child.handshake()
    child.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="cancel_aware")
    time.sleep(0.2)

    started = time.monotonic()
    child.send(MessageType.CANCEL_TASK, task_id="t1")
    cancelled = child.expect(MessageType.CANCELLED, timeout=CANCEL_BUDGET)
    assert cancelled["task_id"] == "t1"
    assert time.monotonic() - started < CANCEL_BUDGET

    child.send(MessageType.EXECUTE_TASK, task_id="t2", action_id="echo")
    result = child.expect(
        MessageType.RESULT, timeout=3.0, ignore=(MessageType.LOG, MessageType.PROGRESS)
    )
    assert result["task_id"] == "t2"


def test_real_process_runs_a_task_from_the_explicit_api_and_cancels():
    child = Child(explicit_api=True)
    try:
        child.handshake()

        child.send(
            MessageType.EXECUTE_TASK,
            task_id="t1",
            action_id="echo",
            kwargs={"payload": {"nested": [1, 2, 3]}},
        )
        result = child.expect(
            MessageType.RESULT, ignore=(MessageType.LOG, MessageType.PROGRESS)
        )
        assert result["value"] == {"echo": {"payload": {"nested": [1, 2, 3]}}}

        child.send(MessageType.EXECUTE_TASK, task_id="t2", action_id="cancel_aware")
        time.sleep(0.2)
        child.send(MessageType.CANCEL_TASK, task_id="t2")

        cancelled = child.expect(MessageType.CANCELLED, timeout=CANCEL_BUDGET)
        assert cancelled["task_id"] == "t2"

        child.send(MessageType.SHUTDOWN)
        assert child.expect(MessageType.BYE) is not None
        child.process.join(3)
        assert child.process.exitcode == 0
    finally:
        child.close()
