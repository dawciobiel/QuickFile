# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
import json
import os
from app.plugin_manager import PluginManager
from plugins.base import ViewerPlugin
from app.plugin_sandbox import SandboxedPluginWrapper # Import SandboxedPluginWrapper

# Fixture to create a fake plugin structure
@pytest.fixture
def mock_plugin_dir(tmp_path):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    # Plugin 1: Two versions, the newer one should be loaded
    viewer_plugin_path = plugin_dir / "org.example" / "viewer"
    viewer_v1_path = viewer_plugin_path / "1.0.0"
    viewer_v1_path.mkdir(parents=True)
    (viewer_v1_path / "metadata.json").write_text(json.dumps({
        "id": "org.example.viewer", "version": "1.0.0", "type": "viewer",
        "entry_point": "plugin:MyViewerV1"
    }))
    (viewer_v1_path / "plugin.py").write_text("""
from plugins.base import ViewerPlugin
class MyViewerV1(ViewerPlugin):
    def get_name(self): return "MyViewerV1"
    def get_description(self): return "A mock viewer plugin v1"
    def can_view(self, path): return path.endswith('.txt')
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
""")

    viewer_v2_path = viewer_plugin_path / "1.1.0"
    viewer_v2_path.mkdir()
    (viewer_v2_path / "metadata.json").write_text(json.dumps({
        "id": "org.example.viewer", "version": "1.1.0", "type": "viewer",
        "entry_point": "plugin:MyViewerV2",
        "sandboxed": True # Oznaczamy jako sandboxed
    }))
    (viewer_v2_path / "plugin.py").write_text("""
from plugins.base import ViewerPlugin
class MyViewerV2(ViewerPlugin):
    def get_name(self): return "MyViewerV2"
    def get_description(self): return "A mock viewer plugin v2"
    def can_view(self, path): return path.endswith('.v2')
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
""")

    # Plugin 2: Broken metadata.json
    broken_plugin_path = plugin_dir / "org.example" / "broken" / "1.0.0"
    broken_plugin_path.mkdir(parents=True)
    (broken_plugin_path / "metadata.json").write_text("{ not valid json }")
    (broken_plugin_path / "plugin.py").write_text("class Broken: pass")

    return plugin_dir

# Fixture to create a PluginManager with a mocked directory
@pytest.fixture
def plugin_manager(mocker, mock_plugin_dir):
    # Mock the methods that interact with the real filesystem/config
    mocker.patch.object(PluginManager, '_ensure_bundled_plugins', return_value=None)
    
    # Instantiate the manager, but tell it to use our mock directory
    pm = PluginManager(plugin_dirs=[str(mock_plugin_dir)])
    
    yield pm # Używamy yield, aby zapewnić, że shutdown zostanie wywołany
    pm.shutdown() # Zamykamy procesy piaskownicy po teście

def test_load_latest_plugin_version(plugin_manager):
    """Test that only the latest version of a plugin is loaded and it's sandboxed."""
    assert len(plugin_manager.plugins["viewer"]) == 1
    
    loaded_plugin = plugin_manager.plugins["viewer"][0]
    
    # Sprawdzamy, czy załadowany plugin jest wrapperem piaskownicy
    assert isinstance(loaded_plugin, SandboxedPluginWrapper)
    
    # Sprawdzamy, czy nazwa pluginu jest poprawnie delegowana
    assert loaded_plugin.get_name() == "MyViewerV2"

def test_get_viewer_for_file(plugin_manager):
    """Test that get_viewer_for_file returns the correct sandboxed plugin."""
    viewer = plugin_manager.get_viewer_for_file("test.v2")
    
    assert isinstance(viewer, SandboxedPluginWrapper)
    assert viewer.get_name() == "MyViewerV2"
    assert viewer.can_view("test.v2") is True # can_view powinno być delegowane
    assert viewer.can_view("test.txt") is False # can_view powinno być delegowane
    
    # Version 1.0.0 should not be loaded, so it won't find a viewer for .txt
    assert plugin_manager.get_viewer_for_file("test.txt") is None

def test_loading_broken_plugin_is_handled(plugin_manager):
    """Test that a broken plugin doesn't crash the manager and other plugins are loaded."""
    # This test implicitly checks that the manager initialized without crashing.
    # The assertion from test_load_latest_plugin_version further confirms that
    # the valid plugin was loaded despite the broken one.
    assert len(plugin_manager.plugins["viewer"]) == 1
