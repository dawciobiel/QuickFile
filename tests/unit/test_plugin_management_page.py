# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
The settings page drives the same operations as the updater CLI.

Opening the page only scans the local plugin directory. Checking and updating
are explicit actions and run through an injected runner; tests use a
synchronous runner so no thread or network is involved.

Specification: ``docs/architecture/plugins/plugins.md``
("Zarządzanie wtyczkami zewnętrznymi").
"""

import hashlib
import json
import zipfile

import pytest

from app.plugin_installer import install
from app.plugin_management import PluginManagementService
from app.plugin_state import disable_plugin
from utils.plugin_management_page import PluginManagementPage


PLUGIN_ID = "org.example.viewer"

PLUGIN_SOURCE = """
from plugins.base import ViewerPlugin
class Viewer(ViewerPlugin):
    def get_name(self): return "Managed Viewer"
    def get_description(self): return "Managed by the settings page tests"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
"""


class Env:
    def __init__(self, root):
        self.root = root
        self.packages = root / "packages"
        config = root / ".config" / "QuickFile"
        self.dest = config / "plugins-external"
        self.install_dir = config / "plugins"
        self.install_dir.mkdir(parents=True)
        self.feed_dir = root / "feed"


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def run_sync(function, on_success, on_error):
    try:
        result = function()
    except Exception as error:  # noqa: BLE001 - mirrors the production runner
        on_error(str(error))
    else:
        on_success(result)


def make_package(directory, version="1.0.0", plugin_id=PLUGIN_ID):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{plugin_id.rsplit('.', 1)[-1]}-{version}.zip"
    entries = {
        "metadata.json": json.dumps(
            {
                "id": plugin_id,
                "version": version,
                "type": "viewer",
                "name": "Managed Viewer",
                "entry_point": "plugin:Viewer",
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


def install_version(env, version, plugin_id=PLUGIN_ID):
    package = make_package(env.packages, version, plugin_id)
    return install(package, dest=env.dest, install_dir=env.install_dir)


def entry_for(path, version, plugin_id=PLUGIN_ID):
    content = path.read_bytes()
    return {
        "id": plugin_id,
        "version": version,
        "file": path.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def feed_with(env, versions, plugin_id=PLUGIN_ID):
    packages = []
    for version in versions:
        path = make_package(env.feed_dir, version, plugin_id)
        packages.append(entry_for(path, version, plugin_id))
    env.feed_dir.mkdir(parents=True, exist_ok=True)
    index = env.feed_dir / "plugin-index.json"
    index.write_text(
        json.dumps({"schema_version": 1, "packages": packages}),
        encoding="utf-8",
    )
    return index.as_uri()


def make_page(env, feed=None):
    service = PluginManagementService(
        feed=feed or feed_with(env, []),
        dest=env.dest,
        install_dir=env.install_dir,
    )
    return PluginManagementPage(service=service, runner=run_sync)


def row_for(page, plugin_id=PLUGIN_ID):
    for row in range(page.table.rowCount()):
        if page.table.item(row, 0).text() == plugin_id:
            return row
    raise AssertionError(f"{plugin_id} is not in the table")


def status_for(page, plugin_id=PLUGIN_ID):
    return page._statuses[plugin_id]


def test_the_page_lists_plugins_without_checking_the_feed(qapp, env):
    install_version(env, "1.0.0")

    page = make_page(env)
    try:
        row = row_for(page)
        assert page.table.item(row, 1).text() == "1.0.0"
        assert page.table.item(row, 2).text() == ""
        assert status_for(page) == "not-checked"
        assert page.message_label.text() == ""
    finally:
        page.deleteLater()


def test_check_marks_an_update_available(qapp, env):
    install_version(env, "1.0.0")
    page = make_page(env, feed_with(env, ["1.0.1"]))
    try:
        page.table.selectRow(0)
        page.check_button.click()

        row = row_for(page)
        assert page.table.item(row, 2).text() == "1.0.1"
        assert status_for(page) == "update-available"
        assert page.update_button.isEnabled()
    finally:
        page.deleteLater()


def test_update_installs_the_selected_plugin(qapp, env):
    install_version(env, "1.0.0")
    page = make_page(env, feed_with(env, ["1.0.1"]))
    try:
        page.table.selectRow(0)
        page.check_button.click()
        page.table.selectRow(0)
        page.update_button.click()

        assert (env.dest / "org.example" / "viewer" / "1.0.1").is_dir()
        assert (env.dest / "org.example" / "viewer" / "1.0.0").is_dir()
        assert "1.0.1" in page.message_label.text()
        assert "Restart" in page.message_label.text()
        assert page.table.item(row_for(page), 1).text() == "1.0.1"
    finally:
        page.deleteLater()


def test_rollback_switches_to_the_previous_version(qapp, env):
    install_version(env, "1.0.0")
    install_version(env, "1.0.1")
    page = make_page(env)
    try:
        page.table.selectRow(0)
        assert page.rollback_button.isEnabled()
        page.rollback_button.click()

        assert (env.dest / "org.example" / "viewer" / "1.0.1.disabled").is_dir()
        assert page.table.item(row_for(page), 1).text() == "1.0.0"
        assert "1.0.0" in page.message_label.text()
    finally:
        page.deleteLater()


def test_toggle_disables_and_enables_a_plugin(qapp, env):
    install_version(env, "1.0.0")
    page = make_page(env)
    try:
        page.table.selectRow(0)
        assert page.toggle_button.text() == "Disable"
        page.toggle_button.click()

        assert status_for(page) == "disabled"
        assert page.toggle_button.text() == "Enable"
        assert (env.dest / "org.example" / "viewer.disabled" / "1.0.0").is_dir()

        page.table.selectRow(0)
        page.toggle_button.click()

        assert status_for(page) == "not-checked"
        assert (env.dest / "org.example" / "viewer" / "1.0.0").is_dir()
    finally:
        page.deleteLater()


def test_a_disabled_plugin_stays_disabled_after_a_check(qapp, env):
    install_version(env, "1.0.0")
    disable_plugin(PLUGIN_ID, destination=env.dest, install_dir=env.install_dir)
    page = make_page(env, feed_with(env, ["1.0.1"]))
    try:
        page.table.selectRow(0)
        page.check_button.click()

        assert status_for(page) == "disabled"
        assert page.table.item(row_for(page), 2).text() == ""
        assert not page.update_button.isEnabled()
    finally:
        page.deleteLater()


def test_a_feed_error_is_shown_inline(qapp, env):
    install_version(env, "1.0.0")
    page = make_page(env, feed="http://example.com/plugin-index.json")
    try:
        page.check_button.click()

        assert "https or file" in page.message_label.text()
        assert status_for(page) == "not-checked"
    finally:
        page.deleteLater()


def test_actions_need_a_selection(qapp, env):
    install_version(env, "1.0.0")
    page = make_page(env)
    try:
        assert not page.update_button.isEnabled()
        assert not page.rollback_button.isEnabled()
        assert not page.toggle_button.isEnabled()
    finally:
        page.deleteLater()


def test_a_shipped_plugin_is_not_toggled(qapp, env):
    install_version(env, "1.0.0")
    (env.install_dir / "org.example" / "viewer").mkdir(parents=True)
    page = make_page(env, feed_with(env, ["1.0.1"]))
    try:
        page.table.selectRow(0)
        page.check_button.click()
        page.table.selectRow(0)

        assert status_for(page) == "managed-by-application"
        assert not page.toggle_button.isEnabled()
    finally:
        page.deleteLater()


def test_the_settings_dialog_exposes_the_plugins_page(qapp, env, monkeypatch):
    monkeypatch.setenv("HOME", str(env.root))
    from app.settings_manager import SettingsManager
    from app.theme_manager import ThemeManager
    from utils.settings_dialog import SettingsDialog

    settings = SettingsManager()
    dialog = SettingsDialog(None, settings, ThemeManager(settings))
    try:
        assert "Plugins" in dialog.items
        assert isinstance(dialog.pages["Plugins"], PluginManagementPage)
    finally:
        dialog.deleteLater()
