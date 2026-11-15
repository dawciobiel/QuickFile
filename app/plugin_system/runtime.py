# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The plugin side of the runtime protocol (v1).

One plugin process has exactly two long-lived threads plus transient task work:

* the **IPC thread** only reads messages and updates task state; it never runs
  plugin code, so ``CANCEL_TASK`` is not queued behind a long copy,
* the **worker thread** executes queued jobs one at a time. A job is either a
  task (``EXECUTE_TASK``) or a cheap query (``CALL``).

Plugin code never touches the connection. It sees a ``TaskContext`` whose
callbacks turn into ``PROGRESS`` / ``EVENT`` / ``RESULT`` messages, exactly as
before, so existing ``PluginBase`` implementations keep working through
``LegacyPluginAdapter``.
"""

from __future__ import annotations

import collections
import logging
import threading
import traceback
import uuid
from typing import Any, Iterable, Mapping

from .api import AbstractTask, PluginBase, TaskContext
from .protocol import (
    PROTOCOL_VERSION,
    SUPPORTED_VERSIONS,
    Direction,
    ErrorCode,
    InvalidMessage,
    Message,
    MessageType,
    UnknownMessageType,
    UnsupportedVersion,
    decode,
    direction_of,
    encode,
    negotiate_version,
)

DEFAULT_STARTUP_TIMEOUT = 5.0
DEFAULT_SHUTDOWN_GRACE = 2.0
DEFAULT_INPUT_TIMEOUT = 30.0

EXIT_OK = 0
EXIT_INTERNAL_ERROR = 1
EXIT_PROTOCOL_ERROR = 2

#: How long the worker sleeps between checks when idle.
_IDLE_POLL = 0.05


class _TaskJob:
    __slots__ = ("task_id", "action_id", "kwargs", "context")

    def __init__(self, task_id: str, action_id: str, kwargs: Mapping[str, Any], context: "TaskBridge"):
        self.task_id = task_id
        self.action_id = action_id
        self.kwargs = dict(kwargs)
        self.context = context


class _CallJob:
    __slots__ = ("call_id", "method", "args", "kwargs")

    def __init__(self, call_id: str, method: str, args: list, kwargs: Mapping[str, Any]):
        self.call_id = call_id
        self.method = method
        self.args = list(args)
        self.kwargs = dict(kwargs)


class _PendingInput:
    __slots__ = ("event", "value")

    def __init__(self):
        self.event = threading.Event()
        self.value: Any = None


class TaskBridge(TaskContext):
    """``TaskContext`` handed to plugin tasks.

    Thread-safe: the task thread reads cancel/pause state, the IPC thread
    writes it, and ``wait_if_paused`` must wake up when a cancel arrives.
    """

    def __init__(self, runtime: "PluginRuntime", task_id: str):
        self._runtime = runtime
        self.task_id = task_id
        self._lock = threading.Lock()
        self._pause_condition = threading.Condition(self._lock)
        self._cancelled = False
        self._paused = False

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def wait_if_paused(self):
        with self._pause_condition:
            while self._paused and not self._cancelled:
                # A timeout, not a bare wait: the flag may be set by a thread
                # that cannot notify (for example during interpreter shutdown).
                self._pause_condition.wait(0.1)

    def set_cancelled(self, value: bool):
        with self._pause_condition:
            self._cancelled = value
            if value:
                # Cancelling a paused task must release it.
                self._paused = False
                self._pause_condition.notify_all()

    def set_paused(self, value: bool):
        with self._pause_condition:
            if self._cancelled:
                return
            self._paused = value
            if not value:
                self._pause_condition.notify_all()

    # --- Callbacks used by AbstractTask._initialize ---

    def report_progress(self, percent: Any):
        try:
            value = int(percent)
        except (TypeError, ValueError):
            self._runtime.log(
                "warning",
                f"Task {self.task_id} reported a non-numeric progress: {percent!r}",
            )
            return
        value = max(0, min(100, value))
        self._runtime.send(MessageType.PROGRESS, task_id=self.task_id, percent=value)

    def report_event(self, name: str, payload: Mapping[str, Any] | None = None):
        self._runtime.send(
            MessageType.EVENT,
            task_id=self.task_id,
            name=str(name),
            payload=dict(payload or {}),
        )

    def request_input(self, name: str, payload: Mapping[str, Any] | None = None) -> dict:
        return self._runtime.request_input(self.task_id, name, payload)


class PluginRuntime:
    """Serves one plugin instance over one connection."""

    def __init__(
        self,
        connection,
        adapter: "PluginAdapter",
        *,
        plugin_id: str,
        plugin_version: str,
        supported_versions: Iterable[int] = SUPPORTED_VERSIONS,
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
        shutdown_grace: float = DEFAULT_SHUTDOWN_GRACE,
        input_timeout: float = DEFAULT_INPUT_TIMEOUT,
        logger: logging.Logger | None = None,
    ):
        self._connection = connection
        self._adapter = adapter
        self._plugin_id = plugin_id
        self._plugin_version = plugin_version
        self._supported_versions = tuple(supported_versions)
        self._startup_timeout = startup_timeout
        self._shutdown_grace = shutdown_grace
        self._input_timeout = input_timeout
        self._logger = logger or logging.getLogger(f"plugin-runtime-{plugin_id}")

        self._send_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._queue_condition = threading.Condition(self._state_lock)
        self._queue: collections.deque[_TaskJob | _CallJob] = collections.deque()
        self._contexts: dict[str, TaskBridge] = {}
        self._pending_inputs: dict[str, _PendingInput] = {}

        self._stop_event = threading.Event()
        self._ready = False
        self._dead = False
        self._negotiated_version: int | None = None
        self._methods: tuple[str, ...] = ()
        self._worker: threading.Thread | None = None

    # --- Public entry point -------------------------------------------------

    def serve(self) -> int:
        """Run until shutdown, a protocol error or a broken connection."""
        try:
            if not self._handshake():
                return EXIT_PROTOCOL_ERROR

            self._worker = threading.Thread(
                target=self._worker_loop,
                name=f"plugin-worker-{self._plugin_id}",
                daemon=True,
            )
            self._worker.start()
            self._ipc_loop()
            self._shutdown()
            return EXIT_OK
        except Exception as exc:  # pragma: no cover - defensive
            self.log("error", f"Runtime crashed: {exc}")
            self.send(
                MessageType.ERROR,
                task_id=None,
                code=ErrorCode.INTERNAL,
                message=str(exc),
                traceback=traceback.format_exc(),
            )
            return EXIT_INTERNAL_ERROR
        finally:
            self._stop_event.set()

    # --- Handshake ----------------------------------------------------------

    def _handshake(self) -> bool:
        try:
            if not self._connection.poll(self._startup_timeout):
                self.log(
                    "warning",
                    f"Host did not send HELLO within {self._startup_timeout}s.",
                )
                return False
            raw = self._connection.recv()
        except (EOFError, BrokenPipeError, OSError):
            return False

        try:
            message = decode(raw, supported_versions=self._supported_versions)
        except UnsupportedVersion as exc:
            self._send_error(None, ErrorCode.PROTOCOL_MISMATCH, str(exc))
            return False
        except UnknownMessageType as exc:
            self._send_error(None, ErrorCode.PROTOCOL_ERROR, str(exc))
            return False
        except InvalidMessage as exc:
            self._send_error(None, ErrorCode.PROTOCOL_ERROR, str(exc))
            return False

        if message.type is not MessageType.HELLO:
            self._send_error(
                None,
                ErrorCode.PROTOCOL_ERROR,
                f"Expected HELLO as the first message, got {message.type}",
            )
            return False

        try:
            version = negotiate_version(
                message["protocol_min"],
                message["protocol_max"],
                self._supported_versions,
            )
        except UnsupportedVersion as exc:
            self._send_error(None, ErrorCode.PROTOCOL_MISMATCH, str(exc))
            return False
        except InvalidMessage as exc:
            self._send_error(None, ErrorCode.PROTOCOL_ERROR, str(exc))
            return False

        self._negotiated_version = version
        self._methods = tuple(self._adapter.public_methods())
        self._ready = True
        self.log(
            "debug",
            f"Handshake complete: protocol v{version}, {len(self._methods)} methods.",
        )
        self.send(
            MessageType.READY,
            protocol_version=version,
            plugin_id=self._plugin_id,
            plugin_version=self._plugin_version,
            methods=list(self._methods),
        )
        return True

    # --- IPC loop -----------------------------------------------------------

    def _ipc_loop(self):
        while not self._stop_event.is_set() and not self._dead:
            try:
                if not self._connection.poll(0.05):
                    continue
                raw = self._connection.recv()
            except (EOFError, BrokenPipeError, OSError):
                self.log("warning", "Host closed the connection.")
                self._dead = True
                break

            try:
                message = decode(raw, supported_versions=self._supported_versions)
            except UnknownMessageType as exc:
                self.log("warning", f"Ignoring unknown message type {exc.message_type!r}.")
                continue
            except (InvalidMessage, UnsupportedVersion) as exc:
                self.log("error", f"Invalid message from the host: {exc}")
                self._send_error(None, ErrorCode.PROTOCOL_ERROR, str(exc))
                continue

            if direction_of(message.type) is not Direction.HOST_TO_PLUGIN:
                self.log("warning", f"Ignoring {message.type} received from the host.")
                continue

            self._dispatch(message)

    def _dispatch(self, message: Message):
        message_type = message.type

        if message_type is MessageType.EXECUTE_TASK:
            self._accept_task(message)
        elif message_type is MessageType.CANCEL_TASK:
            self._cancel_task(message["task_id"])
        elif message_type is MessageType.PAUSE_TASK:
            self._set_paused(message["task_id"], True)
        elif message_type is MessageType.RESUME_TASK:
            self._set_paused(message["task_id"], False)
        elif message_type is MessageType.CALL:
            self._accept_call(message)
        elif message_type is MessageType.INPUT_RESPONSE:
            self._resolve_input(message)
        elif message_type is MessageType.SHUTDOWN:
            self.log("debug", f"Shutdown requested: {message.get('reason') or 'no reason'}")
            self._stop_event.set()
        elif message_type is MessageType.HELLO:
            self.log("warning", "Ignoring a duplicate HELLO.")

    # --- Task intake and control -------------------------------------------

    def _accept_task(self, message: Message):
        task_id = message["task_id"]
        action_id = message["action_id"]
        kwargs = message.get("kwargs") or {}

        if not isinstance(kwargs, Mapping):
            self._send_error(
                task_id,
                ErrorCode.PROTOCOL_ERROR,
                f"EXECUTE_TASK kwargs must be a mapping, got {type(kwargs).__name__}",
            )
            return

        with self._state_lock:
            duplicate = task_id in self._contexts
            if not duplicate:
                context = TaskBridge(self, task_id)
                self._contexts[task_id] = context
                self._queue.append(_TaskJob(task_id, action_id, kwargs, context))
                self._queue_condition.notify_all()

        if duplicate:
            self._send_error(
                task_id,
                ErrorCode.PROTOCOL_ERROR,
                f"Task {task_id} is already queued or running",
            )

    def _cancel_task(self, task_id: str):
        queued = False
        with self._state_lock:
            context = self._contexts.get(task_id)
            if context is None:
                self.log("warning", f"CANCEL_TASK for unknown task {task_id}; ignoring.")
                return
            context.set_cancelled(True)
            for job in self._queue:
                if isinstance(job, _TaskJob) and job.task_id == task_id:
                    self._queue.remove(job)
                    self._contexts.pop(task_id, None)
                    queued = True
                    break

        if queued:
            # The task never ran, so its terminal message comes from here.
            self.send(MessageType.CANCELLED, task_id=task_id)

    def _set_paused(self, task_id: str, paused: bool):
        with self._state_lock:
            context = self._contexts.get(task_id)
        if context is None:
            self.log("warning", f"Pause/resume for unknown task {task_id}; ignoring.")
            return
        context.set_paused(paused)

    def _accept_call(self, message: Message):
        job = _CallJob(
            call_id=message["call_id"],
            method=message["method"],
            args=message.get("args") or [],
            kwargs=message.get("kwargs") or {},
        )
        with self._state_lock:
            self._queue.append(job)
            self._queue_condition.notify_all()

    # --- Worker loop --------------------------------------------------------

    def _worker_loop(self):
        while True:
            with self._state_lock:
                while not self._queue and not self._stopping():
                    self._queue_condition.wait(0.05)
                if self._stopping():
                    return
                job = self._queue.popleft()

            try:
                if isinstance(job, _TaskJob):
                    self._run_task(job)
                else:
                    self._run_call(job)
            except Exception:  # pragma: no cover - defensive
                self.log("error", f"Unhandled job error: {traceback.format_exc()}")

    def _run_task(self, job: _TaskJob):
        context = job.context
        if context.is_cancelled():
            self._finish_task(job.task_id, MessageType.CANCELLED)
            return

        try:
            task = self._adapter.create_task(job.action_id, job.kwargs, context)
            result = task.run()
        except Exception as exc:
            if context.is_cancelled():
                self._finish_task(job.task_id, MessageType.CANCELLED)
            else:
                self._finish_task(
                    job.task_id,
                    MessageType.ERROR,
                    code=ErrorCode.INTERNAL,
                    message=str(exc),
                    traceback=traceback.format_exc(),
                )
        else:
            if context.is_cancelled():
                self._finish_task(job.task_id, MessageType.CANCELLED)
            else:
                self._finish_task(job.task_id, MessageType.RESULT, value=result)

    def _finish_task(self, task_id: str, message_type: MessageType, **fields):
        # Unregister before sending, so a very fast re-submission of the same
        # task_id is not rejected as a duplicate terminal message.
        with self._state_lock:
            self._contexts.pop(task_id, None)
        self.send(message_type, task_id=task_id, **fields)

    def _run_call(self, job: _CallJob):
        try:
            if job.method not in self._methods:
                raise AttributeError(
                    f"{job.method!r} is not exposed by this plugin. "
                    f"Available: {sorted(self._methods)}"
                )
            result = self._adapter.invoke(job.method, job.args, job.kwargs)
        except Exception as exc:
            self.send(
                MessageType.RETURN,
                call_id=job.call_id,
                ok=False,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
        else:
            self.send(MessageType.RETURN, call_id=job.call_id, ok=True, value=result)

    # --- User input (reserved in v1) ---------------------------------------

    def request_input(
        self, task_id: str, name: str, payload: Mapping[str, Any] | None = None
    ) -> dict:
        request_id = uuid.uuid4().hex
        pending = _PendingInput()
        with self._state_lock:
            self._pending_inputs[request_id] = pending

        sent = self.send(
            MessageType.INPUT_REQUEST,
            request_id=request_id,
            task_id=task_id,
            name=str(name),
            payload=dict(payload or {}),
        )
        if not sent:
            with self._state_lock:
                self._pending_inputs.pop(request_id, None)
            return {}

        if not pending.event.wait(self._input_timeout):
            self.log(
                "warning",
                f"No answer to input request {name!r} within {self._input_timeout}s.",
            )
            with self._state_lock:
                self._pending_inputs.pop(request_id, None)
            return {}

        with self._state_lock:
            self._pending_inputs.pop(request_id, None)
        # ``None`` means "not supported / no answer" on the wire.
        return pending.value if pending.value is not None else {}

    def _resolve_input(self, message: Message):
        request_id = message["request_id"]
        with self._state_lock:
            pending = self._pending_inputs.get(request_id)
        if pending is None:
            self.log("warning", f"INPUT_RESPONSE for unknown request {request_id}.")
            return
        pending.value = message["value"]
        pending.event.set()

    # --- Shutdown -----------------------------------------------------------

    def _shutdown(self):
        with self._state_lock:
            queued = list(self._queue)
            self._queue.clear()
            contexts = list(self._contexts.values())
            self._contexts.clear()
            self._queue_condition.notify_all()

        # Queued tasks never ran: their terminal message is CANCELLED.
        for job in queued:
            if isinstance(job, _TaskJob):
                self.send(MessageType.CANCELLED, task_id=job.task_id)

        # Running tasks are cooperative; cancel wakes a paused one. Their own
        # thread sends the terminal message.
        for context in contexts:
            context.set_cancelled(True)

        if self._worker is not None:
            self._worker.join(self._shutdown_grace)
            if self._worker.is_alive():
                self.log("warning", "Worker did not stop within the shutdown grace period.")

        if not self._dead:
            self.send(MessageType.BYE, reason="runtime stopped")

    # --- Helpers ------------------------------------------------------------

    def _stopping(self) -> bool:
        return self._stop_event.is_set() or self._dead

    def _wire_version(self) -> int:
        return self._negotiated_version or PROTOCOL_VERSION

    def send(self, message_type: MessageType, **fields) -> bool:
        """Send one message; returns ``False`` once the channel is dead."""
        with self._send_lock:
            if self._dead:
                return False
            try:
                self._connection.send(
                    encode(message_type, version=self._wire_version(), **fields)
                )
                return True
            except (BrokenPipeError, EOFError, OSError):
                self._dead = True
                return False

    def _send_error(
        self,
        task_id: str | None,
        code: ErrorCode,
        message: str,
        traceback_text: str | None = None,
    ):
        self.send(
            MessageType.ERROR,
            task_id=task_id,
            code=code,
            message=message,
            traceback=traceback_text,
        )

    def log(self, level: str, message: str):
        logger_method = getattr(self._logger, level, self._logger.info)
        logger_method(message)
        if self._ready and level in ("warning", "error") and not self._dead:
            self.send(MessageType.LOG, level=level, message=message)


class PluginAdapter:
    """What the runtime needs from a plugin, independent of its style."""

    def public_methods(self) -> Iterable[str]:
        raise NotImplementedError

    def create_task(
        self, action_id: str, kwargs: Mapping[str, Any], context: TaskContext
    ) -> AbstractTask:
        raise NotImplementedError

    def invoke(self, method: str, args: list, kwargs: Mapping[str, Any]) -> Any:
        raise NotImplementedError


class LegacyPluginAdapter(PluginAdapter):
    """Adapter for plugins written against ``PluginBase`` / ``AbstractTask``."""

    def __init__(self, plugin: PluginBase):
        if not isinstance(plugin, PluginBase):
            raise TypeError(
                f"{type(plugin).__name__} is not a PluginBase; the legacy adapter "
                "only supports the current plugin contract"
            )
        self._plugin = plugin
        self._public_methods = tuple(
            sorted(
                name
                for name in dir(type(plugin))
                if not name.startswith("_")
                and callable(getattr(type(plugin), name, None))
            )
        )

    def public_methods(self) -> Iterable[str]:
        return self._public_methods

    def create_task(
        self, action_id: str, kwargs: Mapping[str, Any], context: TaskContext
    ) -> AbstractTask:
        task = self._plugin.create_task(action_id, **kwargs)
        if not isinstance(task, AbstractTask):
            raise TypeError(
                f"{type(self._plugin).__name__}.create_task({action_id!r}) returned "
                f"{type(task).__name__}, expected an AbstractTask"
            )
        task._initialize(
            context,
            context.report_progress,
            context.report_event,
            context.request_input,
        )
        return task

    def invoke(self, method: str, args: list, kwargs: Mapping[str, Any]) -> Any:
        return getattr(self._plugin, method)(*args, **kwargs)
