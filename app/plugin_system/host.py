# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The host side of the runtime protocol: one QObject per sandboxed plugin.

The class keeps the surface that the rest of the application already uses
(``start``/``stop``/``is_ready``, ``execute_task``, the four control methods,
attribute-style synchronous calls and the five Qt signals), so
``PluginManager``, ``BackgroundTaskManager``, ``TaskQueueManager`` and the UI
need no changes. Underneath it speaks ``runtime-protocol.md`` instead of the
old ad-hoc dictionaries.

Attribute access still works, but only for methods advertised in ``READY`` and
through an explicit ``CALL``/``RETURN`` pair. An unknown name raises
``AttributeError`` immediately; it never blocks the caller.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import multiprocessing
import os
import sys
import threading
import time
import traceback
import uuid
from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from app.plugin_system.api import PluginBase
from app.plugin_system.protocol import (
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
)
from app.plugin_system.runtime import (
    EXIT_INTERNAL_ERROR,
    LegacyPluginAdapter,
    PluginRuntime,
)

#: How long the plugin process may take to load and answer HELLO.
STARTUP_TIMEOUT = 5.0

#: Synchronous calls happen at load time (menu actions) on a cold process.
#: The protocol default is 5 s; the host keeps the historical 10 s.
CALL_TIMEOUT = 10.0

#: Time the plugin gets to exit after SHUTDOWN before it is terminated.
SHUTDOWN_GRACE = 2.0

_SERIALIZABLE_TYPES = (str, int, float, bool, list, dict, tuple, type(None))


class _PendingCall:
    __slots__ = ("event", "value", "error")

    def __init__(self):
        self.event = threading.Event()
        self.value: Any = None
        self.error: str | None = None

    def resolve(self, value: Any):
        self.value = value
        self.event.set()

    def fail(self, error: str):
        self.error = error
        self.event.set()


class SandboxedPluginWrapper(QObject):
    """Host-side handle for a plugin running in its own process."""

    progress_updated = pyqtSignal(str, int)
    method_finished = pyqtSignal(str, object)
    method_failed = pyqtSignal(str, str, str)
    critical_error = pyqtSignal(str)
    data_event_received = pyqtSignal(str, str, dict)

    STARTUP_TIMEOUT = STARTUP_TIMEOUT
    CALL_TIMEOUT = CALL_TIMEOUT

    def __init__(self, plugin_path: str, metadata: Mapping[str, Any]):
        super().__init__()
        self.plugin_path = plugin_path
        self.metadata = dict(metadata)
        self.logger = logging.getLogger(
            f"SandboxedPluginWrapper-{metadata.get('id', 'unknown')}"
        )

        self.process: multiprocessing.Process | None = None
        self.parent_pipe = None
        self.child_pipe = None

        self.active_tasks: set[str] = set()
        self._plugin_methods: set[str] = set()
        self._ready_event = threading.Event()
        self._stop_event = threading.Event()

        self._send_lock = threading.Lock()
        self._calls_lock = threading.Lock()
        self._pending_calls: dict[str, _PendingCall] = {}
        self._listener: threading.Thread | None = None
        self._dead = False

        self._make_pipe()

    # --- Lifecycle ----------------------------------------------------------

    def start(self):
        if self.process is not None and self.process.is_alive():
            return

        self._ready_event.clear()
        self._stop_event.clear()
        self._dead = False
        self._plugin_methods = set()
        self._make_pipe()

        self.process = multiprocessing.Process(
            target=run_plugin_process,
            args=(self.child_pipe, self.plugin_path, self.metadata),
        )
        self.process.daemon = True
        self.process.start()
        self.logger.info("Sandbox process started.")

        # The child owns its end now; keeping a copy here would prevent EOF
        # detection when the child dies.
        try:
            self.child_pipe.close()
        except OSError:
            pass

        self._listener = threading.Thread(
            target=self._listen_to_pipe,
            name=f"plugin-ipc-{self.metadata.get('id', 'unknown')}",
            daemon=True,
        )
        self._listener.start()

        self._send(MessageType.HELLO, **self._hello_fields())
        self._wait_until_ready()

    def _hello_fields(self) -> dict:
        versions = tuple(self._supported_versions())
        return {
            "protocol_min": min(versions),
            "protocol_max": max(versions),
            "plugin_id": self.metadata.get("id", ""),
        }

    def _supported_versions(self):
        return SUPPORTED_VERSIONS

    def _wait_until_ready(self):
        deadline = time.monotonic() + self.STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            if self._ready_event.wait(0.05):
                break
            if self.process is not None and not self.process.is_alive():
                break

        if self._ready_event.is_set():
            self.logger.debug(
                "Plugin %s API: %s",
                self.metadata.get("id"),
                sorted(self._plugin_methods),
            )
        elif self.process is not None and not self.process.is_alive():
            self.logger.error(
                "Plugin %s failed to start: the process exited during initialization.",
                self.metadata.get("id"),
            )
        else:
            self.logger.warning(
                "Plugin %s did not answer HELLO within %ss. "
                "Attribute-style calls will raise AttributeError; use execute_task().",
                self.metadata.get("id"),
                self.STARTUP_TIMEOUT,
            )

    def is_ready(self) -> bool:
        """True when the process is alive and has completed the handshake."""
        return (
            self._ready_event.is_set()
            and not self._dead
            and self.process is not None
            and self.process.is_alive()
        )

    def stop(self):
        process = self.process
        if process is not None and process.is_alive():
            self.logger.info("Stopping sandbox process...")
            self._send(MessageType.SHUTDOWN, reason="host shutdown")
            self._stop_event.set()

            process.join(SHUTDOWN_GRACE)
            if process.is_alive():
                self.logger.warning(
                    "Sandbox process did not exit gracefully. Terminating."
                )
                process.terminate()
                process.join(1.0)
            else:
                self.logger.info("Sandbox process stopped.")
        else:
            self._stop_event.set()

        self._abort_pending_calls("Plugin process stopped")

        if self._listener is not None:
            self._listener.join(1.0)
        self._close_pipes()

    def _make_pipe(self):
        self._close_pipes()
        self.parent_pipe, self.child_pipe = multiprocessing.Pipe()

    def _close_pipes(self):
        for name in ("parent_pipe", "child_pipe"):
            pipe = self.__dict__.get(name)
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass
            self.__dict__[name] = None

    # --- Task API -----------------------------------------------------------

    def execute_task(self, task_id, action_id, **kwargs):
        self.active_tasks.add(task_id)
        sent = self._send(
            MessageType.EXECUTE_TASK,
            task_id=task_id,
            action_id=action_id,
            kwargs=kwargs,
        )
        if not sent:
            self.logger.error(
                "Plugin %s is not available; task %s cannot start.",
                self.metadata.get("id"),
                task_id,
            )
            self.active_tasks.discard(task_id)
            self.method_failed.emit(task_id, "Plugin is not available", "")

    def cancel_task(self, task_id):
        self._send(MessageType.CANCEL_TASK, task_id=task_id)

    def pause_task(self, task_id):
        self._send(MessageType.PAUSE_TASK, task_id=task_id)

    def resume_task(self, task_id):
        self._send(MessageType.RESUME_TASK, task_id=task_id)

    # --- Synchronous attribute calls ---------------------------------------

    def __getattr__(self, name):
        # Never intercept private or dunder attributes: libraries (copy, pickle,
        # inspect) probe them and a callable returned here breaks them.
        if name.startswith("_"):
            raise AttributeError(name)

        known_methods = self.__dict__.get("_plugin_methods", set())
        if name not in known_methods:
            raise AttributeError(
                f"{type(self).__name__} has no attribute {name!r}. "
                f"Methods exposed by the plugin: {sorted(known_methods)}"
            )

        def sync_method_wrapper(*args, **kwargs):
            return self._call_method(name, args, kwargs)

        return sync_method_wrapper

    def _call_method(self, name: str, args: tuple, kwargs: Mapping[str, Any]):
        call_id = uuid.uuid4().hex
        pending = _PendingCall()
        with self._calls_lock:
            self._pending_calls[call_id] = pending

        try:
            sent = self._send(
                MessageType.CALL,
                call_id=call_id,
                method=name,
                args=self._serializable(args, name),
                kwargs=self._serializable(kwargs, name),
            )
            if not sent:
                raise RuntimeError(f"Plugin {self.metadata.get('id')} is not available")

            if not pending.event.wait(self.CALL_TIMEOUT):
                raise TimeoutError(
                    f"Timeout waiting for sync method '{name}' after "
                    f"{self.CALL_TIMEOUT}s"
                )
            if pending.error is not None:
                raise RuntimeError(f"Plugin error: {pending.error}")
            return pending.value
        finally:
            with self._calls_lock:
                self._pending_calls.pop(call_id, None)

    def _serializable(self, values, method_name):
        if isinstance(values, Mapping):
            items = values.items()
        else:
            items = enumerate(values)

        cleaned = {} if isinstance(values, Mapping) else []
        for key, value in items:
            if isinstance(value, _SERIALIZABLE_TYPES):
                if isinstance(cleaned, dict):
                    cleaned[key] = value
                else:
                    cleaned.append(value)
            else:
                self.logger.warning(
                    "Dropping a non-serializable argument %r passed to %s().",
                    key,
                    method_name,
                )
        return cleaned

    # --- IPC listener -------------------------------------------------------

    def _listen_to_pipe(self):
        # A dying thread must never take the process with it: at interpreter
        # shutdown this runs alongside a half-closed logging module.
        try:
            self._listen_loop()
        except (EOFError, BrokenPipeError, OSError):
            self._on_channel_lost()
        except Exception:  # noqa: BLE001 - see above
            self._safe_log(
                "exception",
                "Plugin %s listener crashed.",
                self.metadata.get("id"),
            )

    def _listen_loop(self):
        while not self._stop_event.is_set():
            try:
                pipe = self.__dict__.get("parent_pipe")
                if pipe is None:
                    break
                if not pipe.poll(0.05):
                    if self._dead:
                        break
                    continue
                raw = pipe.recv()
            except (EOFError, BrokenPipeError, OSError):
                self._on_channel_lost()
                return

            try:
                message = decode(raw)
            except UnknownMessageType as exc:
                self._safe_log(
                    "warning",
                    "Ignoring unknown message type %r from plugin %s.",
                    exc.message_type,
                    self.metadata.get("id"),
                )
                continue
            except UnsupportedVersion as exc:
                self._safe_log("error", "Plugin %s: %s", self.metadata.get("id"), exc)
                self._emit(self.critical_error, f"Protocol error: {exc}")
                continue
            except InvalidMessage as exc:
                self._safe_log(
                    "error",
                    "Invalid message from plugin %s: %s",
                    self.metadata.get("id"),
                    exc,
                )
                continue

            if direction_of(message.type) is not Direction.PLUGIN_TO_HOST:
                self._safe_log("warning", "Ignoring %s sent by the plugin.", message.type)
                continue

            self._handle(message)

        # A stop request closes the loop even if the pipe is still open.
        if self._dead:
            self._on_channel_lost()

    # --- Output from the IPC thread ----------------------------------------

    def _safe_log(self, level: str, message: str, *args):
        """Log without depending on the logging module being usable.

        During interpreter shutdown the streams are closed; a write from a
        daemon thread aborts the process with
        ``Fatal Python error: _enter_buffered_busy``. Losing a log line is
        better than losing the exit code.
        """
        if sys.is_finalizing():
            return

        log = getattr(self.logger, level, self.logger.info)
        try:
            log(message, *args)
        except (ValueError, OSError):
            pass

    def _emit(self, signal, *args):
        """Emit a Qt signal from the IPC thread, tolerating a deleted wrapper.

        The thread outlives the Python object when a wrapper is garbage
        collected without ``stop()``; emitting then raises ``RuntimeError``
        and, before Python 3.13, used to abort at shutdown.
        """
        if sys.is_finalizing():
            return

        try:
            signal.emit(*args)
        except RuntimeError:
            self._safe_log(
                "debug",
                "Dropped a signal for plugin %s: the wrapper is gone.",
                self.metadata.get("id"),
            )

    def _handle(self, message: Message):
        message_type = message.type

        if message_type is MessageType.READY:
            self._plugin_methods = set(message["methods"])
            self._safe_log(
                "debug",
                "Plugin %s ready (protocol v%s).",
                self.metadata.get("id"),
                message["protocol_version"],
            )
            self._ready_event.set()

        elif message_type is MessageType.PROGRESS:
            self._emit(self.progress_updated, message["task_id"], message["percent"])

        elif message_type is MessageType.EVENT:
            self._emit(
                self.data_event_received,
                message["task_id"],
                message["name"],
                message.get("payload") or {},
            )

        elif message_type is MessageType.RESULT:
            task_id = message["task_id"]
            self.active_tasks.discard(task_id)
            self._emit(self.method_finished, task_id, message.get("value"))

        elif message_type is MessageType.CANCELLED:
            task_id = message["task_id"]
            self.active_tasks.discard(task_id)
            # The queue decides whether this is a user cancellation or a real
            # failure; it already treats a cancelled context as CANCELLED.
            self._emit(self.method_failed, task_id, "Task cancelled", "")

        elif message_type is MessageType.ERROR:
            self._handle_error(message)

        elif message_type is MessageType.RETURN:
            self._handle_return(message)

        elif message_type is MessageType.INPUT_REQUEST:
            # v1 host does not ask the user; None means "no answer".
            self._send(
                MessageType.INPUT_RESPONSE,
                request_id=message["request_id"],
                value=None,
            )

        elif message_type is MessageType.LOG:
            level = message["level"]
            if level not in ("debug", "info", "warning", "error", "critical"):
                level = "info"
            self._safe_log(level, "[Plugin] %s", message["message"])

        elif message_type is MessageType.BYE:
            self._safe_log(
                "debug", "Plugin %s said goodbye.", self.metadata.get("id")
            )

    def _handle_error(self, message: Message):
        task_id = message.get("task_id")
        error = message.get("message") or "Unknown plugin error"
        traceback_text = message.get("traceback") or ""

        if task_id is None:
            self._safe_log(
                "error",
                "Plugin %s failed [%s]: %s\n%s",
                self.metadata.get("id"),
                message["code"],
                error,
                traceback_text,
            )
            self._emit(
                self.critical_error, f"Plugin process error: {error}\n{traceback_text}"
            )
            self._fail_all_active(f"Plugin process failed: {error}")
            return

        if task_id not in self.active_tasks:
            self._safe_log(
                "warning",
                "Received an error for unknown task %s from plugin %s.",
                task_id,
                self.metadata.get("id"),
            )
            return

        self.active_tasks.discard(task_id)
        self._emit(self.method_failed, task_id, error, traceback_text)

    def _handle_return(self, message: Message):
        call_id = message["call_id"]
        with self._calls_lock:
            pending = self._pending_calls.get(call_id)

        if pending is None:
            self._safe_log("warning", "RETURN for unknown call %s.", call_id)
            return

        if message["ok"]:
            pending.resolve(message.get("value"))
        else:
            pending.fail(message.get("error") or "Unknown plugin error")

    def _on_channel_lost(self):
        self._dead = True
        if self._stop_event.is_set():
            return
        self._safe_log("warning", "Pipe closed unexpectedly.")
        self._emit(self.critical_error, "Plugin process pipe closed unexpectedly.")
        self._fail_all_active("Plugin process crashed")

    def _fail_all_active(self, reason: str):
        for task_id in list(self.active_tasks):
            self._emit(self.method_failed, task_id, reason, "")
        self.active_tasks.clear()

    def _abort_pending_calls(self, reason: str):
        with self._calls_lock:
            pending = list(self._pending_calls.values())
        for call in pending:
            call.fail(reason)

    # --- Transport ----------------------------------------------------------

    def _send(self, message_type: MessageType, **fields) -> bool:
        pipe = self.__dict__.get("parent_pipe")
        if pipe is None or self._dead:
            return False
        with self._send_lock:
            if self._dead:
                return False
            try:
                pipe.send(
                    encode(message_type, version=self._wire_version(), **fields)
                )
                return True
            except (BrokenPipeError, EOFError, OSError):
                self._dead = True
                return False

    def _wire_version(self) -> int:
        return PROTOCOL_VERSION


def _prepare_plugin_import_path(plugin_path: str):
    importlib.invalidate_caches()

    project_root = os.path.abspath(os.path.join(plugin_path, "..", "..", ".."))
    sys.path.insert(0, project_root)

    libs_dir = os.path.join(plugin_path, "libs")
    if os.path.exists(libs_dir):
        sys.path.insert(0, libs_dir)
    sys.path.insert(0, plugin_path)


def _load_plugin_instance(plugin_path: str, metadata: Mapping[str, Any]):
    entry_point = metadata["entry_point"]
    module_name, class_name = entry_point.split(":")
    module_file_path = os.path.join(plugin_path, module_name.replace(".", os.sep) + ".py")

    spec = importlib.util.spec_from_file_location("plugin_main", module_file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plugin_class = getattr(module, class_name)
    return plugin_class()


def run_plugin_process(pipe, plugin_path: str, metadata: Mapping[str, Any]):
    """Entry point of the child process."""
    logger = logging.getLogger(f"SandboxedPluginWrapper-{metadata.get('id', 'unknown')}")
    exit_code = EXIT_INTERNAL_ERROR

    try:
        _prepare_plugin_import_path(plugin_path)
        plugin_instance = _load_plugin_instance(plugin_path, metadata)

        if not isinstance(plugin_instance, PluginBase):
            raise TypeError(
                f"Plugin {metadata.get('id')} does not inherit from PluginBase"
            )

        runtime = PluginRuntime(
            pipe,
            LegacyPluginAdapter(plugin_instance),
            plugin_id=metadata["id"],
            plugin_version=metadata.get("version", "0.0.0"),
            logger=logger,
        )
        exit_code = runtime.serve()
    except Exception as exc:
        logger.error(
            "Plugin %s failed to start: %s", metadata.get("id"), exc, exc_info=True
        )
        try:
            pipe.send(
                encode(
                    MessageType.ERROR,
                    task_id=None,
                    code=ErrorCode.INTERNAL,
                    message=f"Plugin failed to start: {exc}",
                    traceback=traceback.format_exc(),
                )
            )
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        try:
            pipe.close()
        except OSError:
            pass

    raise SystemExit(exit_code)
