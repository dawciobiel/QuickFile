# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
import json
from app.plugin_manager import PluginManager
from app.plugin_system.api import Capability
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


def test_plugin_refresh_drops_libs_of_versions_that_are_no_longer_bundled(tmp_path):
    source = tmp_path / "source"
    (source / "1.2.0").mkdir(parents=True)
    (source / "1.2.0" / "plugin.py").write_text("", encoding="utf-8")

    target = tmp_path / "target"
    (target / "1.1.0" / "libs" / "old").mkdir(parents=True)
    (target / "1.2.0" / "libs" / "keep").mkdir(parents=True)

    PluginManager._copy_preserving_libs(str(source), str(target))

    assert (target / "1.2.0" / "libs" / "keep").is_dir()
    assert not (target / "1.1.0").exists()


def test_non_sandboxed_plugin_that_needs_libs_is_rejected(tmp_path, mocker, caplog):
    mocker.patch.object(PluginManager, "_ensure_bundled_plugins", return_value=None)

    version_dir = tmp_path / "plugins" / "org.example" / "dep" / "1.0.0"
    version_dir.mkdir(parents=True)
    (version_dir / "metadata.json").write_text(json.dumps({
        "id": "org.example.dep",
        "version": "1.0.0",
        "type": "viewer",
        "entry_point": "plugin:DepPlugin",
        "python_dependencies": ["quickfile-testdep"],
    }))
    (version_dir / "plugin.py").write_text("""
from plugins.base import ViewerPlugin
class DepPlugin(ViewerPlugin):
    def get_name(self): return "DepPlugin"
    def get_description(self): return "Needs a dependency from libs"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
""")

    info = version_dir / "libs" / "quickfile_testdep-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: quickfile-testdep\nVersion: 1.0\n",
        encoding="utf-8",
    )

    manager = PluginManager(plugin_dirs=[str(tmp_path / "plugins")])
    try:
        assert manager.plugins["viewer"] == []
    finally:
        manager.shutdown()

    assert "sandboxed" in caplog.text


class FakeArchivePlugin:
    def __init__(self, plugin_id, extensions, capabilities):
        self.metadata = {"id": plugin_id, "capabilities": capabilities}
        self.extensions = extensions

    def get_supported_extensions(self):
        return list(self.extensions)


def test_get_archivers_filters_by_capability(plugin_manager):
    creator = FakeArchivePlugin(
        "org.example.creator", ["zip"], [Capability.ARCHIVE_CREATE]
    )
    extractor = FakeArchivePlugin(
        "org.example.extractor", [".rar"], [Capability.ARCHIVE_EXTRACT]
    )
    plugin_manager.plugins["archive"] = [creator, extractor]

    assert plugin_manager.get_archivers(Capability.ARCHIVE_CREATE) == [creator]
    assert plugin_manager.get_archivers(Capability.ARCHIVE_EXTRACT) == [extractor]
    assert plugin_manager.get_archivers() == [creator, extractor]


def test_archiver_lookups_normalize_extensions_and_capabilities(plugin_manager):
    creator = FakeArchivePlugin(
        "org.example.creator", ["zip"], [Capability.ARCHIVE_CREATE]
    )
    extractor = FakeArchivePlugin(
        "org.example.extractor", [".ZIP"], [Capability.ARCHIVE_EXTRACT]
    )
    plugin_manager.plugins["archive"] = [creator, extractor]

    assert (
        plugin_manager.get_archiver_for_extension(
            ".zip", Capability.ARCHIVE_CREATE
        )
        is creator
    )
    assert (
        plugin_manager.get_archiver_for_file(
            "/tmp/archive.ZIP", Capability.ARCHIVE_EXTRACT
        )
        is extractor
    )
    assert (
        plugin_manager.get_archiver_for_file(
            "/tmp/archive.ZIP", Capability.ARCHIVE_CREATE
        )
        is creator
    )


def test_archiver_without_capabilities_stays_available_for_legacy_plugins(
    plugin_manager,
):
    legacy = FakeArchivePlugin("org.example.legacy", ["tar"], [])
    plugin_manager.plugins["archive"] = [legacy]

    assert plugin_manager.get_archivers(Capability.ARCHIVE_CREATE) == [legacy]
    assert plugin_manager.get_archivers(Capability.ARCHIVE_EXTRACT) == [legacy]


def test_a_capability_filter_can_exclude_every_archiver(plugin_manager):
    creator = FakeArchivePlugin(
        "org.example.creator", ["zip"], [Capability.ARCHIVE_CREATE]
    )
    plugin_manager.plugins["archive"] = [creator]

    assert plugin_manager.get_archivers(Capability.ARCHIVE_EXTRACT) == []
    assert (
        plugin_manager.get_archiver_for_file(
            "/tmp/archive.zip", Capability.ARCHIVE_EXTRACT
        )
        is None
    )
