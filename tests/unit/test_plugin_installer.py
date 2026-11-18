# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Installing an external plugin is an explicit, offline action.

A package is a zip of one plugin version directory (or that directory itself).
The installer derives the destination from metadata, validates everything first
and only then moves the result into plugins-external/. Overwrites are refusals:
a shipped id would be ignored by the loader anyway, and replacing a version in
place would hide what changed.

Specification: ``docs/architecture/plugins/plugins.md``
("Instalacja wtyczki zewnętrznej").
"""

import json
import os
import zipfile

import pytest

from app import plugin_installer
from app.plugin_installer import PluginInstallationError, install


PLUGIN_SOURCE = """
from plugins.base import ViewerPlugin
class {class_name}(ViewerPlugin):
    def get_name(self): return "{name}"
    def get_description(self): return "Installed from a package"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
"""


def metadata(**overrides):
    data = {
        "id": "org.example.installed",
        "version": "1.0.0",
        "type": "viewer",
        "name": "Installed Viewer",
        "entry_point": "plugin:InstalledViewer",
    }
    data.update(overrides)
    return data


def write_package(root, **overrides):
    root.mkdir(parents=True, exist_ok=True)
    meta = metadata(**overrides)
    (root / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (root / "plugin.py").write_text(
        PLUGIN_SOURCE.format(class_name="InstalledViewer", name=meta.get("name")),
        encoding="utf-8",
    )
    return root


def zip_package(source, archive_path, arc_prefix=""):
    with zipfile.ZipFile(archive_path, "w") as archive:
        for dirpath, _, filenames in os.walk(source):
            for filename in filenames:
                absolute = os.path.join(dirpath, filename)
                relative = os.path.relpath(absolute, source)
                arcname = os.path.join(arc_prefix, relative) if arc_prefix else relative
                archive.write(absolute, arcname)
    return archive_path


@pytest.fixture
def dirs(tmp_path):
    install_dir = tmp_path / "plugins"
    install_dir.mkdir()
    dest = tmp_path / "plugins-external"
    return install_dir, dest


def test_a_version_directory_is_installed_under_its_metadata_id(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(tmp_path / "pkg")

    result = install(package, dest=dest, install_dir=install_dir)

    target = dest / "org.example" / "installed" / "1.0.0"
    assert result.path == str(target)
    assert result.plugin_id == "org.example.installed"
    assert result.version == "1.0.0"
    assert (target / "metadata.json").is_file()
    assert (target / "plugin.py").is_file()


def test_a_zip_of_the_version_directory_is_installed(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(tmp_path / "pkg")
    archive = zip_package(package, tmp_path / "plugin.zip")

    result = install(archive, dest=dest, install_dir=install_dir)

    assert (dest / "org.example" / "installed" / "1.0.0" / "metadata.json").is_file()
    assert result.version == "1.0.0"


def test_a_zip_that_wraps_the_directory_in_a_folder_is_accepted(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(tmp_path / "pkg")
    archive = zip_package(package, tmp_path / "plugin.zip", arc_prefix="installed")

    install(archive, dest=dest, install_dir=install_dir)

    assert (dest / "org.example" / "installed" / "1.0.0" / "plugin.py").is_file()


def test_directory_entries_in_the_archive_are_skipped(tmp_path, dirs):
    install_dir, dest = dirs
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("metadata.json", json.dumps(metadata()))
        handle.writestr("plugin.py", "")
        handle.writestr("assets/", "")
        handle.writestr("assets/note.txt", "hello")

    install(archive, dest=dest, install_dir=install_dir)

    target = dest / "org.example" / "installed" / "1.0.0"
    assert target.is_dir()
    assert (target / "assets" / "note.txt").read_text(encoding="utf-8") == "hello"


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": None},
        {"version": None},
        {"type": None},
        {"entry_point": None},
        {"version": "not-a-version"},
        {"entry_point": "missing:Plugin"},
        {"entry_point": "plugin"},
        {"id": "nodots"},
        {"group_id": "org.other"},
        {"artifact_id": "other_artifact"},
    ],
)
def test_invalid_metadata_is_rejected_and_nothing_is_installed(
    tmp_path, dirs, overrides
):
    install_dir, dest = dirs
    data = metadata(**overrides)
    data = {key: value for key, value in data.items() if value is not None}
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "metadata.json").write_text(json.dumps(data), encoding="utf-8")
    (package / "plugin.py").write_text("", encoding="utf-8")

    with pytest.raises(PluginInstallationError):
        install(package, dest=dest, install_dir=install_dir)

    assert not dest.exists() or list(dest.iterdir()) == []


def test_an_invalid_settings_schema_rejects_the_package(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(
        tmp_path / "pkg",
        settings={"schema": {"level": {"type": "unknown", "default": 1}}},
    )

    with pytest.raises(PluginInstallationError, match="schema"):
        install(package, dest=dest, install_dir=install_dir)


def test_an_invalid_external_tools_declaration_rejects_the_package(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(
        tmp_path / "pkg",
        external_tools=[{"id": "backend", "name": "Backend"}],
    )

    with pytest.raises(PluginInstallationError, match="external_tools"):
        install(package, dest=dest, install_dir=install_dir)


def test_a_package_without_exactly_one_metadata_file_is_rejected(tmp_path, dirs):
    install_dir, dest = dirs
    wrapper = tmp_path / "wrapped"
    (wrapper / "one").mkdir(parents=True)
    (wrapper / "one" / "metadata.json").write_text("{}", encoding="utf-8")
    (wrapper / "two").mkdir()
    (wrapper / "two" / "metadata.json").write_text("{}", encoding="utf-8")
    (wrapper / "extra.txt").write_text("junk", encoding="utf-8")
    archive = zip_package(wrapper, tmp_path / "plugin.zip")

    with pytest.raises(PluginInstallationError, match="metadata.json"):
        install(archive, dest=dest, install_dir=install_dir)


@pytest.mark.parametrize("member", ["../escape.txt", "/absolute.txt"])
def test_archives_with_escaping_paths_are_rejected(tmp_path, dirs, member):
    install_dir, dest = dirs
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("metadata.json", json.dumps(metadata()))
        handle.writestr("plugin.py", "")
        handle.writestr(member, "escape")

    with pytest.raises(PluginInstallationError, match="path"):
        install(archive, dest=dest, install_dir=install_dir)


def test_archives_with_symlinks_are_rejected(tmp_path, dirs):
    install_dir, dest = dirs
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("metadata.json", json.dumps(metadata()))
        handle.writestr("plugin.py", "")
        link = zipfile.ZipInfo("link")
        link.external_attr = (0o120777 & 0xFFFF) << 16
        handle.writestr(link, "metadata.json")

    with pytest.raises(PluginInstallationError, match="symlink"):
        install(archive, dest=dest, install_dir=install_dir)


def test_a_plugin_shipped_with_the_application_is_not_installed(tmp_path, dirs):
    install_dir, dest = dirs
    (install_dir / "org.example" / "installed" / "1.0.0").mkdir(parents=True)
    package = write_package(tmp_path / "pkg")

    with pytest.raises(PluginInstallationError, match="shipped"):
        install(package, dest=dest, install_dir=install_dir)

    assert not dest.exists() or list(dest.iterdir()) == []


def test_an_installed_version_is_not_overwritten(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(tmp_path / "pkg")
    install(package, dest=dest, install_dir=install_dir)

    with pytest.raises(PluginInstallationError, match="already"):
        install(package, dest=dest, install_dir=install_dir)


def test_another_version_is_installed_next_to_the_existing_one(tmp_path, dirs):
    install_dir, dest = dirs
    install(write_package(tmp_path / "v1"), dest=dest, install_dir=install_dir)

    result = install(
        write_package(tmp_path / "v2", version="1.1.0"),
        dest=dest,
        install_dir=install_dir,
    )

    assert result.version == "1.1.0"
    artifact_dir = dest / "org.example" / "installed"
    assert sorted(os.listdir(artifact_dir)) == ["1.0.0", "1.1.0"]


def test_missing_dependencies_are_reported_but_do_not_block_installation(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(
        tmp_path / "pkg", python_dependencies=["quickfile-testdep"]
    )

    result = install(package, dest=dest, install_dir=install_dir)

    assert any("quickfile-testdep" in warning for warning in result.warnings)
    assert (dest / "org.example" / "installed" / "1.0.0").is_dir()


def test_a_non_sandboxed_plugin_needing_libs_is_rejected(tmp_path, dirs):
    install_dir, dest = dirs
    package = write_package(
        tmp_path / "pkg", python_dependencies=["quickfile-testdep"]
    )
    info = package / "libs" / "quickfile_testdep-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: quickfile-testdep\nVersion: 1.0\n",
        encoding="utf-8",
    )

    with pytest.raises(PluginInstallationError, match="sandboxed"):
        install(package, dest=dest, install_dir=install_dir)


def test_a_failed_installation_leaves_no_partial_tree(tmp_path, dirs):
    install_dir, dest = dirs
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("metadata.json", json.dumps(metadata(version="bad")))
        handle.writestr("plugin.py", "")

    with pytest.raises(PluginInstallationError):
        install(archive, dest=dest, install_dir=install_dir)

    leftovers = list(dest.iterdir()) if dest.exists() else []
    assert leftovers == []


def test_the_default_destination_is_the_external_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert plugin_installer.default_destination() == str(
        tmp_path / ".config" / "QuickFile" / "plugins-external"
    )


def test_the_cli_installs_and_reports_the_destination(tmp_path, dirs, capsys):
    install_dir, dest = dirs
    package = write_package(tmp_path / "pkg")

    exit_code = plugin_installer.main(
        [
            "install",
            str(package),
            "--dest",
            str(dest),
            "--install-dir",
            str(install_dir),
        ]
    )

    assert exit_code == 0
    assert str(dest / "org.example" / "installed" / "1.0.0") in capsys.readouterr().out


def test_the_cli_reports_a_rejected_package(tmp_path, dirs, capsys):
    install_dir, dest = dirs
    package = write_package(tmp_path / "pkg", version="bad")

    exit_code = plugin_installer.main(
        [
            "install",
            str(package),
            "--dest",
            str(dest),
            "--install-dir",
            str(install_dir),
        ]
    )

    assert exit_code == 1
    assert "bad" in capsys.readouterr().err
