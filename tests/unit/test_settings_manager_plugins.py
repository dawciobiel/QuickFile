# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Plugin settings are persisted per plugin id, not per display name."""

import pytest

from app.settings_manager import SettingsManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return SettingsManager()


def test_a_plugin_without_settings_gets_an_empty_mapping(manager):
    assert manager.get_plugin_settings("org.example.zip") == {}


def test_plugin_settings_are_stored_per_plugin(manager, tmp_path):
    manager.set_plugin_settings("org.example.zip", {"compresslevel": 9})
    manager.set_plugin_settings("org.example.rar", {"password": "secret"})

    reloaded = SettingsManager()

    assert reloaded.get_plugin_settings("org.example.zip") == {"compresslevel": 9}
    assert reloaded.get_plugin_settings("org.example.rar") == {"password": "secret"}


def test_get_plugin_settings_returns_a_copy(manager):
    manager.set_plugin_settings("org.example.zip", {"compresslevel": 9})

    options = manager.get_plugin_settings("org.example.zip")
    options["compresslevel"] = 1

    assert manager.get_plugin_settings("org.example.zip") == {"compresslevel": 9}


def test_a_corrupted_plugin_settings_value_does_not_break_the_manager(manager):
    manager.settings["plugin_settings"] = "broken"

    assert manager.get_plugin_settings("org.example.zip") == {}

    manager.set_plugin_settings("org.example.zip", {"compresslevel": 9})

    assert manager.get_plugin_settings("org.example.zip") == {"compresslevel": 9}


def test_a_corrupted_entry_for_one_plugin_is_ignored(manager):
    manager.settings["plugin_settings"] = {"org.example.zip": "broken"}

    assert manager.get_plugin_settings("org.example.zip") == {}
