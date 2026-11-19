# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
External plugins can be disabled without deleting anything.

A whole plugin is disabled by renaming its artifact directory to
``<artifact>.disabled``; the loader ignores that suffix. The state lives only on
disk, so enabling it again is a rename back. Collisions and shipped ids are
refusals, never silent overwrites.

Specification: ``docs/architecture/plugins/plugins.md``
("Zarządzanie wtyczkami zewnętrznymi").
"""

import json

import pytest

from app.plugin_state import (
    PluginStateError,
    disable_plugin,
    enable_plugin,
    scan_external_plugins,
)
from app.plugin_updater import check_updates


PLUGIN_ID = "org.example.viewer"


def write_version(version_dir, plugin_id=PLUGIN_ID, version="1.0.0", name=None):
    version_dir.mkdir(parents=True)
    (version_dir / "metadata.json").write_text(
        json.dumps(
            {
                "id": plugin_id,
                "version": version,
                "type": "viewer",
                "name": name or plugin_id.rsplit(".", 1)[-1],
                "entry_point": "plugin:Viewer",
            }
        ),
        encoding="utf-8",
    )
    return version_dir


def write_plugin(root, plugin_id=PLUGIN_ID, version="1.0.0", name=None):
    group_id, _, artifact_id = plugin_id.rpartition(".")
    return write_version(
        root / group_id / artifact_id / version, plugin_id, version, name
    )


@pytest.fixture
def dirs(tmp_path):
    install_dir = tmp_path / "plugins"
    install_dir.mkdir()
    dest = tmp_path / "plugins-external"
    return dest, install_dir


def test_scan_reports_the_highest_active_version(dirs):
    dest, _ = dirs
    write_plugin(dest, version="1.0.9")
    write_plugin(dest, version="1.0.10")

    plugins = scan_external_plugins(dest)

    assert [(item.plugin_id, item.version, item.enabled) for item in plugins] == [
        (PLUGIN_ID, "1.0.10", True)
    ]
    assert plugins[0].versions == ("1.0.10", "1.0.9")


def test_scan_includes_disabled_plugins(dirs):
    dest, _ = dirs
    write_plugin(dest)
    disable_plugin(PLUGIN_ID, destination=dest, install_dir=dirs[1])

    plugins = scan_external_plugins(dest)

    assert [(item.plugin_id, item.enabled) for item in plugins] == [(PLUGIN_ID, False)]
    assert plugins[0].path.endswith("viewer.disabled")


def test_disabling_renames_the_artifact_directory(dirs):
    dest, install_dir = dirs
    write_plugin(dest)

    result = disable_plugin(
        PLUGIN_ID, destination=dest, install_dir=install_dir
    )

    assert result.enabled is False
    assert (dest / "org.example" / "viewer.disabled" / "1.0.0").is_dir()
    assert not (dest / "org.example" / "viewer").exists()


def test_enabling_renames_the_directory_back(dirs):
    dest, install_dir = dirs
    write_plugin(dest)
    disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)

    result = enable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)

    assert result.enabled is True
    assert (dest / "org.example" / "viewer" / "1.0.0").is_dir()
    assert not (dest / "org.example" / "viewer.disabled").exists()


def test_disabling_an_uninstalled_plugin_is_an_error(dirs):
    dest, install_dir = dirs

    with pytest.raises(PluginStateError, match="not installed"):
        disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)


def test_enabling_an_active_plugin_is_an_error(dirs):
    dest, install_dir = dirs
    write_plugin(dest)

    with pytest.raises(PluginStateError, match="already enabled"):
        enable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)


def test_disabling_a_shipped_plugin_is_refused(dirs):
    dest, install_dir = dirs
    (install_dir / "org.example" / "viewer").mkdir(parents=True)

    with pytest.raises(PluginStateError, match="shipped"):
        disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)


def test_enabling_a_shipped_plugin_is_refused(dirs):
    dest, install_dir = dirs
    write_plugin(dest)
    disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)
    (install_dir / "org.example" / "viewer").mkdir(parents=True)

    with pytest.raises(PluginStateError, match="shipped"):
        enable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)


def test_disabling_refuses_an_existing_disabled_directory(dirs):
    dest, install_dir = dirs
    write_plugin(dest)
    (dest / "org.example" / "viewer.disabled").mkdir()

    with pytest.raises(PluginStateError, match="already exists"):
        disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)


def test_enabling_refuses_an_existing_active_directory(dirs):
    dest, install_dir = dirs
    write_plugin(dest)
    disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)
    (dest / "org.example" / "viewer").mkdir()

    with pytest.raises(PluginStateError, match="already exists"):
        enable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)


def test_scan_skips_directories_without_metadata(dirs):
    dest, _ = dirs
    write_plugin(dest)
    (dest / "org.example" / "broken" / "1.0.0").mkdir(parents=True)

    plugins = scan_external_plugins(dest)

    assert [item.plugin_id for item in plugins] == [PLUGIN_ID]


def test_scan_refuses_duplicate_plugin_ids(dirs):
    dest, _ = dirs
    write_plugin(dest)
    write_version(dest / "org.example" / "viewer.disabled" / "1.0.0")

    with pytest.raises(PluginStateError, match="more than one"):
        scan_external_plugins(dest)


def test_check_ignores_disabled_plugins(dirs, tmp_path):
    dest, install_dir = dirs
    write_plugin(dest)
    disable_plugin(PLUGIN_ID, destination=dest, install_dir=install_dir)
    feed = tmp_path / "feed"
    feed.mkdir()
    (feed / "plugin-index.json").write_text(
        json.dumps({"schema_version": 1, "packages": []}), encoding="utf-8"
    )

    report = check_updates(
        (feed / "plugin-index.json").as_uri(),
        dest=dest,
        install_dir=install_dir,
    )

    assert report.packages == ()
