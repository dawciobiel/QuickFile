# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Tests for synchronising bundled plugins into the user plugin directory.

The regression these tests exist for: the sync compared version *numbers* only.
After the architecture-v3 refactor the same version could carry different
content, and a stale "newer" copy (1.0.4) from a feature branch was never
replaced by the working 1.0.0 shipped with the application. Every plugin then
failed to import and the UI crashed at startup.
"""

import json
import re
import time

import pytest

from app.plugin_manager import PluginManager


def make_manager():
    """Create a PluginManager without running __init__ side effects."""
    manager = object.__new__(PluginManager)
    manager.version_regex = re.compile(r"^\d+(\.\d+)*$")
    return manager


def write_plugin(root, org, name, version, body):
    version_dir = root / org / name / version
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "metadata.json").write_text(
        json.dumps(
            {
                "id": f"{org}.{name}",
                "version": version,
                "type": "viewer",
                "entry_point": "plugin:Plugin",
            }
        )
    )
    (version_dir / "plugin.py").write_text(body)
    return version_dir


@pytest.fixture
def dirs(tmp_path):
    bundled = tmp_path / "bundled"
    user = tmp_path / "user"
    bundled.mkdir()
    user.mkdir()
    return bundled, user


def test_installs_missing_bundled_plugin(dirs):
    bundled, user = dirs
    write_plugin(bundled, "org.quickfile", "viewer", "1.0.0", "WORKING = True\n")

    make_manager()._sync_bundled_plugin_dirs(str(bundled), str(user))

    installed = user / "org.quickfile" / "viewer" / "1.0.0" / "plugin.py"
    assert installed.read_text() == "WORKING = True\n"


def test_refreshes_same_version_with_different_content(dirs):
    bundled, user = dirs
    write_plugin(bundled, "org.quickfile", "viewer", "1.0.0", "from app.plugin_system.api import PluginBase\n")
    stale = write_plugin(user, "org.quickfile", "viewer", "1.0.0", "from quickfile.app.plugin_system.api import PluginBase\n")

    make_manager()._sync_bundled_plugin_dirs(str(bundled), str(user))

    assert stale.joinpath("plugin.py").read_text().startswith("from app.")


def test_removes_stale_version_directories(dirs):
    bundled, user = dirs
    write_plugin(bundled, "org.quickfile", "copy_operation", "1.0.0", "OK = True\n")
    write_plugin(user, "org.quickfile", "copy_operation", "1.0.4", "BROKEN = True\n")

    make_manager()._sync_bundled_plugin_dirs(str(bundled), str(user))

    plugin_dir = user / "org.quickfile" / "copy_operation"
    assert sorted(p.name for p in plugin_dir.iterdir()) == ["1.0.0"]


def test_preserves_user_installed_libs(dirs):
    bundled, user = dirs
    write_plugin(bundled, "org.quickfile", "splitter", "1.0.0", "OK = True\n")
    version_dir = write_plugin(user, "org.quickfile", "splitter", "1.0.0", "STALE = True\n")
    libs = version_dir / "libs" / "some_dependency"
    libs.mkdir(parents=True)
    (libs / "__init__.py").write_text("")

    make_manager()._sync_bundled_plugin_dirs(str(bundled), str(user))

    assert (version_dir / "plugin.py").read_text() == "OK = True\n"
    assert (libs / "__init__.py").exists()


def test_unchanged_plugin_is_not_rewritten(dirs):
    bundled, user = dirs
    write_plugin(bundled, "org.quickfile", "viewer", "1.0.0", "SAME = True\n")
    write_plugin(user, "org.quickfile", "viewer", "1.0.0", "SAME = True\n")
    installed = user / "org.quickfile" / "viewer" / "1.0.0" / "plugin.py"
    before = installed.stat().st_mtime_ns

    make_manager()._sync_bundled_plugin_dirs(str(bundled), str(user))

    assert installed.stat().st_mtime_ns == before


def test_plugin_that_fails_to_start_is_not_registered(tmp_path, mocker):
    """A sandboxed plugin whose process dies must not reach the UI."""
    plugin_dir = tmp_path / "plugins"
    version_dir = plugin_dir / "org.example" / "broken" / "1.0.0"
    version_dir.mkdir(parents=True)
    (version_dir / "metadata.json").write_text(
        json.dumps(
            {
                "id": "org.example.broken",
                "version": "1.0.0",
                "type": "viewer",
                "entry_point": "plugin:Broken",
                "sandboxed": True,
            }
        )
    )
    (version_dir / "plugin.py").write_text("raise ImportError('broken plugin')\n")

    mocker.patch.object(PluginManager, "_ensure_bundled_plugins", return_value=None)

    started = time.monotonic()
    manager = PluginManager(plugin_dirs=[str(plugin_dir)])
    elapsed = time.monotonic() - started

    try:
        assert manager.plugins["viewer"] == []
        # Fail fast: a dead process must not cost the full startup timeout.
        assert elapsed < 3
    finally:
        manager.shutdown()
