# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Updating an external plugin is an explicit, verified action.

The feed describes available packages; the updater validates the whole feed,
compares numeric versions, downloads into a temporary directory and installs
through ``app.plugin_installer`` only after checking size and SHA-256. Nothing
is removed, so ``rollback`` can disable the newest version and leave the
previous one active.

Specification: ``docs/architecture/plugins/plugins.md``
("Aktualizacja wtyczki zewnętrznej").
"""

import hashlib
import json
import zipfile

import pytest

from app import plugin_updater
from app.plugin_installer import install
from app.plugin_updater import (
    MAX_PACKAGE_SIZE,
    UpdateError,
    check_updates,
    load_feed,
    rollback,
    update_plugin,
)

PLUGIN_ID = "org.example.viewer"

PLUGIN_SOURCE = """
from plugins.base import ViewerPlugin
class UpdaterViewer(ViewerPlugin):
    def get_name(self): return "Updater Viewer"
    def get_description(self): return "Installed by the updater tests"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
"""


class Env:
    def __init__(self, root):
        self.root = root
        self.packages = root / "packages"
        self.feed_dir = root / "feed"
        config = root / ".config" / "QuickFile"
        self.dest = config / "plugins-external"
        self.install_dir = config / "plugins"
        self.install_dir.mkdir(parents=True)


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def package_name(plugin_id, version):
    return f"{plugin_id.rsplit('.', 1)[-1]}-{version}.zip"


def make_package(directory, plugin_id=PLUGIN_ID, version="1.0.0"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / package_name(plugin_id, version)
    entries = {
        "metadata.json": json.dumps(
            {
                "id": plugin_id,
                "version": version,
                "type": "viewer",
                "name": "Updater Viewer",
                "entry_point": "plugin:UpdaterViewer",
            }
        ).encode(),
        "plugin.py": PLUGIN_SOURCE.encode(),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, entries[name])
    return path


def entry_for(path, plugin_id=PLUGIN_ID, version="1.0.0"):
    content = path.read_bytes()
    return {
        "id": plugin_id,
        "version": version,
        "file": path.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def write_feed(feed_dir, packages, schema_version=1):
    feed_dir.mkdir(parents=True, exist_ok=True)
    path = feed_dir / "plugin-index.json"
    path.write_text(
        json.dumps({"schema_version": schema_version, "packages": packages}),
        encoding="utf-8",
    )
    return path.as_uri()


def install_version(env, version, plugin_id=PLUGIN_ID):
    package = make_package(env.packages, plugin_id, version)
    return install(package, dest=env.dest, install_dir=env.install_dir)


def feed_with(env, versions, plugin_id=PLUGIN_ID):
    packages = []
    for version in versions:
        path = make_package(env.feed_dir, plugin_id, version)
        packages.append(entry_for(path, plugin_id, version))
    return write_feed(env.feed_dir, packages)


def test_check_reports_an_update_available(env):
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.1"])

    report = check_updates(url, dest=env.dest, install_dir=env.install_dir)

    assert report.feed == url
    assert [
        (item.plugin_id, item.installed, item.available, item.status)
        for item in report.packages
    ] == [(PLUGIN_ID, "1.0.0", "1.0.1", "update-available")]


def test_check_compares_versions_numerically(env):
    install_version(env, "1.0.9")
    url = feed_with(env, ["1.0.10"])

    report = check_updates(url, dest=env.dest, install_dir=env.install_dir)

    assert report.packages[0].status == "update-available"


def test_check_reports_up_to_date(env):
    install_version(env, "1.0.10")
    url = feed_with(env, ["1.0.9"])

    report = check_updates(url, dest=env.dest, install_dir=env.install_dir)

    assert report.packages[0].available == "1.0.9"
    assert report.packages[0].status == "up-to-date"


def test_check_reports_not_in_feed(env):
    install_version(env, "1.0.0")
    unrelated = make_package(env.feed_dir, "org.example.other", "2.0.0")
    url = write_feed(env.feed_dir, [entry_for(unrelated, "org.example.other", "2.0.0")])

    report = check_updates(url, dest=env.dest, install_dir=env.install_dir)

    assert report.packages[0].status == "not-in-feed"
    assert report.packages[0].available is None


def test_check_reports_a_shipped_plugin_as_managed_by_the_application(env):
    install_version(env, "1.0.0")
    (env.install_dir / "org.example" / "viewer").mkdir(parents=True)
    url = feed_with(env, ["1.0.1"])

    report = check_updates(url, dest=env.dest, install_dir=env.install_dir)

    assert report.packages[0].status == "managed-by-application"


def test_check_reports_every_installed_plugin_sorted_by_id(env):
    install_version(env, "1.0.0", "org.example.zeta")
    install_version(env, "1.0.0", "org.example.alpha")
    zeta = make_package(env.feed_dir, "org.example.zeta", "1.0.1")
    alpha = make_package(env.feed_dir, "org.example.alpha", "1.0.1")
    url = write_feed(
        env.feed_dir,
        [
            entry_for(zeta, "org.example.zeta", "1.0.1"),
            entry_for(alpha, "org.example.alpha", "1.0.1"),
        ],
    )

    report = check_updates(url, dest=env.dest, install_dir=env.install_dir)

    assert [item.plugin_id for item in report.packages] == [
        "org.example.alpha",
        "org.example.zeta",
    ]


def test_check_rejects_a_feed_with_one_broken_entry(env):
    install_version(env, "1.0.0")
    path = make_package(env.feed_dir, PLUGIN_ID, "1.0.1")
    valid = entry_for(path, PLUGIN_ID, "1.0.1")
    broken = dict(valid, sha256="not-a-digest")
    url = write_feed(env.feed_dir, [valid, broken])

    with pytest.raises(UpdateError, match="sha256"):
        check_updates(url, dest=env.dest, install_dir=env.install_dir)


def test_check_rejects_a_newer_schema_version(env):
    url = write_feed(env.feed_dir, [], schema_version=2)

    with pytest.raises(UpdateError, match="schema_version"):
        check_updates(url, dest=env.dest, install_dir=env.install_dir)


def test_an_http_feed_is_refused(env):
    with pytest.raises(UpdateError, match="https or file"):
        check_updates("http://example.com/plugin-index.json", dest=env.dest)


def test_a_missing_feed_file_is_an_error(env):
    with pytest.raises(UpdateError, match="Cannot read"):
        load_feed((env.root / "missing.json").as_uri())


def test_update_installs_the_newer_version_and_keeps_the_old_one(env):
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.1"])

    result = update_plugin(
        PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir
    )

    plugin_path = env.dest / "org.example" / "viewer"
    assert result.status == "installed"
    assert result.plugin_id == PLUGIN_ID
    assert result.version == "1.0.1"
    assert result.path == str(plugin_path / "1.0.1")
    assert (plugin_path / "1.0.0" / "metadata.json").is_file()
    assert (plugin_path / "1.0.1" / "metadata.json").is_file()


def test_update_reports_up_to_date_without_installing(env):
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.0"])

    result = update_plugin(
        PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir
    )

    assert result.status == "up-to-date"
    assert not (env.dest / "org.example" / "viewer" / "1.0.0.disabled").exists()


def test_update_refuses_a_downgrade(env):
    install_version(env, "1.0.1")
    url = feed_with(env, ["1.0.0"])

    with pytest.raises(UpdateError, match="older"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)


def test_update_can_select_an_explicit_version(env):
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.1", "1.0.2"])

    result = update_plugin(
        PLUGIN_ID,
        url,
        version="1.0.1",
        dest=env.dest,
        install_dir=env.install_dir,
    )

    assert result.version == "1.0.1"


def test_update_refuses_a_version_missing_from_the_feed(env):
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.1"])

    with pytest.raises(UpdateError, match="1.2.0"):
        update_plugin(
            PLUGIN_ID,
            url,
            version="1.2.0",
            dest=env.dest,
            install_dir=env.install_dir,
        )


def test_update_refuses_a_plugin_missing_from_the_feed(env):
    install_version(env, "1.0.0")
    url = write_feed(env.feed_dir, [])

    with pytest.raises(UpdateError, match="not in the feed"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)


def test_update_requires_an_installed_plugin(env):
    url = feed_with(env, ["1.0.0"])

    with pytest.raises(UpdateError, match="not installed"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)


def test_update_refuses_a_shipped_plugin(env):
    (env.install_dir / "org.example" / "viewer").mkdir(parents=True)
    url = feed_with(env, ["1.0.1"])

    with pytest.raises(UpdateError, match="shipped"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)


def test_update_refuses_a_size_mismatch_and_leaves_the_installation_alone(env):
    install_version(env, "1.0.0")
    path = make_package(env.feed_dir, PLUGIN_ID, "1.0.1")
    entry = dict(entry_for(path, PLUGIN_ID, "1.0.1"), size=path.stat().st_size + 1)
    url = write_feed(env.feed_dir, [entry])

    with pytest.raises(UpdateError, match="size"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)

    assert not (env.dest / "org.example" / "viewer" / "1.0.1").exists()


def test_update_refuses_a_hash_mismatch_and_leaves_the_installation_alone(env):
    install_version(env, "1.0.0")
    path = make_package(env.feed_dir, PLUGIN_ID, "1.0.1")
    entry = dict(entry_for(path, PLUGIN_ID, "1.0.1"), sha256="0" * 64)
    url = write_feed(env.feed_dir, [entry])

    with pytest.raises(UpdateError, match="SHA-256"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)

    assert not (env.dest / "org.example" / "viewer" / "1.0.1").exists()


def test_update_refuses_an_oversized_package_before_downloading(env):
    install_version(env, "1.0.0")
    path = make_package(env.feed_dir, PLUGIN_ID, "1.0.1")
    entry = dict(entry_for(path, PLUGIN_ID, "1.0.1"), size=MAX_PACKAGE_SIZE + 1)
    url = write_feed(env.feed_dir, [entry])

    with pytest.raises(UpdateError, match="256 MiB"):
        update_plugin(PLUGIN_ID, url, dest=env.dest, install_dir=env.install_dir)


def test_rollback_disables_the_newest_version(env):
    install_version(env, "1.0.0")
    install_version(env, "1.0.1")

    result = rollback(
        PLUGIN_ID, dest=env.dest, install_dir=env.install_dir
    )

    plugin_path = env.dest / "org.example" / "viewer"
    assert result.plugin_id == PLUGIN_ID
    assert result.disabled_version == "1.0.1"
    assert result.active_version == "1.0.0"
    assert (plugin_path / "1.0.1.disabled").is_dir()
    assert (plugin_path / "1.0.0").is_dir()
    assert not (plugin_path / "1.0.1").exists()


def test_rollback_needs_a_previous_version(env):
    install_version(env, "1.0.0")

    with pytest.raises(UpdateError, match="only one"):
        rollback(PLUGIN_ID, dest=env.dest, install_dir=env.install_dir)


def test_rollback_refuses_to_overwrite_a_disabled_version(env):
    install_version(env, "1.0.0")
    install_version(env, "1.0.1")
    (env.dest / "org.example" / "viewer" / "1.0.1.disabled").mkdir()

    with pytest.raises(UpdateError, match="already exists"):
        rollback(PLUGIN_ID, dest=env.dest, install_dir=env.install_dir)


def test_rollback_refuses_a_shipped_plugin(env):
    (env.install_dir / "org.example" / "viewer").mkdir(parents=True)

    with pytest.raises(UpdateError, match="shipped"):
        rollback(PLUGIN_ID, dest=env.dest, install_dir=env.install_dir)


def test_rollback_refuses_an_uninstalled_plugin(env):
    with pytest.raises(UpdateError, match="not installed"):
        rollback(PLUGIN_ID, dest=env.dest, install_dir=env.install_dir)


def test_the_cli_prints_json_for_check(env, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(env.root))
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.1"])

    exit_code = plugin_updater.main(["check", "--feed", url, "--json"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["feed"] == url
    assert output["packages"] == [
        {
            "id": PLUGIN_ID,
            "installed": "1.0.0",
            "available": "1.0.1",
            "status": "update-available",
        }
    ]


def test_the_cli_installs_an_update(env, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(env.root))
    install_version(env, "1.0.0")
    url = feed_with(env, ["1.0.1"])

    exit_code = plugin_updater.main(["update", PLUGIN_ID, "--feed", url])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1.0.1" in output
    assert str(env.dest / "org.example" / "viewer" / "1.0.1") in output


def test_the_cli_returns_one_on_a_bad_feed(env, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(env.root))

    exit_code = plugin_updater.main(
        ["check", "--feed", "http://example.com/plugin-index.json"]
    )

    assert exit_code == 1
    assert "https or file" in capsys.readouterr().err
