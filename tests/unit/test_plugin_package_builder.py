# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
A package is only useful if the installer accepts it.

The builder writes the version directory contents at the archive root (the
layout the installer expects), skips bytecode and installed ``libs/``, and fixes
entry timestamps so the same tree produces the same bytes. The result is then
verified by installing it into a temporary directory.

Specification: ``docs/architecture/plugins/plugins.md`` ("Budowanie paczek").
"""

import glob
import hashlib
import json
import os
import subprocess
import sys
import zipfile

import pytest

import scripts.build_plugin_package as builder
from app.plugin_installer import install

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUNDLED_PLUGINS = os.path.join(PROJECT_ROOT, "plugins", "org.quickfile")

PLUGIN_SOURCE = """
from plugins.base import ViewerPlugin
class PackagedViewer(ViewerPlugin):
    def get_name(self): return "Packaged Viewer"
    def get_description(self): return "Packaged from a test tree"
    def can_view(self, path): return True
    def view_file(self, file_path: str, theme_manager=None, parent=None): pass
"""


def write_plugin(plugin_dir, version="1.0.0", plugin_id="org.example.packaged"):
    version_dir = plugin_dir / version
    version_dir.mkdir(parents=True)
    (version_dir / "metadata.json").write_text(
        json.dumps(
            {
                "id": plugin_id,
                "version": version,
                "type": "viewer",
                "name": "Packaged Viewer",
                "entry_point": "plugin:PackagedViewer",
            }
        ),
        encoding="utf-8",
    )
    (version_dir / "plugin.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
    return version_dir


@pytest.fixture
def package_tree(tmp_path):
    plugin_dir = tmp_path / "src" / "packaged"
    write_plugin(plugin_dir)
    output_dir = tmp_path / "dist"
    return plugin_dir, output_dir


def test_the_archive_holds_the_version_directory_at_its_root(package_tree):
    plugin_dir, output_dir = package_tree

    package = builder.build_package(plugin_dir / "1.0.0", output_dir)

    with zipfile.ZipFile(package) as archive:
        assert sorted(archive.namelist()) == ["metadata.json", "plugin.py"]
        assert json.loads(archive.read("metadata.json"))["version"] == "1.0.0"


def test_the_package_name_uses_the_artifact_id_and_version(package_tree):
    plugin_dir, output_dir = package_tree

    package = builder.build_package(plugin_dir / "1.0.0", output_dir)

    assert package.name == "packaged-1.0.0.zip"
    assert package.parent == output_dir


def test_a_plugin_directory_uses_its_highest_version(package_tree):
    plugin_dir, output_dir = package_tree
    write_plugin(plugin_dir, version="1.2.0")

    package = builder.build_package(plugin_dir, output_dir)

    with zipfile.ZipFile(package) as archive:
        assert json.loads(archive.read("metadata.json"))["version"] == "1.2.0"


def test_bytecode_and_installed_libs_are_left_out(package_tree):
    plugin_dir, output_dir = package_tree
    version_dir = plugin_dir / "1.0.0"
    (version_dir / "__pycache__").mkdir()
    (version_dir / "__pycache__" / "plugin.cpython-312.pyc").write_bytes(b"cache")
    (version_dir / "stale.pyc").write_bytes(b"cache")
    (version_dir / "libs" / "dependency").mkdir(parents=True)
    (version_dir / "libs" / "dependency" / "__init__.py").write_text("", encoding="utf-8")
    (version_dir / "wheels").mkdir()
    (version_dir / "wheels" / "dependency-1.0.whl").write_bytes(b"wheel")

    package = builder.build_package(version_dir, output_dir)

    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()

    assert "metadata.json" in names
    assert not [name for name in names if "__pycache__" in name or name.endswith(".pyc")]
    assert not [name for name in names if name.startswith("libs/")]
    assert "wheels/dependency-1.0.whl" in names


def test_building_twice_produces_the_same_bytes(package_tree):
    plugin_dir, output_dir = package_tree
    version_dir = plugin_dir / "1.0.0"

    first = builder.build_package(version_dir, output_dir)
    first_hash = hashlib.sha256(first.read_bytes()).hexdigest()

    second = builder.build_package(version_dir, output_dir)

    assert hashlib.sha256(second.read_bytes()).hexdigest() == first_hash


def test_the_package_installs_with_the_installer(package_tree, tmp_path):
    plugin_dir, output_dir = package_tree
    package = builder.build_package(plugin_dir / "1.0.0", output_dir)

    install_dir = tmp_path / "plugins"
    install_dir.mkdir()
    result = install(
        package, dest=tmp_path / "plugins-external", install_dir=install_dir
    )

    assert result.plugin_id == "org.example.packaged"
    assert os.path.isfile(os.path.join(result.path, "plugin.py"))


def test_a_directory_without_metadata_is_rejected(tmp_path):
    version_dir = tmp_path / "src" / "empty" / "1.0.0"
    version_dir.mkdir(parents=True)

    with pytest.raises(builder.PluginPackageError):
        builder.build_package(version_dir, tmp_path / "dist")


def test_every_bundled_plugin_can_be_packaged(tmp_path):
    plugin_dirs = sorted(
        path
        for path in glob.glob(os.path.join(BUNDLED_PLUGINS, "*"))
        if os.path.isdir(path)
    )

    packages = [builder.build_package(path, tmp_path / "dist") for path in plugin_dirs]

    assert len(packages) == len(plugin_dirs)
    assert all(package.is_file() for package in packages)


def test_the_cli_prints_the_package_path(package_tree, capsys):
    plugin_dir, output_dir = package_tree

    exit_code = builder.main(
        [str(plugin_dir / "1.0.0"), "--output", str(output_dir)]
    )

    assert exit_code == 0
    assert "packaged-1.0.0.zip" in capsys.readouterr().out


def test_the_cli_rejects_broken_input(tmp_path, capsys):
    version_dir = tmp_path / "src" / "empty" / "1.0.0"
    version_dir.mkdir(parents=True)

    exit_code = builder.main([str(version_dir), "--output", str(tmp_path / "dist")])

    assert exit_code == 1
    assert "metadata.json" in capsys.readouterr().err


def test_the_script_runs_as_a_module(package_tree):
    plugin_dir, output_dir = package_tree

    result = subprocess.run(
        [
            sys.executable,
            os.path.join(PROJECT_ROOT, "scripts", "build_plugin_package.py"),
            str(plugin_dir / "1.0.0"),
            "--output",
            str(output_dir),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "packaged-1.0.0.zip" in result.stdout
