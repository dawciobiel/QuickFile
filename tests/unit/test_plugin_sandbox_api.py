# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract tests for the sandboxed plugin wrapper's attribute access.

The wrapper used to answer *every* attribute lookup with an RPC callable that
waited up to 10 seconds for a reply. Typo in an attribute name or a library
probing ``__deepcopy__`` was enough to freeze the caller for 10s.
"""

import time

import pytest

from app.plugin_sandbox import SandboxedPluginWrapper


@pytest.fixture
def wrapper():
    instance = SandboxedPluginWrapper(
        "/nonexistent/plugin", {"id": "org.quickfile.test", "version": "0.0.0"}
    )
    yield instance
    for pipe in (instance.parent_pipe, instance.child_pipe):
        try:
            pipe.close()
        except OSError:
            pass


def test_unknown_attribute_raises_attribute_error(wrapper):
    with pytest.raises(AttributeError):
        wrapper.does_not_exist


def test_unknown_attribute_fails_fast(wrapper):
    started = time.monotonic()
    with pytest.raises(AttributeError):
        wrapper.does_not_exist
    assert time.monotonic() - started < 0.5, "attribute lookup must not block on RPC"


def test_private_attributes_are_never_intercepted(wrapper):
    # Libraries probe these; returning a callable breaks copy/pickle/inspect.
    assert not hasattr(wrapper, "_some_private_marker")
    assert not hasattr(wrapper, "__deepcopy__")


def test_only_advertised_methods_are_callable(wrapper):
    with pytest.raises(AttributeError):
        wrapper.get_name

    wrapper._plugin_methods = {"get_name"}

    assert callable(wrapper.get_name)


def test_attribute_error_mentions_available_methods(wrapper):
    wrapper._plugin_methods = {"get_name", "create_task"}

    with pytest.raises(AttributeError) as excinfo:
        wrapper.typo_here

    message = str(excinfo.value)
    assert "create_task" in message
    assert "get_name" in message
