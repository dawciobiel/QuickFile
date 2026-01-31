# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable

class TaskContext:
    """
    Interface for the task context provided to the plugin task.
    Allows checking for cancellation and pausing.
    """
    def is_cancelled(self) -> bool:
        """Checks if the task has been cancelled."""
        raise NotImplementedError

    def is_paused(self) -> bool:
        """Checks if the task is currently paused."""
        raise NotImplementedError

    def wait_if_paused(self):
        """Blocks execution if the task is paused until it is resumed."""
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
