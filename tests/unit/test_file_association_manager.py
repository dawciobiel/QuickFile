# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""File associations open files with the OS program by default."""

import json

from app.file_association_manager import (
    CONFIG_VERSION,
    FileAction,
    FileAssociationManager,
)


def config_path(home):
    return home / ".config" / "QuickFile" / "file_associations.json"


def write_config(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_new_install_uses_system_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    manager = FileAssociationManager()

    assert manager.get_action_for_file(str(tmp_path / "a.txt")) == (
        FileAction.SYSTEM_DEFAULT,
        None,
    )
    assert manager.get_action_for_file(str(tmp_path / "a.png")) == (
        FileAction.SYSTEM_DEFAULT,
        None,
    )
    saved = json.loads(config_path(tmp_path).read_text(encoding="utf-8"))
    assert saved["version"] == CONFIG_VERSION
    assert all(
        association["action"] == "system_default"
        for association in saved["associations"]
    )


def test_unlisted_types_use_the_system_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    manager = FileAssociationManager()

    for name in ("movie.mp4", "clip.mkv", "song.mp3", "archive.zip"):
        assert manager.get_action_for_file(str(tmp_path / name)) == (
            FileAction.SYSTEM_DEFAULT,
            None,
        )


def test_version_1_default_config_is_migrated(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    write_config(
        config_path(tmp_path),
        {
            "associations": [
                {
                    "name": "Text Files",
                    "extensions": ["txt"],
                    "action": "internal_viewer",
                },
                {
                    "name": "Images",
                    "extensions": ["png"],
                    "action": "internal_viewer",
                },
            ],
            "default_action": "system_default",
        },
    )

    manager = FileAssociationManager()

    assert manager.get_action_for_file("a.txt") == (
        FileAction.SYSTEM_DEFAULT,
        None,
    )
    assert manager.get_action_for_file("a.png") == (
        FileAction.SYSTEM_DEFAULT,
        None,
    )
    saved = json.loads(config_path(tmp_path).read_text(encoding="utf-8"))
    assert saved["version"] == CONFIG_VERSION


def test_custom_associations_survive_migration(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    write_config(
        config_path(tmp_path),
        {
            "associations": [
                {
                    "name": "Logs",
                    "extensions": ["log"],
                    "action": "internal_editor",
                },
                {
                    "name": "Text Files",
                    "extensions": ["txt"],
                    "action": "internal_viewer",
                },
            ],
            "default_action": "system_default",
        },
    )

    manager = FileAssociationManager()

    assert manager.get_action_for_file("a.log") == (
        FileAction.INTERNAL_EDITOR,
        None,
    )
    assert manager.get_action_for_file("a.txt") == (
        FileAction.SYSTEM_DEFAULT,
        None,
    )
