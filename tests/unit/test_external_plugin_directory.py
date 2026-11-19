# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The host scans a user-managed plugin directory next to the install directory.

``plugins-external/`` is where plugins live that cannot ship with the app: they
need a host binary or cannot be redistributed. The host must not install into
it, and an external copy must not shadow a plugin that came with the release.

Specification: ``docs/architecture/plugins/plugins.md`` ("Wtyczki zewnętrzne").
"""

import json

import pytest

from app.plugin_manager import PluginManager


VIEWER_SOURCE = """
from plugins.base import ViewerPlugin
class {class_name}(ViewerPlugin):
    def get_name(self): return "{name}"
    def get_description(self): return "Test viewer"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
"""


def write_plugin(root, plugin_id, version, name):
    artifact_id = plugin_id.split(".")[-1]
    group_id = plugin_id.rsplit(".", 1)[0]
    version_dir = root / group_id / artifact_id / version
    version_dir.mkdir(parents=True)

    class_name = name.replace(" ", "") + "Plugin"
    (version_dir / "metadata.json").write_text(
        json.dumps(
            {
                "id": plugin_id,
                "version": version,
                "type": "viewer",
                "entry_point": f"plugin:{class_name}",
            }
        ),
        encoding="utf-8",
    )
    (version_dir / "plugin.py").write_text(
        VIEWER_SOURCE.format(class_name=class_name, name=name), encoding="utf-8"
    )
    return version_dir


@pytest.fixture
def separate_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(PluginManager, "_ensure_bundled_plugins", lambda self: None)
    install = tmp_path / "plugins"
    external = tmp_path / "plugins-external"
    install.mkdir()
    external.mkdir()
    return install, external


def test_plugins_are_loaded_from_both_directories(separate_dirs):
    install, external = separate_dirs
    write_plugin(install, "org.example.shipped", "1.0.0", "Shipped")
    write_plugin(external, "org.example.user", "1.0.0", "User Installed")

    manager = PluginManager(plugin_dirs=[str(install), str(external)])
    try:
        loaded = {plugin.metadata["id"]: plugin for plugin in manager.plugins["viewer"]}

        assert set(loaded) == {"org.example.shipped", "org.example.user"}
        assert loaded["org.example.user"].get_name() == "User Installed"
    finally:
        manager.shutdown()


def test_a_disabled_artifact_directory_is_not_loaded(separate_dirs):
    install, external = separate_dirs
    write_plugin(install, "org.example.shipped", "1.0.0", "Shipped")
    write_plugin(external, "org.example.user", "1.0.0", "User Installed")
    (external / "org.example" / "user").rename(
        external / "org.example" / "user.disabled"
    )

    manager = PluginManager(plugin_dirs=[str(install), str(external)])
    try:
        assert {
            plugin.metadata["id"] for plugin in manager.plugins["viewer"]
        } == {"org.example.shipped"}
    finally:
        manager.shutdown()


def test_a_missing_external_directory_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(PluginManager, "_ensure_bundled_plugins", lambda self: None)
    install = tmp_path / "plugins"
    install.mkdir()
    write_plugin(install, "org.example.shipped", "1.0.0", "Shipped")

    manager = PluginManager(
        plugin_dirs=[str(install), str(tmp_path / "does-not-exist")]
    )
    try:
        assert [plugin.metadata["id"] for plugin in manager.plugins["viewer"]] == [
            "org.example.shipped"
        ]
    finally:
        manager.shutdown()


def test_an_external_copy_does_not_shadow_a_shipped_plugin(separate_dirs, caplog):
    install, external = separate_dirs
    write_plugin(install, "org.example.viewer", "1.0.0", "Shipped")
    write_plugin(external, "org.example.viewer", "9.0.0", "User Override")

    manager = PluginManager(plugin_dirs=[str(install), str(external)])
    try:
        names = [plugin.get_name() for plugin in manager.plugins["viewer"]]

        assert names == ["Shipped"]
        assert "org.example.viewer" in caplog.text
        assert "conflict" in caplog.text.lower()
    finally:
        manager.shutdown()


def test_the_default_layout_scans_the_external_directory_last(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(PluginManager, "_ensure_bundled_plugins", lambda self: None)

    manager = PluginManager()
    try:
        install = tmp_path / ".config" / "QuickFile" / "plugins"
        external = tmp_path / ".config" / "QuickFile" / "plugins-external"
        assert manager.plugin_dirs == [str(install), str(external)]
    finally:
        manager.shutdown()


def test_the_app_never_installs_plugins_into_the_external_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    manager = PluginManager()
    try:
        config_dir = tmp_path / ".config" / "QuickFile"
        assert (config_dir / "plugins").is_dir()
        assert not (config_dir / "plugins-external").exists(), (
            "only the first plugin directory is an install target"
        )
    finally:
        manager.shutdown()
