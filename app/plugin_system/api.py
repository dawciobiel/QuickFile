# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable


class Capability:
    """Closed vocabulary of plugin capabilities.

    ``type`` decides which slot a plugin occupies in ``PluginManager.plugins``;
    a capability says what the plugin can do inside that slot. Archive plugins
    are the first user: ``type: archive`` alone cannot tell a creator from an
    extractor, so ``archive.create`` and ``archive.extract`` are declared in
    ``metadata.json`` and used to filter the UI and route tasks.

    Values are plain strings so they survive JSON and the plugin process
    boundary unchanged. Keep the vocabulary closed: add constants here instead
    of inventing strings in metadata.
    """

    #: Plugin can build an archive from files. Handles ``create_archive``.
    ARCHIVE_CREATE = "archive.create"
    #: Plugin can unpack an archive. Handles ``extract_archive``.
    ARCHIVE_EXTRACT = "archive.extract"

    ALL = frozenset({ARCHIVE_CREATE, ARCHIVE_EXTRACT})


class TaskCancelled(Exception):
    """Raised by ``TaskContext.check_cancelled()`` when the user cancels.

    The runtime turns it into a ``CANCELLED`` message, not an ``ERROR``; a task
    that raises it is doing exactly what the host asked for.
    """


class TaskContext:
    """
    What a task may do with the task it is running.

    The runtime supplies the implementation; plugins only read it. Legacy tasks
    receive the same object through ``AbstractTask._initialize``, so every
    method here works for both styles.
    """

    #: Identifier assigned by the host; stable for the lifetime of the task.
    task_id: str

    def is_cancelled(self) -> bool:
        """Checks if the task has been cancelled."""
        raise NotImplementedError

    def is_paused(self) -> bool:
        """Checks if the task is currently paused."""
        raise NotImplementedError

    def wait_if_paused(self):
        """Blocks execution if the task is paused until it is resumed."""
        raise NotImplementedError

    def check_cancelled(self):
        """Raises ``TaskCancelled`` if the task has been cancelled.

        Preferred over ``is_cancelled()`` in the explicit API: it cannot be
        forgotten as a bare ``if`` without a ``raise``.
        """
        if self.is_cancelled():
            raise TaskCancelled("Task was cancelled")

    def progress(self, percentage: int):
        """Reports progress (0-100) to the main application."""
        raise NotImplementedError

    def event(self, name: str, payload: Optional[Dict[str, Any]] = None):
        """Sends a domain event to the main application."""
        raise NotImplementedError

    def request_input(
        self, name: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Asks the main application for input and waits for the answer."""
        raise NotImplementedError

    def log(self, level: str, message: str):
        """Logs in the plugin process; warnings and errors reach the host too."""
        raise NotImplementedError


class AbstractTask(ABC):
    """
    Base class for all long-running tasks executed by plugins.
    This class runs in a separate Worker Thread within the plugin process.
    """
    def __init__(self):
        self._context: Optional[TaskContext] = None
        self._progress_callback: Optional[Callable[[int], None]] = None
        self._event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self._input_request_callback: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None

    def _initialize(self, context: TaskContext, 
                    progress_callback: Callable[[int], None],
                    event_callback: Callable[[str, Dict[str, Any]], None],
                    input_request_callback: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        """Internal initialization method called by the worker."""
        self._context = context
        self._progress_callback = progress_callback
        self._event_callback = event_callback
        self._input_request_callback = input_request_callback

    @abstractmethod
    def run(self):
        """
        The main logic of the task.
        This method must be implemented by the plugin developer.
        It should periodically check self._context.is_cancelled().
        """
        pass

    def emit_progress(self, percentage: int):
        """Reports progress (0-100) to the main application."""
        if self._progress_callback:
            self._progress_callback(percentage)

    def emit_event(self, event_name: str, payload: Dict[str, Any] = None):
        """
        Sends a custom data event to the main application.
        Example: emit_event("item_found", {"path": "/tmp/file.txt"})
        """
        if self._event_callback:
            self._event_callback(event_name, payload or {})

    def request_user_input(self, event_name: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Sends a request for user input and WAITS for the response.
        Example: response = request_user_input("password_required", {"archive": "secret.zip"})
        """
        if self._input_request_callback:
            return self._input_request_callback(event_name, payload or {})
        return {}

    @property
    def context(self) -> TaskContext:
        """Access to the task context (cancellation/pause status)."""
        return self._context


class PluginBase(ABC):
    """
    Base class for all QuickFile plugins.
    Defines metadata and factory methods for tasks.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Display name of the plugin."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Short description of the plugin."""
        pass

    def get_menu_actions(self) -> list[dict]:
        """
        Returns a list of menu actions provided by this plugin.
        Each action should define 'action_id' which maps to a factory method.
        """
        return []

    def create_task(self, action_id: str, **kwargs) -> AbstractTask:
        """
        Factory method to create a task instance based on action_id.
        Must be implemented if the plugin provides background tasks.
        """
        raise NotImplementedError(f"Plugin {self.get_name()} does not support task creation for {action_id}")

    def handle_event(self, event_name: str, payload: Dict[str, Any], task_id: str):
        """
        Optional handler for custom events emitted by tasks.
        This runs in the MAIN application process (UI thread).
        """
        pass


class PluginTask(ABC):
    """
    One unit of background work in the explicit task API.

    ``run`` receives its context as an argument: there is no ``self.context``,
    no ``_initialize`` and no hidden state set by the runtime. The return value
    becomes the task result and must be serializable (str, int, float, bool,
    list, dict, tuple, None). Raise ``TaskCancelled`` to report a cancellation.

    Not to be confused with ``app.task_queue_manager.Task``, which is the
    queue entry on the UI side.
    """

    @abstractmethod
    def run(self, context: TaskContext):
        """Do the work and return a serializable result."""
        pass


class TaskPlugin(PluginBase):
    """
    Plugin whose tasks use the explicit task API (``PluginTask``).

    The marker is what ``adapter_for`` looks at: a subclass gets
    ``TaskPluginAdapter``, every other ``PluginBase`` keeps the legacy adapter.
    Do not mix both styles in one class -- create two plugins instead.
    """

    def create_task(self, action_id: str, **kwargs) -> PluginTask:
        """
        Factory method returning a ``PluginTask`` for ``action_id``.

        Arguments come from ``EXECUTE_TASK.kwargs`` and are passed through
        unchanged, so the factory is the only place that validates them.
        """
        raise NotImplementedError(
            f"Plugin {self.get_name()} does not support task creation for {action_id}"
        )
