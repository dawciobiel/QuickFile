# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract for host binaries required by plugins.

``python_dependencies`` cannot express "this package needs a program in PATH".
The host validates the declaration, resolves one executable with
``shutil.which`` and refuses nothing on its own: deciding what to do about a
missing tool belongs to the caller.

Specification: ``docs/architecture/plugins/plugins.md`` ("Narzędzia zewnętrzne").
"""

import json

import pytest

from app.external_tools import (
    ExternalToolsError,
    check_tools,
    missing_tools,
    requirements_for,
)
from app.plugin_manager import PluginManager


RAR_METADATA = {
    "id": "org.quickfile.rar_archiver",
    "name": "RAR Archiver",
    "external_tools": [
        {
            "id": "rar_backend",
            "name": "RAR extraction backend",
            "executables": ["unrar", "unar", "bsdtar", "7z", "7zz"],
        }
    ],
}


def fake_which(available):
    """Report only the given commands as installed."""

    def which(command):
        return "/usr/bin/" + command if command in available else None

    return which


def test_metadata_without_declarations_has_no_requirements():
    assert requirements_for({"id": "org.example.plain"}) == []
    assert requirements_for({}) == []
    assert requirements_for(None) == []


def test_a_declaration_becomes_a_requirement():
    (requirement,) = requirements_for(RAR_METADATA)

    assert requirement.id == "rar_backend"
    assert requirement.name == "RAR extraction backend"
    assert requirement.executables == ("unrar", "unar", "bsdtar", "7z", "7zz")


@pytest.mark.parametrize("available", [{"unrar"}, {"bsdtar"}, {"7zz"}])
def test_any_listed_executable_satisfies_the_requirement(available):
    (status,) = check_tools(RAR_METADATA, which=fake_which(available))

    assert status.available
    assert status.executable == "/usr/bin/" + next(iter(available))
    assert missing_tools(RAR_METADATA, which=fake_which(available)) == []


def test_the_first_listed_executable_wins_and_later_ones_are_not_asked():
    asked = []

    def which(command):
        asked.append(command)
        return "/opt/bin/bsdtar" if command == "bsdtar" else None

    (status,) = check_tools(RAR_METADATA, which=which)

    assert status.executable == "/opt/bin/bsdtar"
    assert asked == ["unrar", "unar", "bsdtar"]


def test_a_missing_tool_is_reported_with_all_candidates():
    (status,) = missing_tools(RAR_METADATA, which=fake_which(set()))

    assert status.requirement.id == "rar_backend"
    assert not status.available
    assert status.executable is None
    assert status.requirement.executables == ("unrar", "unar", "bsdtar", "7z", "7zz")


def test_only_unsatisfied_requirements_are_reported():
    metadata = {
        "external_tools": [
            {"id": "present", "name": "Present", "executables": ["installed"]},
            {"id": "absent", "name": "Absent", "executables": ["gone"]},
        ]
    }

    missing = missing_tools(metadata, which=fake_which({"installed"}))

    assert [status.requirement.id for status in missing] == ["absent"]


@pytest.mark.parametrize(
    "declaration",
    [
        {"id": "x", "name": "Kind", "executables": ["unrar"]},
        ["unrar"],
        [{"name": "Kind", "executables": ["unrar"]}],
        [{"id": "", "name": "Kind", "executables": ["unrar"]}],
        [{"id": "x", "executables": ["unrar"]}],
        [{"id": "x", "name": "", "executables": ["unrar"]}],
        [{"id": "x", "name": "Kind"}],
        [{"id": "x", "name": "Kind", "executables": []}],
        [{"id": "x", "name": "Kind", "executables": "unrar"}],
        [{"id": "x", "name": "Kind", "executables": [""]}],
        [{"id": "x", "name": "Kind", "executables": [1]}],
        [{"id": "x", "name": "Kind", "executables": ["/usr/bin/unrar"]}],
        [{"id": "x", "name": "Kind", "executables": ["bin\\unrar"]}],
        [
            {"id": "x", "name": "One", "executables": ["one"]},
            {"id": "x", "name": "Two", "executables": ["two"]},
        ],
    ],
)
def test_invalid_declarations_are_rejected(declaration):
    with pytest.raises(ExternalToolsError):
        requirements_for({"external_tools": declaration})


def test_a_plugin_with_a_malformed_declaration_is_not_loaded(
    tmp_path, monkeypatch, caplog
):
    monkeypatch.setattr(PluginManager, "_ensure_bundled_plugins", lambda self: None)

    version_dir = tmp_path / "plugins" / "org.example" / "broken_tools" / "1.0.0"
    version_dir.mkdir(parents=True)
    (version_dir / "metadata.json").write_text(
        json.dumps(
            {
                "id": "org.example.broken_tools",
                "version": "1.0.0",
                "type": "viewer",
                "entry_point": "plugin:BrokenTools",
                "external_tools": [{"id": "backend", "name": "Backend"}],
            }
        ),
        encoding="utf-8",
    )
    (version_dir / "plugin.py").write_text(
        """
from plugins.base import ViewerPlugin
class BrokenTools(ViewerPlugin):
    def get_name(self): return "BrokenTools"
    def get_description(self): return "Declares tools without executables"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
""",
        encoding="utf-8",
    )

    manager = PluginManager(plugin_dirs=[str(tmp_path / "plugins")])
    try:
        assert manager.plugins["viewer"] == []
    finally:
        manager.shutdown()

    assert "external_tools" in caplog.text
    assert "org.example.broken_tools" in caplog.text
