# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Smoke tests for the plugins that ship with QuickFile in sandbox mode.

``test_plugin_host.py`` proves the transport against a throwaway plugin. This
module proves the other half: every bundled plugin that declares
``"sandboxed": true`` really loads from its own directory, finishes the
handshake and can answer the two calls the UI makes while building menus.

That catches packaging and import regressions (missing ``libs/``, broken
``entry_point``, a plugin that imports an optional dependency at module level)
which the dummy plugin cannot see.
"""

import os
import platform

import pytest

from app.plugin_system.host import SandboxedPluginWrapper
from tests.plugin_helpers import iter_plugin_metadata


def _discover_sandboxed_plugins():
    plugins = []
    for metadata_path, metadata in iter_plugin_metadata():
        if metadata.get("sandboxed", False):
            plugins.append((os.path.dirname(metadata_path), metadata))
    return plugins


def _platform_supported(metadata):
    supported = [name.lower() for name in metadata.get("platforms", [])]
    if not supported:
        return True

    current = platform.system().lower()
    if current == "darwin":
        current = "macos"
    return current in supported


SANDBOXED_PLUGINS = _discover_sandboxed_plugins()
PLUGIN_IDS = [metadata["id"] for _path, metadata in SANDBOXED_PLUGINS]


def test_the_suite_covers_the_shipped_sandboxed_plugins():
    """Guard against a silent no-op if discovery ever stops matching."""
    assert len(SANDBOXED_PLUGINS) >= 8
    assert len(set(PLUGIN_IDS)) == len(PLUGIN_IDS)


@pytest.mark.parametrize(
    "plugin_dir, metadata", SANDBOXED_PLUGINS, ids=PLUGIN_IDS
)
def test_bundled_plugin_starts_and_answers_queries(plugin_dir, metadata, qapp):
    if not _platform_supported(metadata):
        pytest.skip(f"{metadata['id']} does not support {platform.system()}")

    wrapper = SandboxedPluginWrapper(plugin_dir, metadata)
    wrapper.start()
    try:
        assert wrapper.is_ready(), (
            f"{metadata['id']} did not finish the handshake; "
            f"check that {plugin_dir} still imports cleanly"
        )

        # The whole plugin API surface the UI relies on at load time.
        name = wrapper.get_name()
        assert isinstance(name, str) and name.strip(), metadata["id"]

        actions = wrapper.get_menu_actions()
        assert isinstance(actions, list), metadata["id"]
        for action in actions:
            assert isinstance(action, dict), metadata["id"]
            assert "action_id" in action, metadata["id"]
    finally:
        wrapper.stop()

    assert not wrapper.is_ready()
