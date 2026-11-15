# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for the plugin-side runtime, driven over a real (in-process) pipe.

No Qt, no subprocess and no filesystem: the runtime is started in a thread and
the test plays the host. That keeps the cancel/queue/ordering assertions fast
and deterministic while still exercising the actual IPC loop, the worker
thread and the message codec.

Specification: ``docs/architecture/plugins/runtime-protocol.md``.
"""

import multiprocessing
import threading
import time

import pytest

from app.plugin_system.protocol import (
    PROTOCOL_VERSION,
    ErrorCode,
    MessageType,
    decode,
    encode,
)
from app.plugin_system.runtime import (
    EXIT_OK,
    EXIT_PROTOCOL_ERROR,
    LegacyPluginAdapter,
    PluginRuntime,
    TaskPluginAdapter,
)
from tests.dummy_plugin import DummyPlugin
from tests.dummy_task_plugin import DummyTaskPlugin

PLUGIN_ID = "org.quickfile.dummy"
PLUGIN_VERSION = "0.1.0"

# Cancel must feel instant; the protocol target is 200 ms, the test allows
# scheduling noise on a loaded CI machine.
CANCEL_BUDGET = 0.5

#: Messages that are not interesting when waiting for a specific outcome.
NOISE = (MessageType.LOG, MessageType.PROGRESS, MessageType.EVENT)


class Host:
    """The host side of the pipe, in one small helper."""

    def __init__(self, connection):
        self.connection = connection

    def send(self, message_type, **fields):
        self.connection.send(encode(message_type, **fields))

    def send_raw(self, raw):
        self.connection.send(raw)

    def recv(self, timeout=2.0):
        if not self.connection.poll(timeout):
            raise AssertionError(f"No message within {timeout}s")
        return decode(self.connection.recv())

    def expect(self, message_type, timeout=2.0, ignore=(MessageType.LOG,)):
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

    def collect(self, duration=0.2):
        """Everything that arrives within ``duration``, excluding LOG."""
        deadline = time.monotonic() + duration
        messages = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return messages
            if not self.connection.poll(remaining):
                return messages
            message = decode(self.connection.recv())
            if message.type is not MessageType.LOG:
                messages.append(message)

    def handshake(self, protocol_min=PROTOCOL_VERSION, protocol_max=PROTOCOL_VERSION):
        self.send(
            MessageType.HELLO,
            protocol_min=protocol_min,
            protocol_max=protocol_max,
            plugin_id=PLUGIN_ID,
        )
        return self.expect(MessageType.READY)


class RuntimeHarness:
    def __init__(self, input_timeout=0.2, adapter=None):
        self.host_connection, self.plugin_connection = multiprocessing.Pipe()
        if adapter is None:
            adapter = LegacyPluginAdapter(DummyPlugin())
        self.runtime = PluginRuntime(
            self.plugin_connection,
            adapter,
            plugin_id=PLUGIN_ID,
            plugin_version=PLUGIN_VERSION,
            startup_timeout=1.0,
            shutdown_grace=1.0,
            input_timeout=input_timeout,
        )
        self.exit_code = None
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        self.host = Host(self.host_connection)

    def _serve(self):
        self.exit_code = self.runtime.serve()

    def wait_exit(self, timeout=2.0):
        self.thread.join(timeout)
        assert not self.thread.is_alive(), "runtime did not stop"
        return self.exit_code

    def close(self):
        if self.thread.is_alive():
            try:
                self.host.send(MessageType.SHUTDOWN)
            except (BrokenPipeError, OSError):
                pass
            self.thread.join(1.0)
        self.host_connection.close()
        self.plugin_connection.close()


@pytest.fixture
def harness():
    instance = RuntimeHarness()
    yield instance
    instance.close()


@pytest.fixture
def ready(harness):
    harness.host.handshake()
    return harness


@pytest.fixture
def explicit_harness():
    """The same runtime, serving a plugin written against the explicit API."""
    instance = RuntimeHarness(adapter=TaskPluginAdapter(DummyTaskPlugin()))
    yield instance
    instance.close()


@pytest.fixture
def explicit_ready(explicit_harness):
    explicit_harness.host.handshake()
    return explicit_harness


# --- Handshake --------------------------------------------------------------


def test_plugin_waits_for_hello_before_sending_ready(harness):
    assert harness.host.collect(0.15) == []
    assert harness.thread.is_alive()


def test_hello_is_answered_with_ready(harness):
    message = harness.host.handshake()

    assert message["protocol_version"] == PROTOCOL_VERSION
    assert message["plugin_id"] == PLUGIN_ID
    assert message["plugin_version"] == PLUGIN_VERSION
    assert "create_task" in message["methods"]
    assert "get_name" in message["methods"]


def test_ready_lists_only_public_methods(harness):
    methods = harness.host.handshake()["methods"]

    assert not [name for name in methods if name.startswith("_")]


def test_protocol_version_mismatch_is_reported_and_stops(harness):
    harness.host.send(
        MessageType.HELLO,
        protocol_min=2,
        protocol_max=3,
        plugin_id=PLUGIN_ID,
    )

    error = harness.host.expect(MessageType.ERROR)
    assert error["code"] == ErrorCode.PROTOCOL_MISMATCH
    assert harness.wait_exit() == EXIT_PROTOCOL_ERROR


def test_first_message_must_be_hello(harness):
    harness.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="echo")

    error = harness.host.expect(MessageType.ERROR)
    assert error["code"] == ErrorCode.PROTOCOL_ERROR
    assert "HELLO" in error["message"]
    assert harness.wait_exit() == EXIT_PROTOCOL_ERROR


# --- Tasks ------------------------------------------------------------------


def test_execute_task_returns_result(ready):
    ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="echo",
        kwargs={"hello": "world"},
    )

    progress = ready.host.expect(MessageType.PROGRESS)
    assert progress["task_id"] == "t1"
    assert progress["percent"] == 100

    result = ready.host.expect(MessageType.RESULT)
    assert result["task_id"] == "t1"
    assert result["value"] == {"echo": {"hello": "world"}}


def test_progress_is_reported_before_the_result(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="progress")

    messages = []
    while True:
        message = ready.host.recv()
        if message.type is MessageType.LOG:
            continue
        messages.append(message)
        if message.type is MessageType.RESULT:
            break

    assert [message.type for message in messages] == [
        MessageType.PROGRESS,
        MessageType.PROGRESS,
        MessageType.PROGRESS,
        MessageType.RESULT,
    ]
    assert [message["percent"] for message in messages[:-1]] == [33, 67, 100]


def test_domain_events_are_forwarded(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="event")

    event = ready.host.expect(MessageType.EVENT)
    assert event["name"] == "item_found"
    assert event["payload"] == {"path": "/tmp/found.txt"}

    result = ready.host.expect(MessageType.RESULT, ignore=NOISE)
    assert result["task_id"] == "t1"


def test_failing_task_reports_internal_error_with_a_traceback(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="fail")

    error = ready.host.expect(MessageType.ERROR)
    assert error["task_id"] == "t1"
    assert error["code"] == ErrorCode.INTERNAL
    assert "dummy task failed on purpose" in error["message"]
    assert "RuntimeError" in error["traceback"]


def test_unknown_action_fails_the_task_without_killing_the_runtime(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="no_such_action")

    error = ready.host.expect(MessageType.ERROR)
    assert error["code"] == ErrorCode.INTERNAL
    assert error["task_id"] == "t1"

    ready.host.send(MessageType.EXECUTE_TASK, task_id="t2", action_id="echo")
    assert ready.host.expect(MessageType.RESULT, ignore=NOISE)["task_id"] == "t2"


def test_duplicate_task_id_is_a_protocol_error(ready):
    ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="progress",
        kwargs={"steps": 40, "delay": 0.01},
    )
    time.sleep(0.1)
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="echo")

    error = ready.host.expect(MessageType.ERROR, ignore=NOISE)
    assert error["task_id"] == "t1"
    assert error["code"] == ErrorCode.PROTOCOL_ERROR

    ready.host.send(MessageType.CANCEL_TASK, task_id="t1")
    assert ready.host.expect(MessageType.CANCELLED, ignore=NOISE)["task_id"] == "t1"


# --- Cancellation -----------------------------------------------------------


def test_cancel_stops_a_running_task_quickly(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="cancel_aware")
    time.sleep(0.1)

    started = time.monotonic()
    ready.host.send(MessageType.CANCEL_TASK, task_id="t1")

    terminal = ready.host.expect(MessageType.CANCELLED, timeout=CANCEL_BUDGET)
    assert terminal["task_id"] == "t1"
    assert time.monotonic() - started < CANCEL_BUDGET


def test_cancel_of_a_queued_task_finishes_it_before_the_running_one(ready):
    # t1 keeps the worker busy; t2 waits in the queue.
    ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="progress",
        kwargs={"steps": 20, "delay": 0.02},
    )
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t2", action_id="echo")
    time.sleep(0.05)

    ready.host.send(MessageType.CANCEL_TASK, task_id="t2")

    cancelled = ready.host.expect(MessageType.CANCELLED, timeout=CANCEL_BUDGET, ignore=NOISE)
    assert cancelled["task_id"] == "t2"

    result = ready.host.expect(MessageType.RESULT, timeout=2.0, ignore=NOISE)
    assert result["task_id"] == "t1", "the cancelled queued task must not run"


def test_cancel_of_an_unknown_task_is_ignored(ready):
    ready.host.send(MessageType.CANCEL_TASK, task_id="ghost")

    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="echo")
    assert ready.host.expect(MessageType.RESULT, ignore=NOISE)["task_id"] == "t1"


# --- Pause and resume -------------------------------------------------------


def test_pause_holds_the_task_until_resume(ready):
    ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="progress",
        kwargs={"steps": 10, "delay": 0.02},
    )
    time.sleep(0.05)
    ready.host.send(MessageType.PAUSE_TASK, task_id="t1")
    time.sleep(0.2)

    assert not [
        message
        for message in ready.host.collect(0.2)
        if message.type is MessageType.RESULT
    ], "a paused task must not finish"

    ready.host.send(MessageType.RESUME_TASK, task_id="t1")
    assert (
        ready.host.expect(MessageType.RESULT, timeout=2.0, ignore=NOISE)["task_id"]
        == "t1"
    )


def test_cancelling_a_paused_task_wakes_it(ready):
    ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="progress",
        kwargs={"steps": 20, "delay": 0.02},
    )
    time.sleep(0.05)
    ready.host.send(MessageType.PAUSE_TASK, task_id="t1")
    time.sleep(0.15)

    started = time.monotonic()
    ready.host.send(MessageType.CANCEL_TASK, task_id="t1")

    terminal = ready.host.expect(MessageType.CANCELLED, timeout=CANCEL_BUDGET, ignore=NOISE)
    assert terminal["task_id"] == "t1"
    assert time.monotonic() - started < CANCEL_BUDGET


# --- Synchronous calls ------------------------------------------------------


def test_call_returns_a_value(ready):
    ready.host.send(MessageType.CALL, call_id="c1", method="get_name", args=[], kwargs={})

    response = ready.host.expect(MessageType.RETURN)
    assert response["call_id"] == "c1"
    assert response["ok"] is True
    assert response["value"] == "Dummy Plugin"


def test_call_to_an_unexposed_method_fails_without_killing_the_runtime(ready):
    ready.host.send(MessageType.CALL, call_id="c1", method="_private_helper")

    response = ready.host.expect(MessageType.RETURN)
    assert response["ok"] is False
    assert "_private_helper" in response["error"]

    ready.host.send(MessageType.CALL, call_id="c2", method="get_name")
    assert ready.host.expect(MessageType.RETURN)["call_id"] == "c2"


def test_call_waits_behind_a_running_task(ready):
    ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="progress",
        kwargs={"steps": 5, "delay": 0.02},
    )
    ready.host.send(MessageType.CALL, call_id="c1", method="get_name")

    first = ready.host.expect(MessageType.RESULT, timeout=2.0, ignore=NOISE)
    second = ready.host.expect(MessageType.RETURN, timeout=2.0, ignore=NOISE)
    assert first["task_id"] == "t1"
    assert second["call_id"] == "c1"


# --- Input request ----------------------------------------------------------


def test_input_request_is_answered_by_the_host(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="input")

    request = ready.host.expect(MessageType.INPUT_REQUEST)
    assert request["task_id"] == "t1"
    assert request["name"] == "ask"

    ready.host.send(
        MessageType.INPUT_RESPONSE,
        request_id=request["request_id"],
        value={"answer": 42},
    )

    result = ready.host.expect(MessageType.RESULT)
    assert result["value"] == {"answer": {"answer": 42}}


def test_unanswered_input_request_falls_back_to_an_empty_dict(ready):
    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="input")

    ready.host.expect(MessageType.INPUT_REQUEST)
    # Nothing is sent back; the runtime times out (input_timeout=0.2).
    result = ready.host.expect(MessageType.RESULT, timeout=2.0)
    assert result["value"] == {"answer": {}}


# --- Robustness -------------------------------------------------------------


def test_unknown_message_type_is_ignored(ready):
    ready.host.send_raw({"v": PROTOCOL_VERSION, "type": "FROM_THE_FUTURE", "x": 1})

    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="echo")
    assert ready.host.expect(MessageType.RESULT, ignore=NOISE)["task_id"] == "t1"


def test_message_in_the_wrong_direction_is_ignored(ready):
    ready.host.send(MessageType.PROGRESS, task_id="ghost", percent=50)

    ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="echo")
    assert ready.host.expect(MessageType.RESULT, ignore=NOISE)["task_id"] == "t1"


def test_malformed_message_is_reported_and_the_runtime_keeps_working(ready):
    ready.host.send_raw({"v": PROTOCOL_VERSION, "type": "EXECUTE_TASK", "task_id": "t1"})

    error = ready.host.expect(MessageType.ERROR)
    assert error["code"] == ErrorCode.PROTOCOL_ERROR
    assert "action_id" in error["message"]

    ready.host.send(MessageType.EXECUTE_TASK, task_id="t2", action_id="echo")
    assert ready.host.expect(MessageType.RESULT, ignore=NOISE)["task_id"] == "t2"


def test_a_non_mapping_message_is_reported(ready):
    ready.host.send_raw(b"not a message")

    error = ready.host.expect(MessageType.ERROR)
    assert error["code"] == ErrorCode.PROTOCOL_ERROR


# --- Lifecycle --------------------------------------------------------------


def test_shutdown_sends_bye_and_stops(harness):
    harness.host.handshake()

    harness.host.send(MessageType.SHUTDOWN)

    assert harness.host.expect(MessageType.BYE) is not None
    assert harness.wait_exit() == EXIT_OK


def test_host_disappearing_stops_the_runtime(ready):
    ready.host.connection.close()

    assert ready.wait_exit(timeout=2.0) == EXIT_OK


# --- The explicit task API over the same wire -------------------------------


def test_explicit_api_task_returns_a_result(explicit_ready):
    explicit_ready.host.send(
        MessageType.EXECUTE_TASK,
        task_id="t1",
        action_id="echo",
        kwargs={"payload": {"nested": [1, 2, 3]}},
    )

    result = explicit_ready.host.expect(MessageType.RESULT, ignore=NOISE)
    assert result["value"] == {"echo": {"payload": {"nested": [1, 2, 3]}}}


def test_explicit_api_task_reports_progress(explicit_ready):
    host = explicit_ready.host
    host.send(
        MessageType.EXECUTE_TASK, task_id="t1", action_id="progress", kwargs={"steps": 3}
    )

    progress = []
    while True:
        message = host.recv(2.0)
        if message.type is MessageType.PROGRESS:
            progress.append(message["percent"])
        elif message.type is MessageType.RESULT:
            break

    assert progress == [33, 67, 100]


def test_explicit_api_task_emits_events(explicit_ready):
    explicit_ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="event")

    event = explicit_ready.host.expect(MessageType.EVENT)
    assert event["name"] == "item_found"
    assert event["payload"] == {"path": "/tmp/found.txt"}


def test_explicit_api_cancel_becomes_cancelled_not_error(explicit_ready):
    explicit_ready.host.send(
        MessageType.EXECUTE_TASK, task_id="t1", action_id="cancel_aware"
    )
    time.sleep(0.1)

    started = time.monotonic()
    explicit_ready.host.send(MessageType.CANCEL_TASK, task_id="t1")

    cancelled = explicit_ready.host.expect(MessageType.CANCELLED, timeout=CANCEL_BUDGET)
    assert cancelled["task_id"] == "t1"
    assert time.monotonic() - started < CANCEL_BUDGET


def test_explicit_api_exception_becomes_an_error_with_a_traceback(explicit_ready):
    explicit_ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="fail")

    error = explicit_ready.host.expect(MessageType.ERROR)
    assert error["task_id"] == "t1"
    assert error["code"] == ErrorCode.INTERNAL
    assert "dummy task failed on purpose" in error["message"]
    assert "RuntimeError" in error["traceback"]


def test_explicit_api_log_reaches_the_host(explicit_ready):
    explicit_ready.host.send(MessageType.EXECUTE_TASK, task_id="t1", action_id="log")

    log = explicit_ready.host.expect(MessageType.LOG, ignore=())
    assert log["level"] == "warning"
    assert log["message"] == "dummy task says hello"
